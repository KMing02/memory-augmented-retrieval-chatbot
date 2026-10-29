import os
import socket
from pathlib import Path

import pytest


def test_default_configuration_has_temporary_storage_and_dummy_credentials():
    from src.config import AppConfig

    config = AppConfig.load()
    assert config.openai_api_key == "dummy"
    assert os.environ["DEEPSEEK_API_KEY"] == "dummy"
    assert config.openai_base_url == "http://127.0.0.1:1/v1"
    assert config.database_path.is_absolute()
    assert "memory-chatbot-pytest-" in str(config.database_path)
    assert config.langchain_chroma_persist_dir.parent == config.database_path.parent
    assert os.environ["PYTHON_DOTENV_DISABLED"] == "1"
    assert os.environ["HF_HUB_OFFLINE"] == "1"


def test_external_sockets_fail_before_connecting():
    with socket.socket() as sock, pytest.raises(OSError, match="External network disabled"):
        sock.connect(("192.0.2.1", 443))


@pytest.mark.browser
def test_loopback_remains_available():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.create_connection(server.getsockname()) as client:
            peer, _ = server.accept()
            peer.close()
            assert client.getpeername() == server.getsockname()


def test_dotenv_cannot_override_test_environment(tmp_path, monkeypatch):
    from dotenv import load_dotenv

    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=synthetic-secret-that-must-not-load\n")
    load_dotenv(env, override=True)
    assert os.environ["OPENAI_API_KEY"] == "dummy"
    assert not Path("data/chatbot.db.old").exists()
