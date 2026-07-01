"""
ServiceOne Database Module — Google Cloud Firestore Client Connection Manager
"""
import os
import sys
import json
import random
import urllib.request
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from google.cloud import firestore
from config import settings

logger = logging.getLogger("serviceone_api.database")

# ── Firestore Client Connection ──────────────────────────────
db_client = None
use_mock_db = False

try:
    # Google Cloud Firestore Client automatically retrieves credentials from 
    # the GOOGLE_APPLICATION_CREDENTIALS path (or metadata server in Cloud Run)
    db_client = firestore.Client()
    logger.info("[Firestore] Client initialized successfully.")
    print("[Firestore] Client initialized successfully.")
except Exception as e:
    logger.warning(f"[Firestore Init Warning] Failed to connect to GCP Firestore: {e}. Falling back to In-Memory DB.")
    print(f"[Firestore Warning] Fallback to local memory db: {e}")
    use_mock_db = True

# ── Mock In-Memory Firestore Fallback for Offline Dev/Testing ────────────────
class MockDocumentReference:
    def __init__(self, doc_id, data_store, collection_name):
        self.id = doc_id
        self._store = data_store
        self._col = collection_name

    def get(self):
        class MockSnap:
            def __init__(self, exists, data, doc_id):
                self.exists = exists
                self.id = doc_id
                self._data = data
            def to_dict(self):
                return self._data
        
        doc_data = self._store.get(self._col, {}).get(self.id)
        return MockSnap(doc_data is not None, doc_data, self.id)

    def set(self, data, merge=True):
        if self._col not in self._store:
            self._store[self._col] = {}
        if merge and self.id in self._store[self._col]:
            self._store[self._col][self.id].update(data)
        else:
            self._store[self._col][self.id] = data

    def delete(self):
        if self._col in self._store and self.id in self._store[self._col]:
            del self._store[self._col][self.id]

class MockQuery:
    def __init__(self, collection_name, data_store):
        self._col = collection_name
        self._store = data_store
        self._filters = []
        self._order_by = None
        self._limit = None

    def where(self, field, op, val):
        self._filters.append((field, op, val))
        return self

    def order_by(self, field, direction="ASCENDING"):
        self._order_by = (field, direction)
        return self

    def limit(self, count):
        self._limit = count
        return self

    def stream(self):
        docs = list(self._store.get(self._col, {}).values())
        filtered = []
        for d in docs:
            match = True
            for field, op, val in self._filters:
                # Basic mock operations
                field_val = d.get(field)
                if op == "==" and field_val != val:
                    match = False
                elif op == ">" and not (field_val is not None and field_val > val):
                    match = False
                elif op == "<" and not (field_val is not None and field_val < val):
                    match = False
                elif op == "in" and field_val not in val:
                    match = False
            if match:
                filtered.append(d)
        
        if self._order_by:
            field, direction = self._order_by
            # Sort by field. Convert empty fields to default empty strings/integers for sorting
            filtered.sort(key=lambda x: x.get(field, ""), reverse=(direction == "DESCENDING" or direction == firestore.Query.DESCENDING))
            
        if self._limit:
            filtered = filtered[:self._limit]
            
        class MockDocSnap:
            def __init__(self, data):
                self.id = str(data.get("id", ""))
                self._data = data
            def to_dict(self):
                return self._data

        return [MockDocSnap(d) for d in filtered]

class MockFirestoreClient:
    def __init__(self):
        self._store = {}

    def collection(self, name):
        class MockColRef:
            def __init__(self, col_name, store):
                self.name = col_name
                self._store = store
            def document(self, doc_id=None):
                if not doc_id:
                    doc_id = str(random.randint(100000, 999999))
                return MockDocumentReference(doc_id, self._store, self.name)
            def where(self, field, op, val):
                return MockQuery(self.name, self._store).where(field, op, val)
            def order_by(self, field, direction="ASCENDING"):
                return MockQuery(self.name, self._store).order_by(field, direction)
            def limit(self, count):
                return MockQuery(self.name, self._store).limit(count)
            def stream(self):
                return MockQuery(self.name, self._store).stream()
        return MockColRef(name, self._store)

if use_mock_db:
    db_client = MockFirestoreClient()

# ── Helper to convert Firestore Documents to psycopg2 Dict interface ──
def _to_row(snap) -> Optional[Dict[str, Any]]:
    if not snap or not snap.exists:
        return None
    return snap.to_dict()

def _to_rows(stream) -> List[Dict[str, Any]]:
    return [doc.to_dict() for doc in stream]

# Generate a safe random 32-bit positive integer ID for compatibility
def _gen_id() -> int:
    return random.randint(1, 2147483647)

