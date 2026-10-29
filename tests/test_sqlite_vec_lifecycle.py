"""Real sqlite-vec storage with tiny deterministic embeddings: no model/network."""

from dataclasses import replace

from src.database import Database
from src.memory.long_term_store import SQLiteLongTermMemoryStore, LongTermMemoryWrite
from src.memory.long_term_vector_index import LongTermMemoryVectorIndex
from src.memory.structured_memory_vector_sync import StructuredMemoryVectorSync


class TinyEmbeddings:
    def embed_query(self, text):
        return [1.0 if "Python" in text else 0.1, 0.5] + [0.0] * 382

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]


def test_real_vector_update_and_delete_are_idempotent(tmp_path):
    database = Database(tmp_path / "vector.db")
    index = LongTermMemoryVectorIndex(database=database)
    index._embeddings_cache = TinyEmbeddings()
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
    first = store.get(write.namespace, write.memory_id)
    store.upsert(replace(write, value="User prefers Rust."))
    assert store.last_sync_error is None
    assert store.get(write.namespace, write.memory_id).rowid == first.rowid
    with index._vec_connect() as conn:
        assert conn.execute("SELECT count(*) FROM vec_memories").fetchone()[0] == 1
    store.delete(write.namespace, write.memory_id)
    store.delete(write.namespace, write.memory_id)
    with index._vec_connect() as conn:
        assert conn.execute("SELECT count(*) FROM vec_memories").fetchone()[0] == 0
