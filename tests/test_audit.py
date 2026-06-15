import os
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.pii import hash_user_id

AUDIT_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))


def test_audit_logs() -> None:
    # Clear audit logs
    if AUDIT_PATH.exists():
        try:
            AUDIT_PATH.unlink()
        except Exception:
            pass

    client = TestClient(app)
    response = client.post(
        "/chat",
        json={
            "user_id": "u_audit_88",
            "session_id": "s_audit_88",
            "feature": "summary",
            "message": "Audit my email secret@domain.com please."
        }
    )
    assert response.status_code == 200
    
    assert AUDIT_PATH.exists()
    lines = AUDIT_PATH.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 0
    
    found_completed = False
    for line in lines:
        if not line.strip():
            continue
        record = json.loads(line)
        
        # Verify schema
        assert "ts" in record
        assert "event" in record
        assert "user_id_hash" in record
        assert "session_id" in record
        assert "correlation_id" in record
        assert "payload" in record
        
        # Assert no raw user ID
        assert "u_audit_88" not in json.dumps(record)
        
        # Assert PII scrubbed (the email in message payload)
        if "chat.request.received" in record["event"]:
            preview = record["payload"].get("message_preview", "")
            assert "secret@domain.com" not in preview
            assert "REDACTED_EMAIL" in preview
            
        if "chat.request.completed" in record["event"]:
            found_completed = True
            
    assert found_completed