# ── Quote Checks ─────────────────────────────────────────────
def save_quote_check(data: dict) -> int:
    """Save a quote check result. Returns the new document ID."""
    row_id = data.get("id") or _gen_id()
    doc_data = {
        "id": int(row_id),
        "user_id": data.get("user_id"),
        "city": data.get("city", ""),
        "area": data.get("area", ""),
        "appliance": data.get("appliance", ""),
        "brand": data.get("brand", ""),
        "service_type": data.get("service_type", ""),
        "quoted_price": float(data.get("quoted_price", 0)),
        "fair_range_min": float(data.get("fair_range_min", 0)) if data.get("fair_range_min") else None,
        "fair_range_max": float(data.get("fair_range_max", 0)) if data.get("fair_range_max") else None,
        "verdict": data.get("verdict", ""),
        "confidence_score": float(data.get("confidence_score", 0)) if data.get("confidence_score") else None,
        "explanation": data.get("explanation", ""),
        "provider_name": data.get("provider_name", ""),
        "full_result_json": data.get("full_result_json", {}),
        "created_at": datetime.now().isoformat()
    }
    db_client.collection("quote_checks").document(str(row_id)).set(doc_data)
    return row_id


def get_quote_history(limit=50):
    """Get recent quote check history."""
    stream = db_client.collection("quote_checks").order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
    return _to_rows(stream)


# ── Search History ───────────────────────────────────────────
def save_search_history(data: dict) -> int:
    """Save a search to history for dashboard."""
    row_id = data.get("id") or _gen_id()
    doc_data = {
        "id": int(row_id),
        "user_id": data.get("user_id"),
        "search_query": data.get("search_query", ""),
        "appliance_type": data.get("appliance_type", ""),
        "service_type": data.get("service_type", ""),
        "city": data.get("city", ""),
        "quoted_price": float(data.get("quoted_price", 0)) if data.get("quoted_price") else 0.0,
        "verdict": data.get("verdict", ""),
        "potential_savings": float(data.get("potential_savings", 0)) if data.get("potential_savings") else 0.0,
        "source_links": data.get("source_links", []),
        "full_result_json": data.get("full_result_json", {}),
        "is_bookmarked": bool(data.get("is_bookmarked", False)),
        "created_at": datetime.now().isoformat()
    }
    db_client.collection("search_history").document(str(row_id)).set(doc_data)
    return row_id


def get_search_history(limit=50, email: str = None):
    """Get recent search history for dashboard, filtered by user email."""
    if not email:
        return []
    
    # 1. Retrieve the user ID from user email
    user = get_user_by_email(email)
    if not user:
        return []
    
    user_id = user["id"]
    stream = db_client.collection("search_history") \
                       .where("user_id", "==", int(user_id)) \
                       .order_by("created_at", direction=firestore.Query.DESCENDING) \
                       .limit(limit).stream()
    return _to_rows(stream)


def toggle_bookmark(search_id: int) -> bool:
    """Toggle bookmark on a search history item."""
    doc_ref = db_client.collection("search_history").document(str(search_id))
    snap = doc_ref.get()
    if snap.exists:
        curr = snap.to_dict().get("is_bookmarked", False)
        new_val = not curr
        doc_ref.set({"is_bookmarked": new_val}, merge=True)
        return new_val
    return False


# ── Custom Searches ──────────────────────────────────────────
def save_custom_search(data: dict) -> int:
    """Save a user-added custom search URL."""
    row_id = data.get("id") or _gen_id()
    doc_data = {
        "id": int(row_id),
        "user_id": data.get("user_id"),
        "search_label": data.get("search_label", ""),
        "search_url": data.get("search_url", ""),
        "search_type": data.get("search_type", "custom"),
        "notes": data.get("notes", ""),
        "created_at": datetime.now().isoformat()
    }
    db_client.collection("custom_searches").document(str(row_id)).set(doc_data)
    return row_id


def get_custom_searches(limit=50, email: str = None):
    """Get user's custom searches, filtered by user email."""
    if not email:
        return []
    user = get_user_by_email(email)
    if not user:
        return []
    
    user_id = user["id"]
    stream = db_client.collection("custom_searches") \
                       .where("user_id", "==", int(user_id)) \
                       .order_by("created_at", direction=firestore.Query.DESCENDING) \
                       .limit(limit).stream()
    return _to_rows(stream)


def delete_custom_search(search_id: int):
    """Delete a custom search."""
    db_client.collection("custom_searches").document(str(search_id)).delete()


