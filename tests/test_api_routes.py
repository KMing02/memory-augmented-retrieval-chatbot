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


def test_rest_end_chat_flushes_memory_and_finalizes_gist_before_transition(api, monkeypatch):
    from src.memory.short_term import ChatEndMemoryProcessingResult

    client, database = api
    database.create_chat("chat")
    database.save_message("chat", "user", "Synthetic project marker is cobalt.")
    database.save_message("chat", "assistant", "Recorded.")
    calls = []

    def flush(chat_id):
        assert database.is_chat_active(chat_id)
        calls.append(chat_id)
        return ChatEndMemoryProcessingResult(2, 1)

    monkeypatch.setattr(
        api_routes,
        "_chat_service_getter",
        lambda: SimpleNamespace(memory=SimpleNamespace(process_all_for_chat_end=flush)),
    )
    assert client.post("/api/chats/chat/end").status_code == 200
    assert not database.is_chat_active("chat")
    assert len(database.chat_gists_for_chat("chat", "previous_chat_gist")) == 1
    assert calls == ["chat"]
    assert client.post("/api/chats/chat/end").status_code == 200
    assert calls == ["chat"]


def test_rest_end_failure_keeps_chat_active(api, monkeypatch):
    client, database = api
    database.create_chat("chat")

    def fail(chat_id):
        raise RuntimeError("synthetic extraction failure")

    monkeypatch.setattr(
        api_routes,
        "_chat_service_getter",
        lambda: SimpleNamespace(memory=SimpleNamespace(process_all_for_chat_end=fail)),
    )
    assert client.post("/api/chats/chat/end").status_code == 500
    assert database.is_chat_active("chat")


def test_rest_memory_changes_keep_real_vector_and_snapshot_state_consistent(api, monkeypatch):
    import json
    from src.core.contracts import SourcePlan
    from src.memory.long_term_store import SQLiteLongTermMemoryStore, LongTermMemoryWrite
    from src.memory.long_term_vector_index import LongTermMemoryVectorIndex
    from src.memory.structured_memory_vector_sync import StructuredMemoryVectorSync
    from src.retrieval.structured_memory_retriever import StructuredMemoryRetriever

    client, database = api
    database.create_chat("chat")

    class Embeddings:
        def embed_query(self, text):
            return [1.0] + [0.0] * 383

    monkeypatch.setattr(LongTermMemoryVectorIndex, "_embeddings", lambda self: Embeddings())
    index = LongTermMemoryVectorIndex(database=database)
    store = SQLiteLongTermMemoryStore(database, vector_sync=StructuredMemoryVectorSync(index))
    write = LongTermMemoryWrite(
        namespace=("memory", "user_preferences"),
        memory_id="user_preferences:language",
        category="user_preferences",
        key="language",
        value="User prefers Python.",
    )
    store.upsert(write)
    assert store.last_sync_error is None
    snapshot = {
        "memories": [
            {
                "id": write.memory_id,
                "category": write.category,
                "key": write.key,
                "value": write.value,
                "status": "active",
            }
        ]
    }
    database.upsert_chat_memory_state("chat", json.dumps(snapshot))
    url = "/api/memories/" + write.memory_id
    assert client.post(url + "/deactivate").status_code == 200
    with index._vec_connect() as conn:
        assert conn.execute("SELECT count(*) FROM vec_memories").fetchone()[0] == 0
    assert not StructuredMemoryRetriever(database, mode="sqlite").retrieve(
        "chat", SourcePlan(source="structured_memory", query="unmatched")
    )
    assert client.post(url + "/activate").status_code == 200
    with index._vec_connect() as conn:
        assert conn.execute("SELECT count(*) FROM vec_memories").fetchone()[0] == 1
    database.upsert_chat_memory_state("chat", json.dumps(snapshot))
    assert client.delete(url).status_code == 200
    assert store.get(write.namespace, write.memory_id) is None
    with index._vec_connect() as conn:
        assert conn.execute("SELECT count(*) FROM vec_memories").fetchone()[0] == 0
    assert not StructuredMemoryRetriever(database, mode="sqlite").retrieve(
        "chat", SourcePlan(source="structured_memory", query="unmatched")
    )
