"""Offline defaults are installed before test modules import application code.

No production clients are mocked here: tests inject doubles at their boundaries.
Loopback remains available for local HTTP/browser integration.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

_environment = pytest.MonkeyPatch()
_runtime = TemporaryDirectory(prefix="memory-chatbot-pytest-")
_RUNTIME_ROOT = Path(_runtime.name)


def pytest_configure(config):
    for key in list(os.environ):
        if key.endswith(("_API_KEY", "_AUTH_TOKEN")) or key in {
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        }:
            _environment.delenv(key, raising=False)
    for key, value in {
        "PYTHON_DOTENV_DISABLED": "1",
        "STRUCTURED_MEMORY_RETRIEVAL_MODE": "sqlite",
        "LLM_PROVIDER": "custom",
        "OPENAI_API_KEY": "dummy",
        "DEEPSEEK_API_KEY": "dummy",
        "OPENAI_BASE_URL": "http://127.0.0.1:1/v1",
        "MODEL_NAME": "test-model",
        "DATABASE_PATH": str(_RUNTIME_ROOT / "runtime.db"),
        "LANGCHAIN_CHROMA_PERSIST_DIR": str(_RUNTIME_ROOT / "chroma"),
        "CHROMA_PERSIST_DIRECTORY": str(_RUNTIME_ROOT / "chroma"),
        "HF_HUB_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "UV_OFFLINE": "1",
        "UV_NO_SYNC": "1",
        "UV_PROJECT_ENVIRONMENT": sys.prefix,
        "PYTHON": sys.executable,
    }.items():
        _environment.setenv(key, value)
    original = socket.socket.connect

    def offline_connect(sock, address):
        if isinstance(address, tuple):
            host = address[0]
            try:
                local = ipaddress.ip_address(host).is_loopback
            except ValueError:
                local = host == "localhost"
            if not local:
                raise OSError("External network disabled by offline test suite")
        return original(sock, address)

    _environment.setattr(socket.socket, "connect", offline_connect)


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/e2e/" in str(item.path):
            item.add_marker(pytest.mark.browser)


def pytest_unconfigure(config):
    _environment.undo()
    _runtime.cleanup()
