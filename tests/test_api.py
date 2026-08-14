import os
os.environ.setdefault("GROQ_API_KEY", "dummy_key_for_tests")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200


def test_chat_rejects_empty_message():
    r = client.post("/chat", json={"conversation_id": "test", "message": ""})
    assert r.status_code == 422


def test_conversation_not_found():
    r = client.get("/conversations/does-not-exist-xyz")
    assert r.status_code == 404