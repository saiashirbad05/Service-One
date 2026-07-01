import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_forecast_trend_endpoint():
    response = client.get("/api/forecast/trend?appliance=AC&city=Mumbai")
    assert response.status_code == 200
    data = response.json()
    assert "trend" in data
    assert "forecast" in data
    assert data["appliance"] == "AC"
    assert data["city"] == "Mumbai"

def test_community_query_endpoint():
    payload = {
        "query": "What is the typical price for washing machine drum issues in Bangalore?",
        "city": "Bangalore",
        "appliance": "Washing Machine"
    }
    response = client.post("/api/community-query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "data_points_used" in data
    assert "city" in data
    assert "appliance" in data
