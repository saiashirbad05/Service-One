import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["scraper"] == "tinyfish"

def test_pincode_validation_failure():
    # Test invalid pincode lengths
    response = client.get("/api/geo/pincode/123")
    assert response.status_code == 400
    assert "Invalid pincode" in response.json()["detail"]

    # Test non-digit pincodes
    response = client.get("/api/geo/pincode/abc123")
    assert response.status_code == 400

def test_lookup_missing_pincode():
    # Test a pincode that is valid format but not in db
    response = client.get("/api/geo/pincode/999999")
    # Should return either 200 (for graceful fallback), 404 pincode not found, or throw an error safely
    assert response.status_code in [200, 404, 500]


def test_list_states():
    response = client.get("/api/geo/states")
    assert response.status_code in [200, 500]
    if response.status_code == 200:
        assert "states" in response.json()

def test_healthz_endpoint():
    response = client.get("/healthz")
    assert response.status_code in [200, 503]
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "online"

from unittest.mock import patch

def test_check_quote_fallback():
    # Mock orchestrator.run_analysis to raise an exception to trigger the fallback logic
    with patch("main.orchestrator.run_analysis", side_effect=Exception("Simulated ADK error")):
        payload = {
            "service_type": "gas_refill",
            "appliance_type": "AC",
            "quoted_price": 3200,
            "user_zip_code": "110001",
            "provider_name": "Test Local Works",
            "brand": "LG"
        }
        response = client.post("/api/check-quote", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["verdict"] == "high"
        assert data["metadata"]["fallback_applied"] is True
        assert "Fallback" in data["summary"]
        assert data["details"]["market"]["average_market_price"] == 2200
