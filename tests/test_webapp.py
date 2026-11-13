import pytest
from webapp import app
from database.init_db import init_database

@pytest.fixture
def client():
    app.config["TESTING"] = True
    init_database()
    with app.test_client() as client:
        yield client

def test_dashboard_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert b"WebPulse" in response.data

def test_websites_route(client):
    response = client.get("/websites")
    assert response.status_code == 200
    assert b"Monitored Websites" in response.data

def test_incidents_route(client):
    response = client.get("/incidents")
    assert response.status_code == 200
    assert b"Incidents" in response.data

def test_analytics_route(client):
    response = client.get("/analytics")
    assert response.status_code == 200
    assert b"Analytics" in response.data

def test_settings_route(client):
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"Settings" in response.data

def test_api_latency_data(client):
    response = client.get("/api/latency-data")
    assert response.status_code == 200
    data = response.get_json()
    assert "labels" in data
    assert "values" in data

def test_api_uptime_data(client):
    response = client.get("/api/uptime-data")
    assert response.status_code == 200
    data = response.get_json()
    assert "labels" in data
    assert "values" in data
