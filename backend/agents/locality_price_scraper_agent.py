"""
LocalityPriceScraperAgent — Combines Web Scraping, Data Cleaning, and Fallback pricing calculations.
Exposes tools to fetch live pricing and clean scraped anomalies.
Fully compliant with Google ADK framework.
"""
import os
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from google import adk
from google.adk.tools import FunctionTool
from google import genai
from google.genai import types

from tinyfish_client import get_tinyfish_client

try:
    from db.database import get_cached_signal, save_cached_signal
    HAS_DB = True
except ImportError:
    HAS_DB = False

logger = logging.getLogger("serviceone_api.locality_price_scraper_agent")

class LocalityPriceScraperAgent:
    def __init__(self):
        self.model_name = os.getenv("AGENT_MODEL_FLASH_LITE", "gemini-2.5-flash-lite")
        self.tf = get_tinyfish_client()
        
        # Define the primary ADK Function Tools
        self.scrape_tool = FunctionTool(self.scrape_live_prices)
        self.clean_tool = FunctionTool(self.clean_and_filter_prices)
        
        # Initialize Google GenAI client if available
        try:
            self.genai_client = genai.Client()
            self.has_genai = True
        except Exception as e:
            logger.warning(f"GenAI Client Init failed in LocalityPriceScraperAgent: {e}")
            self.has_genai = False

        self.adk_agent = adk.Agent(
            name="LocalityPriceScraperAgent",
            description="Scrapes live appliance repair market rates and cleans raw data anomalies.",
            instruction=(
                "You are the Locality Pricing & Web Scraping Auditor for ServiceOne. "
                "Use the provided tools to fetch live market rates from online directories "
                "and clean raw data outliers. Provide calculated average pricing and fair ranges."
            ),
            tools=[self.scrape_tool, self.clean_tool],
            model=self.model_name
        )

    def scrape_live_prices(self, appliance: str, service: str, city: str, brand: str = "") -> Dict[str, Any]:
        """
        Scrapes live market prices using TinyFish Search and extracts pricing signals.
        """
        logger.info(f"Scraping live prices: appliance={appliance}, service={service}, city={city}, brand={brand}")
        try:
            search_data = self.tf.search_service_prices(appliance, service, city, brand)
            results = search_data.get("results", [])
            source_links = search_data.get("source_links", [])
            
            snippet_prices = self.tf.extract_prices_from_results(results)
            
            return {
                "raw_results": results[:5],
                "snippet_prices": snippet_prices,
                "source_links": source_links[:5],
                "status": "success"
            }
        except Exception as e:
            logger.error(f"TinyFish scraper tool failure: {e}")
            return {"status": "error", "message": str(e), "snippet_prices": []}

    def clean_and_filter_prices(self, prices: List[float], appliance: str, service: str) -> List[float]:
        """
        Cleans pricing signals by removing outliers and checking baseline bounds for standard appliance repair.
        """
        ranges = {
            "ac": (200, 15000),
            "fridge": (300, 12000),
            "washing machine": (200, 10000),
            "wm": (200, 10000),
            "tv": (300, 15000),
            "ro": (150, 5000),
            "geyser": (200, 8000),
        }
        
        appliance_lower = appliance.lower()
        min_price, max_price = ranges.get(appliance_lower, (100, 20000))
        
        if "install" in service.lower():
            max_price *= 1.5
            
        cleaned = [p for p in prices if min_price <= p <= max_price]
        return sorted(list(set(cleaned)))

    def calculate_fallback_pricing(self, appliance: str, service: str, brand: str, city: str) -> Dict[str, Any]:
        """
        Performs mathematical offline pricing multiplier backup calculations when live scrape has 0 results.
        """
        baselines = {
            "ac": {"repair": 1500, "install": 2500, "service": 800, "gas refill": 2200, "pcb repair": 3500, "deep cleaning": 1200, "cooling issue": 1800},
            "fridge": {"repair": 1800, "service": 600, "compressor repair": 4500, "gas refill": 2500, "thermostat fix": 1200},
            "washing machine": {"repair": 1500, "service": 500, "motor repair": 3500, "drum repair": 2800, "bearing fix": 1600},
            "wm": {"repair": 1500, "service": 500, "motor repair": 3500, "drum repair": 2800, "bearing fix": 1600},
            "tv": {"repair": 2500, "service": 800, "panel repair": 6000, "backlight repair": 3000, "pcb / board fix": 3500},
            "ro": {"repair": 800, "service": 400, "filter replacement": 1500, "membrane change": 2500, "motor repair": 1800},
            "geyser": {"repair": 1200, "install": 1800, "element replacement": 1500, "thermostat fix": 1000},
        }
        
        appliance_lower = appliance.lower()
        service_lower = service.lower()
        
        appliance_prices = baselines.get(appliance_lower, {"repair": 1500})
        base = appliance_prices.get(service_lower)
        if base is None:
            for s_key, s_val in appliance_prices.items():
                if s_key in service_lower or service_lower in s_key:
                    base = s_val
                    break
        if base is None:
            base = appliance_prices.get("repair", 1500)
            
        # Apply brand multiplier
        brand_lower = brand.lower() if brand else ""
        premium_brands = ["daikin", "mitsubishi", "o general", "siemens", "bosch", "apple", "sony", "carrier", "ao smith"]
        value_brands = ["samsung", "lg", "voltas", "blue star", "hitachi", "panasonic", "lloyd", "whirlpool", "godrej", "haier", "ifb", "kent", "aquaguard"]
        
        if any(b in brand_lower for b in premium_brands):
            brand_mult = 1.25
        elif any(b in brand_lower for b in value_brands):
            brand_mult = 1.10
        else:
            brand_mult = 0.95
            
        # Apply city tier multiplier
        metro_cities = ["mumbai", "delhi", "bangalore", "bengaluru", "chennai", "hyderabad", "kolkata", "pune", "gurgaon", "noida", "ghaziabad"]
        if any(metro in city.lower() for metro in metro_cities):
            city_mult = 1.20
        else:
            city_mult = 0.95
            
        combined_base = int(base * brand_mult * city_mult)
        
        return {
            "average_market_price": combined_base,
            "price_range": [round(combined_base * 0.85), round(combined_base * 1.15)],
            "all_prices_found": [round(combined_base * 0.9), combined_base, round(combined_base * 1.1)],
            "sources_scraped": 0,
            "sources": [],
            "provider_suggestions": [],
            "status": "fallback_estimation",
            "notes": "No live crawler matches found. Pricing modeled based on historical regional baselines."
        }

    async def analyze(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Public runner method matching the sub-agent interface.
        """
        appliance = quote_data.get("appliance_type", "ac")
        service = quote_data.get("service_type", "repair")
        brand = quote_data.get("brand", "")
        city = quote_data.get("user_zip_code", "Delhi")
        
        # 1. Try cache check
        cache_key = f"{appliance.lower()}:{service.lower()}:{city.lower()}"
        if brand:
            cache_key += f":{brand.lower()}"
            
        if HAS_DB:
            try:
                cached = get_cached_signal(cache_key)
                if cached:
                    logger.info(f"LocalityPriceScraperAgent Cache HIT for {cache_key}")
                    return {
                        "average_market_price": float(cached["avg_price"]),
                        "price_range": [float(cached["price_range_min"]), float(cached["price_range_max"])],
                        "sources": json.loads(cached["sources_json"]) if isinstance(cached["sources_json"], str) else cached["sources_json"],
                        "provider_suggestions": json.loads(cached["provider_suggestions"]) if isinstance(cached["provider_suggestions"], str) else cached["provider_suggestions"],
                        "status": "cached",
                        "notes": "Served from local Postgres cache layer."
                    }
            except Exception as e:
                logger.error(f"Postgres cache check error: {e}")

        # 2. Run Scraping & Cleaning Tools
        scrape_res = self.scrape_live_prices(appliance, service, city, brand)
        prices = scrape_res.get("snippet_prices", [])
        
        cleaned_prices = self.clean_and_filter_prices(prices, appliance, service)
        
        if cleaned_prices:
            avg_price = sum(cleaned_prices) / len(cleaned_prices)
            result = {
                "average_market_price": round(avg_price),
                "price_range": [cleaned_prices[0], cleaned_prices[-1]],
                "all_prices_found": cleaned_prices,
                "sources_scraped": len(scrape_res.get("raw_results", [])),
                "sources": scrape_res.get("source_links", []),
                "provider_suggestions": [],
                "status": "success",
                "notes": f"Successfully scraped and cleaned live pricing data."
            }
        else:
            result = self.calculate_fallback_pricing(appliance, service, brand, city)
            
        # Cache results if available
        if HAS_DB:
            try:
                save_cached_signal({
                    "cache_key": cache_key,
                    "city": city,
                    "appliance": appliance,
                    "service_type": service,
                    "brand": brand or None,
                    "avg_price": result["average_market_price"],
                    "price_range_min": result["price_range"][0],
                    "price_range_max": result["price_range"][1],
                    "sources_json": json.dumps(result.get("sources", [])),
                    "provider_suggestions": json.dumps(result.get("provider_suggestions", [])),
                    "raw_scraped_data": json.dumps(result.get("all_prices_found", [])),
                    "expires_at": (datetime.now() + timedelta(hours=2)).isoformat(),
                })
            except Exception as e:
                logger.error(f"Postgres cache save error: {e}")
                
        return result
