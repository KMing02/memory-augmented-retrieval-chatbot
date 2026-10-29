import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

from src.config import AppConfig
from src.memory.long_term_vector_index import LongTermMemoryVectorIndex


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/rebuild_long_term_memory_index.py"


def test_rebuild_uses_database_instance_without_loading_models(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    monkeypatch.setattr(
        AppConfig,
        "from_env",
        lambda: SimpleNamespace(database_path=tmp_path / "memory.db", embedding_model_name="fake"),
    )
    seen = []

    def rebuild(index, *, store, namespaces):
        assert index._database.path == tmp_path / "memory.db"
        assert index.embedding_model_name == "fake"
        assert namespaces == []
        seen.append(index)
        return SimpleNamespace(indexed_count=0, skipped_count=0)

    monkeypatch.setattr(LongTermMemoryVectorIndex, "rebuild_from_store", rebuild)
    namespace = runpy.run_path(str(SCRIPT))
    assert namespace["main"]() == 0
    assert len(seen) == 1
    assert "indexed_count=0" in capsys.readouterr().out
