"""
ServiceOne Model Context Protocol (MCP) Server
Exposes PostgreSQL market data safely to Gemini and other LLMs via standardized tool endpoints.
"""
import os
import sys
import json
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP

# Add parent directory to path so config and db can be imported
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from db.database import get_cursor
from config import settings

import redis

# Initialize Redis Client for MCP Caching
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()
    HAS_REDIS = True
except Exception:
    HAS_REDIS = False

# Initialize FastMCP Server
mcp = FastMCP("ServiceOne Market Data MCP Server")

@mcp.tool(name="get_local_pricing_bounds", description="Queries cached market signals and historical runs to find fair price ranges for an appliance service type in a city.")
def get_local_pricing_bounds(city: str, appliance: str, service_type: str) -> str:
    """
    Retrieve fair pricing ranges and market averages.
    
    Args:
        city: City name (e.g., Delhi, Mumbai, Bengaluru)
        appliance: Appliance type (e.g., AC, Fridge, Washing Machine)
        service_type: Service type (e.g., gas_refill, installation, repair)
    """
    # Try Redis L1 cache first
    mcp_cache_key = f"mcp:bounds:{city.lower().replace(' ', '')}:{appliance.lower().replace(' ', '')}:{service_type.lower().replace(' ', '')}"
    if HAS_REDIS:
        try:
            cached_val = redis_client.get(mcp_cache_key)
            if cached_val:
                return cached_val
        except Exception:
            pass

    try:
        with get_cursor() as cur:
            # 1. Search cached market signals
            cur.execute("""
                SELECT avg_price, price_range_min, price_range_max, notes
                FROM cached_market_signals
                WHERE LOWER(city) = LOWER(%s)
                  AND LOWER(appliance) = LOWER(%s)
                  AND LOWER(service_type) = LOWER(%s)
                  AND expires_at > CURRENT_TIMESTAMP
                LIMIT 1;
            """, (city, appliance, service_type))
            row = cur.fetchone()
            
            if row:
                result = {
                    "source": "cached_market_signals",
                    "average_price": float(row["avg_price"]),
                    "price_range_min": float(row["price_range_min"]),
                    "price_range_max": float(row["price_range_max"]),
                    "notes": row["notes"]
                }
                serialized = json.dumps(result, indent=2)
                if HAS_REDIS:
                    try:
                        redis_client.setex(mcp_cache_key, settings.CACHE_TTL_SECONDS, serialized)
                    except Exception:
                        pass
                return serialized
                
            # 2. Try historical quote checks as fallback
            cur.execute("""
                SELECT AVG(quoted_price) as avg_price,
                       MIN(quoted_price) as min_price,
                       MAX(quoted_price) as max_price,
                       COUNT(*) as sample_count
                FROM quote_checks
                WHERE LOWER(city) = LOWER(%s)
                  AND LOWER(appliance) = LOWER(%s)
                  AND LOWER(service_type) = LOWER(%s)
                  AND verdict = 'fair'
                GROUP BY city, appliance, service_type;
            """, (city, appliance, service_type))
            fallback_row = cur.fetchone()
            
            if fallback_row and fallback_row["sample_count"] > 0:
                result = {
                    "source": "historical_quote_checks",
                    "average_price": float(fallback_row["avg_price"]),
                    "price_range_min": float(fallback_row["min_price"]),
                    "price_range_max": float(fallback_row["max_price"]),
                    "sample_count": int(fallback_row["sample_count"]),
                    "notes": f"Based on {fallback_row['sample_count']} historical fair quote checks."
                }
                return json.dumps(result, indent=2)
                
            return json.dumps({
                "status": "no_data",
                "message": f"No pricing data found for {appliance} {service_type} in {city}."
            })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool(name="list_nearby_providers", description="Retrieves verified local appliance service providers registered in a specific city.")
def list_nearby_providers(city: str, appliance: Optional[str] = None) -> str:
    """
    List providers and their ratings/reviews.
    
    Args:
        city: City name
        appliance: Optional appliance type filter
    """
    try:
        with get_cursor() as cur:
            if appliance:
                cur.execute("""
                    SELECT name, area, phone, address, website_url, avg_rating, review_count, is_verified
                    FROM providers
                    WHERE LOWER(city) = LOWER(%s)
                      AND %s = ANY(appliance_types)
                      AND is_active = TRUE
                    ORDER BY avg_rating DESC NULLS LAST
                    LIMIT 10;
                """, (city, appliance))
            else:
                cur.execute("""
                    SELECT name, area, phone, address, website_url, avg_rating, review_count, is_verified
                    FROM providers
                    WHERE LOWER(city) = LOWER(%s)
                      AND is_active = TRUE
                    ORDER BY avg_rating DESC NULLS LAST
                    LIMIT 10;
                """, (city,))
            
            rows = cur.fetchall()
            if rows:
                providers = []
                for row in rows:
                    p = dict(row)
                    # Convert Decimals
                    if p.get("avg_rating"):
                        p["avg_rating"] = float(p["avg_rating"])
                    providers.append(p)
                return json.dumps({"status": "success", "providers": providers}, indent=2)
                
            return json.dumps({
                "status": "no_data",
                "message": f"No service providers registered for {appliance or 'any appliance'} in {city}."
            })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool(name="retrieve_crowdsourced_reports", description="Queries community-submitted and approved quote reports to check real bills submitted by users.")
