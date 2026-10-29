from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src import api_routes
from src.database import Database


@pytest.fixture
def api(monkeypatch, tmp_path):
    app = FastAPI()
    database = Database(tmp_path / "api.db")
    monkeypatch.setattr(api_routes, "cl", SimpleNamespace(server=SimpleNamespace(app=app)))
    monkeypatch.setattr(api_routes, "_database", None)
    monkeypatch.setattr(api_routes, "_chat_service_getter", None)
    api_routes.register_api_routes(database, lambda: SimpleNamespace(start_chat=lambda: "new-chat"))
    return TestClient(app), database


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/chats/missing/messages"),
        ("post", "/api/chats/missing/fork"),
        ("post", "/api/chats/missing/end"),
        ("post", "/api/chats/missing/reactivate"),
        ("post", "/api/chats/missing/consolidate"),
        ("delete", "/api/chats/missing"),
        ("post", "/api/documents/missing/deactivate"),
        ("post", "/api/documents/missing/activate"),
        ("delete", "/api/documents/missing"),
        ("post", "/api/memories/missing/deactivate"),
        ("post", "/api/memories/missing/activate"),
        ("delete", "/api/memories/missing"),
        ("get", "/api/retrieval-logs/missing/0"),
    ],
)
def test_missing_resources_return_http_404(api, method, path):
    client, _ = api
    response = getattr(client, method)(path)
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}
    assert not response.is_success  # Same 2xx condition as browser fetch Response.ok.


@pytest.mark.parametrize(
    "path,operation",
    [
        ("/api/chats", "list_chats"),
        ("/api/documents", "list_all_documents"),
        ("/api/memories", "list_all_memories"),
    ],
)
def test_database_errors_return_http_500(api, monkeypatch, path, operation):
    client, database = api

    def fail(**kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(database, operation, fail)
    response = client.get(path)
    assert response.status_code == 500
    assert response.json() == {"error": "database unavailable"}
    assert not response.is_success


def test_success_payloads_are_preserved(api):
    client, database = api
    database.create_chat("existing")
    database.save_message("existing", "user", "synthetic test message")
    response = client.get("/api/chats/existing/messages")
    assert response.status_code == 200
    assert response.json()[0]["content"] == "synthetic test message"
    response = client.post("/api/chats")
    assert response.status_code == 200
    assert response.json() == {"chat_id": "new-chat"}


def test_invalid_log_path_returns_http_400(api):
    client, _ = api
    response = client.get("/api/chats/invalid..id/consolidation-log")
    assert response.status_code == 400
    assert response.json() == {"error": "invalid chat_id"}
