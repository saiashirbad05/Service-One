"""
DocumentOcrLifespanAgent — Parses receipt images/documents via Vertex AI and estimates appliance lifespan metrics.
Fully compliant with Google ADK framework.
"""
import os
import json
import logging
from typing import Dict, Any
from google import adk
from google.adk.tools import FunctionTool
from google import genai
from google.genai import types

logger = logging.getLogger("serviceone_api.document_ocr_lifespan_agent")

class DocumentOcrLifespanAgent:
    def __init__(self):
        self.model_name = os.getenv("AGENT_MODEL_FLASH", "gemini-2.5-flash")
        
        # Expose tools to the ADK agent
        self.ocr_tool = FunctionTool(self.parse_receipt_doc)
        self.lifespan_tool = FunctionTool(self.estimate_appliance_lifespan)

        try:
            self.genai_client = genai.Client()
            self.has_genai = True
        except Exception as e:
            logger.warning(f"GenAI Client Init failed in DocumentOcrLifespanAgent: {e}")
            self.has_genai = False

        self.adk_agent = adk.Agent(
            name="DocumentOcrLifespanAgent",
            description="Parses invoice documents and estimates remaining appliance lifespan parameters.",
            instruction=(
                "You are the Document OCR & Lifespan Expert for ServiceOne. "
                "Analyze receipt uploads, extract brand/price/appliance features, and evaluate remaining lifespan ranges."
            ),
            tools=[self.ocr_tool, self.lifespan_tool],
            model=self.model_name
        )

    def parse_receipt_doc(self, file_path: str) -> Dict[str, Any]:
        """
        Runs Vertex AI multimodal analysis to extract invoice fields from a receipt photo or PDF.
        """
        if not self.has_genai or not file_path or not os.path.exists(file_path):
            return {
                "quoted_price": None,
                "provider_name": "Local Mechanic",
                "brand": "Generic",
                "appliance_type": "appliance",
                "status": "failed_or_missing_api"
            }

        try:
            # Load receipt image bytes
            with open(file_path, "rb") as f:
                image_bytes = f.read()

            prompt = (
                "Analyze this appliance service receipt or quote document.\n"
                "Extract the following fields into a raw JSON object (do not wrap in markdown):\n"
                "{\n"
                "  \"quoted_price\": float or null,\n"
                "  \"provider_name\": string or null,\n"
                "  \"brand\": string or null,\n"
                "  \"appliance_type\": string or null (one of: AC, Fridge, Washing Machine, TV, RO, Geyser),\n"
                "  \"detected_parts\": list of strings,\n"
                "  \"detected_services\": list of strings\n"
                "}"
            )

            # Invoke multimodal Gemini
            response = self.genai_client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg"
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            extracted = json.loads(response.text.strip())
            return extracted

        except Exception as e:
            logger.error(f"Multimodal OCR tool failed: {e}")
            return {
                "quoted_price": None,
                "provider_name": "Local Mechanic",
                "brand": "Generic",
                "appliance_type": "appliance",
                "status": "error"
            }

    def estimate_appliance_lifespan(self, appliance: str, brand: str, age_years: float) -> Dict[str, Any]:
        """
        Evaluates remaining appliance lifespan based on typical industry depreciation metrics.
        """
        lifespans = {
            "ac": 10.0,
            "fridge": 14.0,
            "washing machine": 11.0,
            "wm": 11.0,
            "tv": 8.0,
            "ro": 6.0,
            "geyser": 8.0
        }

        app_key = appliance.lower()
        max_lifespan = lifespans.get(app_key, 10.0)
        
        remaining = max(0.0, max_lifespan - age_years)
        depreciation_pct = min(100.0, (age_years / max_lifespan) * 100.0)
        
        if remaining > 5.0:
            recommendation = "Excellent condition. Standard repair is highly cost-effective."
        elif remaining > 2.0:
            recommendation = "Moderate age. Consider repair if quote is low to fair; replace if repair is expensive."
        else:
            recommendation = "End-of-life reached. Replacing the appliance is recommended over expensive repairs."

        return {
            "max_expected_lifespan_years": max_lifespan,
            "remaining_lifespan_years": round(remaining, 1),
            "depreciation_percentage": round(depreciation_pct, 1),
            "replacement_recommendation": recommendation
        }

    async def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Public runner method matching the sub-agent interface.
        """
        ocr_res = self.parse_receipt_doc(file_path)
        
        appliance = ocr_res.get("appliance_type") or "AC"
        brand = ocr_res.get("brand") or "Generic"
        
        lifespan_res = self.estimate_appliance_lifespan(appliance, brand, 4.0) # Default age 4 years for fallback
        ocr_res["lifespan"] = lifespan_res
        
        return ocr_res
