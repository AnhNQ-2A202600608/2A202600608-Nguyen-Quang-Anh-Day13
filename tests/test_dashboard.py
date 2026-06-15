from fastapi.testclient import TestClient
from app.main import app


def test_dashboard_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Day 13 Observability Dashboard" in response.text
    assert "chart-latency" in response.text


def test_metrics_history_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/metrics/history")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    
    data = response.json()
    assert isinstance(data, list)
