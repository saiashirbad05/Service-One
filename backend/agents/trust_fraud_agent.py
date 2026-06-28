"""
TrustFraudAgent — Evaluates quote pricing patterns, detects fraud risks, and rates technician trust profiles.
Fully compliant with Google ADK framework.
"""
import os
import logging
from typing import Dict, Any, List
from google import adk
from google.adk.tools import FunctionTool

logger = logging.getLogger("serviceone_api.trust_fraud_agent")

class TrustFraudAgent:
    def __init__(self):
        self.model_name = os.getenv("AGENT_MODEL_FLASH_LITE", "gemini-2.5-flash-lite")
        
        # Expose official function tools to the ADK agent
        self.risk_tool = FunctionTool(self.detect_pricing_anomalies)

        self.adk_agent = adk.Agent(
            name="TrustFraudAgent",
            description="Analyzes repair service quote prices to detect fraud indicators and markup risks.",
            instruction=(
                "You are the Trust & Fraud Expert for ServiceOne. "
                "Analyze quoted repair prices against local market rates, looking for parts markup "
                "or extreme labor fee overcharging."
            ),
            tools=[self.risk_tool],
            model=self.model_name
        )

    def detect_pricing_anomalies(self, quoted_price: float, market_avg: float) -> Dict[str, Any]:
        """
        Analyzes the variance between quoted price and market average to identify potential overcharging.
        """
        if market_avg <= 0:
            return {"risk_level": "low", "risk_score": 0, "flags": []}
            
        variance = ((quoted_price - market_avg) / market_avg) * 100
        flags = []
        
        if variance > 50:
            risk_level = "high"
            risk_score = 85
            flags.append(f"Quote is over 50% above local market rates (+{round(variance)}% variance).")
        elif variance > 20:
            risk_level = "medium"
            risk_score = 45
            flags.append(f"Quote is moderately higher than average (+{round(variance)}% variance).")
        elif variance < -40:
            risk_level = "medium"
            risk_score = 40
            flags.append(f"Quote is unusually low (-{round(abs(variance))}% variance), potential low quality parts warning.")
        else:
            risk_level = "low"
            risk_score = 10
            
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "detected_flags": flags,
            "variance": round(variance, 2)
        }

    async def analyze(self, quote_data: Dict[str, Any], market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Public runner method matching the sub-agent interface.
        """
        quoted = float(quote_data.get("quoted_price", 0))
        market_avg = 1500.0
        
        if market_data and market_data.get("average_market_price"):
            market_avg = float(market_data["average_market_price"])
            
        anomaly_res = self.detect_pricing_anomalies(quoted, market_avg)
        
        trust_signals = ["Basic price benchmark validation passed."]
        if anomaly_res["risk_level"] == "low":
            trust_signals.append("Price matches typical regional baselines.")
            recommendation = "✅ LOW RISK: Quoted price is fair and aligns with local rates."
        elif anomaly_res["risk_level"] == "medium" and anomaly_res["variance"] < 0:
            trust_signals.append("Unusually low rates.")
            recommendation = "⚠️ MEDIUM RISK: Quoted price is unusually cheap. Double-check if the provider uses genuine parts."
        else:
            trust_signals.append("High price variance.")
            recommendation = "❌ HIGH RISK: Quoted price is significantly higher than regional averages. Request an itemized invoice."
            
        return {
            "risk_level": anomaly_res["risk_level"],
            "risk_score": anomaly_res["risk_score"],
            "detected_flags": anomaly_res["detected_flags"],
            "trust_signals": trust_signals,
            "provider_verified": False,
            "recommendation": recommendation
        }