def retrieve_crowdsourced_reports(city: str, appliance: str, service_type: Optional[str] = None) -> str:
    """
    Get crowdsourced pricing data.
    
    Args:
        city: City name
        appliance: Appliance type
        service_type: Optional service type filter
    """
    try:
        with get_cursor() as cur:
            if service_type:
                cur.execute("""
                    SELECT area, provider_name, quoted_price, notes, created_at
                    FROM community_reports
                    WHERE LOWER(city) = LOWER(%s)
                      AND LOWER(appliance) = LOWER(%s)
                      AND LOWER(service_type) = LOWER(%s)
                      AND approved_status = 'approved'
                    ORDER BY created_at DESC
                    LIMIT 15;
                """, (city, appliance, service_type))
            else:
                cur.execute("""
                    SELECT area, service_type, provider_name, quoted_price, notes, created_at
                    FROM community_reports
                    WHERE LOWER(city) = LOWER(%s)
                      AND LOWER(appliance) = LOWER(%s)
                      AND approved_status = 'approved'
                    ORDER BY created_at DESC
                    LIMIT 15;
                """, (city, appliance))
            
            rows = cur.fetchall()
            if rows:
                reports = []
                for row in rows:
                    r = dict(row)
                    r["quoted_price"] = float(r["quoted_price"])
                    if r.get("created_at"):
                        r["created_at"] = r["created_at"].isoformat()
                    reports.append(r)
                return json.dumps({"status": "success", "reports": reports}, indent=2)
                
            return json.dumps({
                "status": "no_data",
                "message": f"No community-submitted reports found for {appliance} in {city}."
            })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool(name="get_pincode_geo_details", description="Translates a 6-digit Indian PIN code to get its state, city, and list of localities.")
def get_pincode_geo_details(pincode: str) -> str:
    """
    Lookup ZIP/PIN details.
    
    Args:
        pincode: 6-digit PIN code
    """
    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT state, city, locality
                FROM geo_locations
                WHERE pincode = %s
                ORDER BY locality ASC;
            """, (pincode,))
            rows = cur.fetchall()
            
            if rows:
                state = rows[0]["state"]
                city = rows[0]["city"]
                localities = [r["locality"] for r in rows]
                return json.dumps({
                    "status": "success",
                    "pincode": pincode,
                    "state": state,
                    "city": city,
                    "localities": localities
                }, indent=2)
                
            return json.dumps({
                "status": "not_found",
                "message": f"PIN code {pincode} not found in database."
            })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool(name="scrape_live_prices", description="Performs live pricing search on local service websites via TinyFish for an appliance and service type in a city.")
def scrape_live_prices(appliance: str, service: str, city: str, brand: str = "") -> str:
    """
    Search TinyFish index for live rates.
    """
    try:
        from tinyfish_client import get_tinyfish_client
        tf = get_tinyfish_client()
        res = tf.search_service_prices(appliance, service, city, brand)
        return json.dumps(res, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@mcp.tool(name="fetch_nearby_technicians", description="Searches Google Maps Places API for appliance repair technicians near the specified coordinates.")
def fetch_nearby_technicians(lat: float, lng: float, keyword: str) -> str:
    """
    Find nearby appliance technicians via Google Maps.
    """
    try:
        import googlemaps
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            return json.dumps({"status": "missing_api_key", "message": "GOOGLE_MAPS_API_KEY env is not set"})
        gmaps = googlemaps.Client(key=api_key)
        res = gmaps.places_nearby(
            location=(lat, lng),
            radius=15000,
            keyword=keyword
        )
        raw_results = res.get('results', [])
        providers = []
        for r in raw_results[:10]:
            providers.append({
                "name": r.get("name", "Local Service Center"),
                "place_id": r.get("place_id"),
                "address": r.get("vicinity", ""),
                "avg_rating": r.get("rating", 0.0),
                "review_count": r.get("user_ratings_total", 0),
                "lat": r.get("geometry", {}).get("location", {}).get("lat", lat),
                "lng": r.get("geometry", {}).get("location", {}).get("lng", lng)
            })
        return json.dumps({"status": "success", "providers": providers}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    mcp.run()