# ── Providers ────────────────────────────────────────────────
def upsert_provider(data: dict) -> int:
    """Insert or update a provider (by name + city + source)."""
    row_id = data.get("id") or _gen_id()
    doc_data = {
        "id": int(row_id),
        "name": data.get("name", ""),
        "city": data.get("city", ""),
        "area": data.get("area", ""),
        "appliance_types": data.get("appliance_types", []),
        "phone": data.get("phone", ""),
        "address": data.get("address", ""),
        "google_maps_url": data.get("google_maps_url", ""),
        "website_url": data.get("website_url", ""),
        "source": data.get("source", ""),
        "source_url": data.get("source_url", ""),
        "avg_rating": float(data.get("avg_rating", 0)) if data.get("avg_rating") else None,
        "review_count": int(data.get("review_count", 0)) if data.get("review_count") else 0,
        "avg_price_min": float(data.get("avg_price_min", 0)) if data.get("avg_price_min") else None,
        "avg_price_max": float(data.get("avg_price_max", 0)) if data.get("avg_price_max") else None,
        "is_verified": bool(data.get("is_verified", False)),
        "is_active": bool(data.get("is_active", True)),
        "is_deleted": bool(data.get("is_deleted", False)),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    db_client.collection("providers").document(str(row_id)).set(doc_data)
    return row_id


def get_providers_by_city(city: str, appliance: str = None, limit=20):
    """Get providers in a city, optionally filtered by appliance type."""
    query = db_client.collection("providers") \
                     .where("is_active", "==", True) \
                     .where("is_deleted", "==", False)

    # Note: Firestore inequality queries cannot easily filter case insensitively 
    # without structured lowercase values. We will query and filter locally or do exact match.
    stream = query.stream()
    rows = _to_rows(stream)
    
    # Filter locally by city name (case-insensitive) and appliance types
    filtered = []
    for r in rows:
        if r.get("city", "").lower() == city.lower():
            if appliance:
                app_list = [a.lower() for a in r.get("appliance_types", [])]
                if appliance.lower() in app_list:
                    filtered.append(r)
            else:
                filtered.append(r)
                
    # Sort by rating descending
    filtered.sort(key=lambda x: x.get("avg_rating") or 0.0, reverse=True)
    return filtered[:limit]


# ── Cache ────────────────────────────────────────────────────
def get_cached_signal(cache_key: str):
    """Get a cached market signal if still valid."""
    # Escape characters that are invalid in doc IDs if needed, or hash the key
    safe_key = cache_key.replace("/", "_").replace("\\", "_")
    snap = db_client.collection("cached_market_signals").document(safe_key).get()
    if snap.exists:
        doc = snap.to_dict()
        exp_str = doc.get("expires_at")
        if exp_str:
            try:
                expires_at = datetime.fromisoformat(exp_str)
                if expires_at > datetime.now():
                    return doc
            except Exception:
                pass
    return None


def save_cached_signal(data: dict):
    """Save or update a cached market signal."""
    cache_key = data.get("cache_key")
    if not cache_key:
        return
    safe_key = cache_key.replace("/", "_").replace("\\", "_")
    doc_data = {
        "cache_key": cache_key,
        "city": data.get("city", ""),
        "appliance": data.get("appliance", ""),
        "service_type": data.get("service_type", ""),
        "brand": data.get("brand"),
        "avg_price": float(data.get("avg_price", 0)) if data.get("avg_price") else 0.0,
        "price_range_min": float(data.get("price_range_min", 0)) if data.get("price_range_min") else 0.0,
        "price_range_max": float(data.get("price_range_max", 0)) if data.get("price_range_max") else 0.0,
        "sources_json": data.get("sources_json", []),
        "provider_suggestions": data.get("provider_suggestions", []),
        "raw_scraped_data": data.get("raw_scraped_data", {}),
        "scraped_at": datetime.now().isoformat(),
        "expires_at": data.get("expires_at") or (datetime.now() + timedelta(hours=2)).isoformat()
    }
    db_client.collection("cached_market_signals").document(safe_key).set(doc_data)


# ── Community Reports ────────────────────────────────────────
def save_community_report(data: dict) -> int:
    """Save a community-submitted report with user ID and proof photo."""
    row_id = data.get("id") or _gen_id()
    doc_data = {
        "id": int(row_id),
        "user_id": data.get("user_id"),
        "city": data.get("city", ""),
        "area": data.get("area", ""),
        "appliance": data.get("appliance", ""),
        "service_type": data.get("service_type", ""),
        "provider_name": data.get("provider_name", ""),
        "quoted_price": float(data.get("quoted_price", 0)) if data.get("quoted_price") else 0.0,
        "approved_status": data.get("approved_status", "pending"),
        "proof_image_url": data.get("proof_image_url"),
        "notes": data.get("notes", ""),
        "created_at": datetime.now().isoformat()
    }
    db_client.collection("community_reports").document(str(row_id)).set(doc_data)
    return row_id


def get_community_reports(city: str = None, appliance: str = None, limit=50):
    """Get approved community reports, optionally filtered."""
    stream = db_client.collection("community_reports").where("approved_status", "==", "approved").stream()
    rows = _to_rows(stream)
    
    filtered = []
    for r in rows:
        match_city = not city or r.get("city", "").lower() == city.lower()
        match_app = not appliance or r.get("appliance", "").lower() == appliance.lower()
        if match_city and match_app:
            filtered.append(r)
            
    filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return filtered[:limit]


def get_user_community_reports(email: str, limit=50):
    """Retrieve community reports strictly submitted by the logged-in user email."""
    if not email:
        return []
    user = get_user_by_email(email)
    if not user:
        return []
        
    user_id = user["id"]
    stream = db_client.collection("community_reports") \
                       .where("user_id", "==", int(user_id)) \
                       .order_by("created_at", direction=firestore.Query.DESCENDING) \
                       .limit(limit).stream()
    return _to_rows(stream)


def get_all_community_reports_for_admin(limit=100):
    """Retrieve all submitted community reports for moderation (pending, approved, rejected)."""
    stream = db_client.collection("community_reports") \
                       .order_by("created_at", direction=firestore.Query.DESCENDING) \
                       .limit(limit).stream()
    reports = _to_rows(stream)
    
    # Enrich with user email and user name
    for r in reports:
        u_id = r.get("user_id")
        if u_id:
            # Quick lookup in users collection
            u_snap = db_client.collection("users").document(str(u_id)).get()
            if u_snap.exists:
                u_data = u_snap.to_dict()
                r["user_email"] = u_data.get("email")
                r["user_name"] = u_data.get("name")
        if "user_email" not in r:
            r["user_email"] = None
        if "user_name" not in r:
            r["user_name"] = None
            
    return reports


def update_community_report_status(report_id: int, status: str) -> bool:
    """Set the approved_status of a community report to approved or rejected."""
    doc_ref = db_client.collection("community_reports").document(str(report_id))
    snap = doc_ref.get()
    if snap.exists:
        doc_ref.set({"approved_status": status}, merge=True)
        return True
    return False


# ── Geographic Lookup (India) — Robust Infallible System ─────────────────

FALLBACK_PINS = {
    "11": {
        "state": "DELHI",
        "city": "New Delhi",
        "localities": ["Connaught Place", "Karol Bagh", "Dwarka Sector 10", "Rohini Sector 3", "Saket", "Vasant Kunj", "Lajpat Nagar", "Chandni Chowk", "Okhla Phase 3", "Rajouri Garden"]
    },
    "12": {
        "state": "HARYANA",
        "city": "Gurugram",
        "localities": ["DLF Phase 3", "Sohna Road", "Sector 45", "Sector 56", "Sector 21", "Udyog Vihar", "Palam Vihar", "Golf Course Road"]
    },
    "13": {
        "state": "HARYANA",
        "city": "Faridabad",
        "localities": ["Sector 15", "Sector 37", "Sector 21C", "Greenfield Colony", "Surajkund", "Mathura Road", "Ballabhgarh"]
    },
    "14": {
        "state": "PUNJAB",
        "city": "Ludhiana",
        "localities": ["Sarabha Nagar", "Model Town", "Civil Lines", "BRS Nagar", "Ferozepur Road", "Gill Road", "Sundar Nagar"]
    },
    "15": {
        "state": "PUNJAB",
        "city": "Amritsar",
        "localities": ["Ranjit Avenue", "Mall Road", "Golden Temple Area", "Putligarh", "Lawrence Road", "Chheharta"]
    },
    "16": {
        "state": "CHANDIGARH",
        "city": "Chandigarh",
        "localities": ["Sector 17", "Sector 35", "Sector 8", "Sector 22", "Sector 15", "Manimajra", "Industrial Area Phase 1"]
    },
    "17": {
        "state": "HIMACHAL PRADESH",
        "city": "Shimla",
        "localities": ["Mall Road", "Chotta Shimla", "Sanjauli", "Kasumpti", "Summer Hill", "Lakkar Bazar", "New Shimla"]
    },
    "18": {
        "state": "JAMMU AND KASHMIR",
        "city": "Jammu",
        "localities": ["Gandhi Nagar", "Trikuta Nagar", "Channi Himmat", "Bari Brahmana", "Rehari Chhawni", "Karan Nagar"]
    },
    "19": {
        "state": "JAMMU AND KASHMIR",
        "city": "Srinagar",
        "localities": ["Lal Chowk", "Rajbagh", "Karan Nagar", "Nishat", "Hazratbal", "Sonwar", "Soura"]
    },
    "20": {
        "state": "UTTAR PRADESH",
        "city": "Noida",
        "localities": ["Sector 62", "Sector 18", "Sector 15", "Sector 50", "Sector 137", "Sector 76", "Noida Extension", "Sector 93"]
    },
    "21": {
        "state": "UTTAR PRADESH",
        "city": "Lucknow",
        "localities": ["Hazratganj", "Gomti Nagar", "Aliganj", "Indira Nagar", "Charbagh", "Aminabad", "Ashiyana", "Mahanagar"]
    },
    "22": {
        "state": "UTTAR PRADESH",
        "city": "Kanpur",
        "localities": ["Swarup Nagar", "Kalyanpur", "Kidwai Nagar", "Civil Lines", "Lajpat Nagar", "Sharda Nagar", "Mall Road"]
    },
    "24": {
        "state": "UTTARAKHAND",
        "city": "Dehradun",
        "localities": ["Rajpur Road", "Dehradun Cantt", "Dalanwala", "Jakhan Cantt", "Patel Nagar", "Prem Nagar", "Vikas Nagar"]
    },
    "25": {
        "state": "UTTAR PRADESH",
        "city": "Meerut",
        "localities": ["Shastri Nagar", "Modipuram", "Saket", "Civil Lines", "Pallavpuram", "Meerut Cantt"]
    },
    "27": {
        "state": "UTTAR PRADESH",
        "city": "Varanasi",
        "localities": ["Lanka", "Cantonment", "Assi Ghat", "Sigra", "Bhelupur", "Sarnath", "Godowlia"]
    },
    "28": {
        "state": "UTTAR PRADESH",
        "city": "Agra",
        "localities": ["Tajganj", "Sanjay Place", "Sikandra", "Dayalbagh", "Kamla Nagar", "Fatehabad Road"]
    },
    "30": {
        "state": "RAJASTHAN",
        "city": "Jaipur",
        "localities": ["Malviya Nagar", "Vaishali Nagar", "C-Scheme", "Mansarovar", "Raja Park", "Tonk Road", "Adarsh Nagar", "Sanganer"]
    },
    "31": {
        "state": "RAJASTHAN",
        "city": "Udaipur",
        "localities": ["Panchwati", "Hiran Magri", "Fatehpura", "Sector 4", "Lake Palace Road", "Shobhagpura"]
    },
    "32": {
        "state": "RAJASTHAN",
        "city": "Kota",
        "localities": ["Vigyan Nagar", "Talwandi", "Rajeev Gandhi Nagar", "Kunhari", "Dadabari", "Nayapura"]
    },
    "34": {
        "state": "RAJASTHAN",
        "city": "Jodhpur",
        "localities": ["Sardarpura", "Shastri Nagar", "Ratanada", "Chasni Circle", "Kamla Nehru Nagar", "Mandore"]
    },
    "36": {
        "state": "GUJARAT",
        "city": "Rajkot",
        "localities": ["Kalawad Road", "Yagnik Road", "Amin Marg", "Moti Tanki", "University Road", "Bhakti Nagar"]
    },
    "38": {
        "state": "GUJARAT",
        "city": "Ahmedabad",
        "localities": ["Satellite", "C G Road", "Bodakdev", "Vastrapur", "Prahlad Nagar", "Navrangpura", "Paldi", "Ghatlodia"]
    },
    "39": {
        "state": "GUJARAT",
        "city": "Surat",
        "localities": ["Adajan", "Vesu", "Piplod", "Varachha", "Katargam", "Nanpura", "Ghod Dod Road"]
    },
    "40": {
        "state": "MAHARASHTRA",
        "city": "Mumbai",
        "localities": ["Andheri West", "Bandra West", "Colaba", "Dadar", "Borivali West", "Powai", "Juhu", "Ghatkopar", "Worli", "Chembur"]
    },
    "41": {
        "state": "MAHARASHTRA",
        "city": "Pune",
        "localities": ["Koregaon Park", "Kothrud", "Aundh", "Viman Nagar", "Hinjewadi", "Baner", "Kalyani Nagar", "Hadapsar", "Wakad"]
    },
    "42": {
        "state": "MAHARASHTRA",
        "city": "Thane",
        "localities": ["Ghodbunder Road", "Naupada", "Wagle Estate", "Kopri", "Vartak Nagar", "Majiwada", "Kalyan"]
    },
    "44": {
        "state": "MAHARASHTRA",
        "city": "Nagpur",
        "localities": ["Dharampeth", "Ramdaspeth", "Sadar", "Wardha Road", "Manish Nagar", "Nandanvan", "Pratap Nagar"]
    },
    "45": {
        "state": "MADHYA PRADESH",
        "city": "Indore",
        "localities": ["Vijay Nagar", "Palasia", "Rajendra Nagar", "Sudama Nagar", "Annapurna", "Chappan Dukan", "Mahalaxmi Nagar"]
    },
    "46": {
        "state": "MADHYA PRADESH",
        "city": "Bhopal",
        "localities": ["Arera Colony", "MP Nagar", "Kolar Road", "TT Nagar", "Indrapuri", "Bairagarh", "Habibganj"]
    },
    "48": {
        "state": "MADHYA PRADESH",
        "city": "Gwalior",
        "localities": ["Lashkar", "Morar", "DD Nagar", "City Center", "Hazira", "Gwalior Cantt"]
    },
    "49": {
        "state": "CHHATTISGARH",
        "city": "Raipur",
        "localities": ["Shankar Nagar", "Devendra Nagar", "Pandri", "Tatibandh", "Samta Colony", "Sadar Bazar"]
    },
    "50": {
        "state": "TELANGANA",
        "city": "Hyderabad",
        "localities": ["Gachibowli", "Madhapur", "Jubilee Hills", "Banjara Hills", "Kondapur", "Begumpet", "Kukatpally", "Secunderabad", "Ameerpet", "Mehdipatnam"]
    },
    "52": {
        "state": "ANDHRA PRADESH",
        "city": "Vijayawada",
        "localities": ["Benz Circle", "Governorpet", "Moghalrajpuram", "Labbipet", "Satyanarayanapuram", "One Town"]
    },
    "53": {
        "state": "ANDHRA PRADESH",
        "city": "Visakhapatnam",
        "localities": ["Gajuwaka", "MVP Colony", "Siripuram", "Madhurawada", "Dwarka Nagar", "Jagadamba Junction", "Maharanipeta"]
    },
    "56": {
        "state": "KARNATAKA",
        "city": "Bengaluru",
        "localities": ["Indiranagar", "Koramangala", "HSR Layout", "Jayanagar", "Whitefield", "Electronic City", "Marathahalli", "BTM Layout", "Malleshwaram", "Hebbal"]
    },
    "57": {
        "state": "KARNATAKA",
        "city": "Mysuru",
        "localities": ["Gokulam", "Vidyaranyapuram", "Jayalakshmipuram", "Hebbal", "Kuvempunagar", "Siddhartha Layout"]
    },
    "58": {
        "state": "KARNATAKA",
        "city": "Hubballi",
        "localities": ["Keshwapur", "Vidyanagar", "Gokul Road", "Deshpande Nagar", "Shirur Park", "Koppikar Road"]
    },
    "60": {
        "state": "TAMIL NADU",
        "city": "Chennai",
        "localities": ["Adyar", "Anna Nagar", "T Nagar", "Velachery", "Mylapore", "Nungambakkam", "Tambaram", "OMR Sholinganallur", "Besant Nagar", "Guindy"]
    },
    "61": {
        "state": "TAMIL NADU",
        "city": "Madurai",
        "localities": ["KK Nagar", "Anna Nagar", "Sellur", "Simmakkal", "Goripalayam", "Koodal Nagar"]
    },
    "64": {
        "state": "TAMIL NADU",
        "city": "Coimbatore",
        "localities": ["Gandhipuram", "RS Puram", "Peelamedu", "Saibaba Colony", "Ramanathapuram", "Singanallur", "Saravanampatti"]
    },
    "68": {
        "state": "KERALA",
        "city": "Kochi",
        "localities": ["Ernakulam", "Edappally", "Kadavanthra", "Kakkanad", "Vytilla", "Fort Kochi", "Aluva", "Tripunithura"]
    },
    "69": {
        "state": "KERALA",
        "city": "Thiruvananthapuram",
        "localities": ["Kazhakkoottam", "Vazhuthacaud", "Palayam", "Pattom", "Kowdiar", "Medical College Area"]
    },
    "70": {
        "state": "WEST BENGAL",
        "city": "Kolkata",
        "localities": ["Salt Lake Sector 5", "Park Street", "Gariahat", "New Town", "Behala", "Jadavpur", "Alipore", "Dum Dum", "Ballygunge", "Howrah"]
    },
    "75": {
        "state": "ODISHA",
        "city": "Bhubaneswar",
        "localities": ["Patia", "Nayapalli", "Kharavela Nagar", "Saheed Nagar", "Jayadev Vihar", "Chandrasekharpur"]
    },
    "78": {
        "state": "ASSAM",
        "city": "Guwahati",
        "localities": ["Ganeshguri", "Paltan Bazaar", "Dispur", "Beltola", "Silpukhuri", "Khanapara", "Adabari"]
    },
    "79": {
        "state": "MEGHALAYA",
        "city": "Shillong",
        "localities": ["Police Bazar", "Laitumkhrah", "Nongthymmai", "Mawlai", "Laban"]
    },
    "80": {
        "state": "BIHAR",
        "city": "Patna",
        "localities": ["Kankarbagh", "Bailey Road", "Boring Road", "Patliputra Colony", "Fraser Road", "Rajendra Nagar", "Anisabad"]
    },
    "82": {
        "state": "JHARKHAND",
        "city": "Ranchi",
        "localities": ["Lalpur", "Morabadi", "Harmu Colony", "Doranda", "Kanke Road", "Bariatu"]
    },
}

JSON_CACHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db", "pincodes_cache.json"))
COMPILED_PINS_CACHE = {}

if os.path.exists(JSON_CACHE_PATH):
    try:
        with open(JSON_CACHE_PATH, "r", encoding="utf-8") as f:
            COMPILED_PINS_CACHE = json.load(f)
        print(f"[Database] Loaded {len(COMPILED_PINS_CACHE)} unique Indian pincodes from compiled cache successfully.")
    except Exception as e:
        print(f"[Database] Error loading compiled pincodes cache: {e}")

def generate_pincode_fallback(pincode: str) -> list:
    """In-memory geographic fallback generator."""
    if len(pincode) != 6 or not pincode.isdigit():
        return []
    
    if pincode in COMPILED_PINS_CACHE:
        record = COMPILED_PINS_CACHE[pincode]
        state = record["state"]
        city = record["city"]
        localities = record["localities"]
        return [{
            "pincode": pincode,
            "locality": loc,
            "city": city,
            "state": state
        } for loc in localities]
        
    prefix2 = pincode[:2]
    prefix1 = pincode[0]
    
    record = FALLBACK_PINS.get(prefix2)
    if not record:
        region_defaults = {
            "1": {"state": "DELHI", "city": "New Delhi", "localities": ["Connaught Place", "Karol Bagh", "Dwarka Sector 10", "Rohini Sector 3", "Saket"]},
            "2": {"state": "UTTAR PRADESH", "city": "Noida", "localities": ["Sector 62", "Sector 18", "Sector 15", "Sector 50", "Sector 137"]},
            "3": {"state": "RAJASTHAN", "city": "Jaipur", "localities": ["Malviya Nagar", "Vaishali Nagar", "C-Scheme", "Mansarovar", "Raja Park"]},
            "4": {"state": "MAHARASHTRA", "city": "Mumbai", "localities": ["Andheri West", "Bandra West", "Colaba", "Dadar", "Borivali West"]},
            "5": {"state": "KARNATAKA", "city": "Bengaluru", "localities": ["Indiranagar", "Koramangala", "HSR Layout", "Jayanagar", "Whitefield"]},
            "6": {"state": "TAMIL NADU", "city": "Chennai", "localities": ["Adyar", "Anna Nagar", "T Nagar", "Velachery", "Mylapore"]},
            "7": {"state": "WEST BENGAL", "city": "Kolkata", "localities": ["Salt Lake Sector 5", "Park Street", "Gariahat", "New Town", "Behala"]},
            "8": {"state": "BIHAR", "city": "Patna", "localities": ["Kankarbagh", "Bailey Road", "Boring Road", "Patliputra Colony", "Fraser Road"]},
            "9": {"state": "TELANGANA", "city": "Hyderabad", "localities": ["Gachibowli", "Madhapur", "Jubilee Hills", "Banjara Hills", "Kondapur"]},
        }
        record = region_defaults.get(prefix1, region_defaults["1"])
        
    state = record["state"]
    city = record["city"]
    localities = record["localities"]
    
    return [{
        "pincode": pincode,
        "locality": loc,
        "city": city,
        "state": state
    } for loc in localities]

def get_geo_states():
    """Retrieve distinct states sorted alphabetically."""
    # Firestore geodata is large, resolve from high-fidelity compiled postal cache directly
    if COMPILED_PINS_CACHE:
        return sorted(list({v["state"] for v in COMPILED_PINS_CACHE.values()}))
    return sorted(list({v["state"] for v in FALLBACK_PINS.values()}))

def get_geo_cities(state: str):
    """Retrieve distinct cities for a given state sorted alphabetically."""
    cities = []
    cache_to_use = COMPILED_PINS_CACHE if COMPILED_PINS_CACHE else FALLBACK_PINS
    for v in cache_to_use.values():
        if v["state"].lower() == state.lower() and v["city"] not in cities:
            cities.append(v["city"])
    return sorted(cities) if cities else ["New Delhi", "Mumbai", "Bengaluru", "Chennai", "Kolkata", "Hyderabad", "Pune", "Noida", "Gurugram"]

def get_geo_localities(city: str):
    """Retrieve distinct localities for a given city sorted alphabetically."""
    localities = []
    cache_to_use = COMPILED_PINS_CACHE if COMPILED_PINS_CACHE else FALLBACK_PINS
    for v in cache_to_use.values():
        if v["city"].lower() == city.lower():
            localities.extend(v["localities"])
    if localities:
        return sorted(list(set(localities)))
    return ["Main Market", "Sector 1", "Civil Lines", "Railway Station Road", "Defense Colony"]

def insert_geo_location(pincode: str, locality: str, city: str, state: str):
    """Dynamically save a geo-location row to Firestore if not already present."""
    try:
        doc_id = f"{pincode}_{locality.lower().strip().replace(' ', '_')}"
        doc_ref = db_client.collection("geo_locations").document(doc_id)
        # Check existence first to prevent redundant write billing
        snap = doc_ref.get()
        if not snap.exists:
            doc_ref.set({
                "pincode": pincode,
                "locality": locality,
                "city": city,
                "state": state,
                "created_at": datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"[GeoLookup] Error saving geo location: {e}")


def fetch_external_pincode(pincode: str):
    """Fetch pincode data from public Indian Postal API as fallback."""
    url = f"https://api.postalpincode.in/pincode/{pincode}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                if data and isinstance(data, list) and data[0].get("Status") == "Success":
                    return data[0].get("PostOffice")
    except Exception as e:
        print(f"[GeoLookup] Error fetching external pincode {pincode}: {e}")
    return None


def get_geo_by_pincode(pincode: str):
    """Retrieve state, city, and localities matching a 6-digit pincode with Firestore lookup."""
    # 1. Check offline high-fidelity compiled cache first (fast, free)
    if COMPILED_PINS_CACHE and pincode in COMPILED_PINS_CACHE:
        record = COMPILED_PINS_CACHE[pincode]
        state = record["state"]
        city = record["city"]
        localities = record["localities"]
        return [{
            "pincode": pincode,
            "locality": loc,
            "city": city,
            "state": state
        } for loc in localities]

    # 2. Check if we have previously saved it dynamically in Firestore
    try:
        stream = db_client.collection("geo_locations").where("pincode", "==", pincode).stream()
        rows = _to_rows(stream)
        if rows:
            return rows
    except Exception as e:
        logger.warning(f"[GeoLookup] Firestore lookup failed for pincode {pincode}: {e}")

    # 3. DB & Local Cache Miss -> Fetch from public Indian Postal API
    offices = fetch_external_pincode(pincode)
    if offices:
        inserted_rows = []
        for office in offices:
            locality = office.get("Name")
            city = office.get("District")
            state = office.get("State")
            if locality and city and state:
                formatted_state = state.upper()
                insert_geo_location(pincode, locality, city, formatted_state)
                inserted_rows.append({
                    "pincode": pincode,
                    "locality": locality,
                    "city": city,
                    "state": formatted_state
                })
        if inserted_rows:
            return inserted_rows
            
    return generate_pincode_fallback(pincode)


# ── Users ────────────────────────────────────────────────────
def get_user_by_email(email: str):
    """Retrieve full user row by email address."""
    stream = db_client.collection("users").where("email", "==", email.lower()).limit(1).stream()
    rows = _to_rows(stream)
    return rows[0] if rows else None


def get_or_create_user(email: str, name: str = None) -> int:
    """Get or create user by email, returning the user's primary key ID."""
    user = get_user_by_email(email)
    if user:
        if (not user.get("name")) and name:
            db_client.collection("users").document(str(user["id"])).set({"name": name}, merge=True)
        return user["id"]
        
    row_id = _gen_id()
    role = "admin" if email.lower() in [
        "developer@serviceone.dev", 
        "test@serviceone.dev", 
        "admin@serviceone.dev",
        "saias@serviceone.dev",
        "saias@gmail.com",
        "saiashribad05@gmail.com"
    ] else "user"
    
    doc_data = {
        "id": int(row_id),
        "email": email.lower(),
        "name": name or email.split("@")[0].capitalize(),
        "google_id": email,
        "role": role,
        "language_preference": "en",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    db_client.collection("users").document(str(row_id)).set(doc_data)
    return row_id
