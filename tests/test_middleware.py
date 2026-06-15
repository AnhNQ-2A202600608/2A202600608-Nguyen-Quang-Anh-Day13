import uuid
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from structlog.contextvars import get_contextvars
from app.middleware import CorrelationIdMiddleware

# Setup dummy app to test middleware
test_app = FastAPI()
test_app.add_middleware(CorrelationIdMiddleware)


@test_app.get("/test-endpoint")
async def test_endpoint(request: Request):
    ctx = get_contextvars()
    return {
        "correlation_id_in_state": getattr(request.state, "correlation_id", None),
        "correlation_id_in_context": ctx.get("correlation_id")
    }


def test_middleware_generates_new_id() -> None:
    client = TestClient(test_app)
    response = client.get("/test-endpoint")
    assert response.status_code == 200
    
    # 1. Header is present in response
    assert "x-request-id" in response.headers
    assert "x-response-time-ms" in response.headers
    
    req_id = response.headers["x-request-id"]
    assert req_id.startswith("req-")
    assert len(req_id) == 12 # req- + 8 hex
    
    # 2. Assert values in request state and context
    data = response.json()
    assert data["correlation_id_in_state"] == req_id
    assert data["correlation_id_in_context"] == req_id


def test_middleware_preserves_incoming_id() -> None:
    client = TestClient(test_app)
    custom_id = "req-abcdef12"
    response = client.get("/test-endpoint", headers={"x-request-id": custom_id})
    assert response.status_code == 200
    
    # Assert preserved
    assert response.headers["x-request-id"] == custom_id
    data = response.json()
    assert data["correlation_id_in_state"] == custom_id
    assert data["correlation_id_in_context"] == custom_id


def test_context_cleared_after_request() -> None:
    client = TestClient(test_app)
    client.get("/test-endpoint")
    
    # After request completes, the contextvars must be clear of correlation_id
    ctx = get_contextvars()
    assert "correlation_id" not in ctx
