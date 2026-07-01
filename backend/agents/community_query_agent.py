import os
import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from google.cloud import firestore
from google import adk

try:
    from google import genai
    from google.genai import types
    genai_client = genai.Client()
except Exception as e:
    genai_client = None

logger = logging.getLogger("serviceone_api.community_query_agent")

router = APIRouter()

# Initialize Firestore
db = firestore.Client(project="service-one-platform")

# Declare RAG Synthesis Agent using Google ADK
synthesis_agent = adk.Agent(
    name="CommunityQueryAgent",
    description="Service-One's Community Intelligence Agent for India.",
    instruction=(
        "You are Service-One's Community Intelligence Agent for India. "
        "You answer questions about home appliance repair pricing using ONLY the real community-submitted invoice data provided. "
        "Rules you must follow:\n"
        "1. Always mention the specific city and appliance in your answer.\n"
        "2. Always give price ranges in Indian Rupees (₹).\n"
        "3. If the data has fewer than 5 records, explicitly note that it is based on limited inputs.\n"
        "4. If a price in the data seems unusually high (e.g. PCB repair above ₹7,000 or general inspection above ₹1,500), flag it as suspicious.\n"
        "5. Keep your answer strictly to 2-3 sentences max.\n"
        "6. Never mention Firestore, databases, JSON, prompts, or technical internals in your answer."
    ),
    model=os.getenv("AGENT_MODEL_FLASH", "gemini-2.5-flash")
)

# Known entities for instant local parameter extraction
CITIES = ["Mumbai", "Bangalore", "Delhi", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad"]
APPLIANCES = ["AC", "Washing Machine", "Refrigerator", "Television", "Microwave", "Geyser", "Dishwasher", "Laptop"]

class QueryRequest(BaseModel):
    query: str
    city: Optional[str] = None
    appliance: Optional[str] = None

@router.post("/api/community-query")
async def community_query(body: QueryRequest):
    try:
        resolved_city = None
        resolved_appliance = None
        
        # Step 1: Instant local keyword matching for extraction
        query_lower = body.query.lower()
        
        for c in CITIES:
            if c.lower() in query_lower:
                resolved_city = c
                break
                
        for a in APPLIANCES:
            if a.lower() in query_lower:
                resolved_appliance = a
                break
        
        if not resolved_appliance:
            if "washing" in query_lower:
                resolved_appliance = "Washing Machine"
            elif "fridge" in query_lower:
                resolved_appliance = "Refrigerator"
            elif "tv" in query_lower:
                resolved_appliance = "Television"
                
        if not resolved_city:
            resolved_city = body.city or "Mumbai"
        if not resolved_appliance:
            resolved_appliance = body.appliance or "AC"
            
        resolved_city = resolved_city.strip().title()
        resolved_appliance = resolved_appliance.strip()
        
        # Step 2: Generate Query Embedding
        query_embedding = None
        if genai_client:
            try:
                embed_res = genai_client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=body.query
                )
                query_embedding = embed_res.embeddings[0].values
            except Exception as ee:
                logger.warning(f"Failed to generate query embedding: {ee}")
                
        # Step 3: Perform Firestore Native Vector Search with Relational Fallback
        reports = []
        if query_embedding:
            try:
                from google.cloud.firestore_v1.vector import Vector
                from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
                
                docs = db.collection("community_reports") \
                         .find_nearest(
                             vector_field="embedding",
                             query_vector=Vector(query_embedding),
                             distance_measure=DistanceMeasure.COSINE,
                             limit=20
                         ).stream()
                for doc in docs:
                    reports.append(doc.to_dict())
            except Exception as ve:
                logger.warning(f"Firestore vector search failed or index building: {ve}")
                
        # Relational fallback
        if not reports:
            docs = db.collection("community_reports") \
                     .where("city", "==", resolved_city) \
                     .stream()
            for doc in docs:
                data = doc.to_dict()
                app_field = data.get("appliance_type") or data.get("appliance")
                if app_field and app_field.lower() == resolved_appliance.lower():
                    reports.append(data)
            reports = reports[:20]
        
        if not reports:
            return {
                "answer": f"No community data available yet for {resolved_appliance} in {resolved_city}. Be the first to submit a report!",
                "data_points_used": 0,
                "city": resolved_city,
                "appliance": resolved_appliance
            }
            
        # Step 3: Context Assembly
        context_lines = []
        for r in reports:
            service = r.get("service_type") or "repair"
            price = r.get("quoted_price")
            verdict = r.get("verdict", "fair")
            pincode = r.get("pincode", "Unknown")
            context_lines.append(
                f"- {resolved_appliance} {service}: ₹{price} ({verdict}) in {resolved_city}, Pincode: {pincode}"
            )
        context_string = "\n".join(context_lines)
        
        # Step 4: Run Direct Generation using synthesis_agent parameters (Optimizes latency to <1s)
        # Calculate mathematical pricing fallbacks in case AI is offline or rate-limited
        prices = [r.get("quoted_price") for r in reports if r.get("quoted_price")]
        if prices:
            avg_p = int(sum(prices) / len(prices))
            min_p = min(prices)
            max_p = max(prices)
            fallback_answer = (
                f"Based on our crowdsourced invoices for {resolved_appliance} in {resolved_city}, "
                f"the typical repair price ranges from ₹{min_p} to ₹{max_p} (averaging around ₹{avg_p})."
            )
        else:
            fallback_answer = f"Our community database records standard repair costs for {resolved_appliance} in {resolved_city} as stable."
            
        answer = fallback_answer
        user_message = (
            f"Community invoice data:\n{context_string}\n\n"
            f"User's question: {body.query}\n\n"
            f"Answer the user's question clearly and factually using only the data above."
        )
        
        if genai_client:
            try:
                response = genai_client.models.generate_content(
                    model=synthesis_agent.model,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=synthesis_agent.instruction,
                        temperature=0.3,
                        max_output_tokens=200,
                        safety_settings=[
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                            ),
                        ]
                    )
                )
                answer = response.text.strip()
            except Exception as ge:
                logger.error(f"Direct Gemini call failed: {ge}")
                # Keep the computed mathematical fallback rather than showing offline message
                answer = fallback_answer
        
        # Serialize top 5 reports for UI display
        serialized_reports = []
        for r in reports[:5]:
            serialized_reports.append({
                "service_type": r.get("service_type"),
                "quoted_price": r.get("quoted_price"),
                "verdict": r.get("verdict"),
                "pincode": r.get("pincode")
            })
            
        return {
            "answer": answer,
            "data_points_used": len(reports),
            "reports": serialized_reports,
            "city": resolved_city,
            "appliance": resolved_appliance
        }
    except Exception as e:
        logger.error(f"Fatal error in community query agent: {e}")
        return {
            "answer": "Concierge dashboard is unable to answer queries at this time.",
            "data_points_used": 0,
            "city": body.city or "Unknown",
            "appliance": body.appliance or "Unknown"
        }
