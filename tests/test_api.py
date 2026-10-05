"""REST API testleri: kimlik doğrulama, yetkilendirme ve onay akışı."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

import src.api as api
from tests.conftest import leave_responder, next_monday

MUHAMMET = {"Authorization": "Bearer demo-token-e001"}
DILAN = {"Authorization": "Bearer demo-token-e003"}


@pytest.fixture
def client(db, fake_llm, monkeypatch):
    start = next_monday(30)
    fake_llm(leave_responder(start, start + timedelta(days=1)))
    monkeypatch.setattr(api, "retrieve", lambda *a, **k: [])  # embedding modelini yükleme
    api.graphs.clear()
    api.thread_owners.clear()
    with TestClient(api.app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_requires_token(client):
    assert client.post("/chat", json={"message": "merhaba"}).status_code == 401


def test_rejects_invalid_token(client):
    headers = {"Authorization": "Bearer sahte-token"}
    assert client.post("/chat", json={"message": "merhaba"}, headers=headers).status_code == 401


def test_me_returns_token_owner(client):
    assert client.get("/me", headers=MUHAMMET).json()["id"] == "E001"


def test_rejects_empty_message(client):
    assert client.post("/chat", json={"message": ""}, headers=MUHAMMET).status_code == 422


def test_simple_chat(client):
    body = client.post("/chat", json={"message": "merhaba"}, headers=MUHAMMET).json()
    assert body["status"] == "completed"
    assert body["reply"]


def test_approval_flow(client):
    body = client.post("/chat", json={"message": "izin istiyorum"}, headers=MUHAMMET).json()
    assert body["status"] == "approval_required"
    assert "Pazartesi" in body["pending_actions"][0]

    thread = body["thread_id"]
    body = client.post(f"/chat/{thread}/approval", json={"approved": True}, headers=MUHAMMET).json()
    assert body["status"] == "completed"
    assert "BAŞARILI" in body["reply"]


def test_cannot_send_message_while_approval_pending(client):
    thread = client.post("/chat", json={"message": "izin istiyorum"}, headers=MUHAMMET).json()["thread_id"]
    response = client.post("/chat", json={"message": "merhaba", "thread_id": thread}, headers=MUHAMMET)
    assert response.status_code == 409


def test_cannot_access_other_employees_thread(client):
    thread = client.post("/chat", json={"message": "izin istiyorum"}, headers=MUHAMMET).json()["thread_id"]
    assert client.post(f"/chat/{thread}/approval", json={"approved": True}, headers=DILAN).status_code == 404
    assert client.post("/chat", json={"message": "x", "thread_id": thread}, headers=DILAN).status_code == 404


def test_approval_without_pending_action(client):
    thread = client.post("/chat", json={"message": "merhaba"}, headers=MUHAMMET).json()["thread_id"]
    response = client.post(f"/chat/{thread}/approval", json={"approved": True}, headers=MUHAMMET)
    assert response.status_code == 409

    # tests/test_api.py dosyasının SONUNA eklenecek testler
def test_dashboard_shows_balance(client):
    body = client.get("/me/dashboard", headers=MUHAMMET).json()
    assert body["profile"]["name"] == "Muhammet Boğa"
    assert body["balance"]["kalan"] == 14


def test_dashboard_reflects_new_request(client):
    thread = client.post("/chat", json={"message": "izin istiyorum"}, headers=MUHAMMET).json()["thread_id"]
    client.post(f"/chat/{thread}/approval", json={"approved": True}, headers=MUHAMMET)
    body = client.get("/me/dashboard", headers=MUHAMMET).json()
    assert body["balance"]["onay_bekleyen"] == 2
    assert body["requests"][0]["status"] == "onay_bekliyor"


def test_web_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Onayınız gerekiyor" in response.text