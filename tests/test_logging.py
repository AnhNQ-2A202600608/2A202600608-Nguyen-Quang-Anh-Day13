import os
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.pii import hash_user_id

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))


def test_logs_schema_and_enrichment() -> None:
    # Clear logs first
    if LOG_PATH.exists():
        try:
            LOG_PATH.unlink()
        except Exception:
            pass

    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "user_id": "u_test_99",
            "session_id": "s_test_99",
            "feature": "qa",
            "message": "Verify logging schema and enrichment."
        }
    )
    assert response.status_code == 200
    
    # Read generated logs.jsonl
    assert LOG_PATH.exists()
    lines = LOG_PATH.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 0
    
    found_chat_req = False
    for line in lines:
        if not line.strip():
            continue
        record = json.loads(line)
        
        # Verify required schema fields
        assert "ts" in record
        assert "level" in record
        assert "service" in record
        assert "event" in record
        
        # Verify specific api fields
        if record.get("service") == "api":
            assert "correlation_id" in record
            assert record["correlation_id"] != "MISSING"
            assert "user_id_hash" in record
            assert "session_id" in record
            assert "feature" in record
            assert "model" in record
            
            # Assert no raw user_id is ever logged
            assert "user_id" not in record
            for val in record.values():
                if isinstance(val, str):
                    assert "u_test_99" not in val
            
            # Assert user_id_hash is correctly set
            assert record["user_id_hash"] == hash_user_id("u_test_99")
            found_chat_req = True
            
    assert found_chat_req
