"""Primary SPA smoke: real servers/auth/storage, deterministic inference only."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import expect, sync_playwright

from src.database import Database

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.browser


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(url, process):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Test server exited; inspect temporary server log")
        try:
            with urlopen(url, timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("Test server readiness timed out")


def test_primary_react_chat_and_end_lifecycle(tmp_path):
    chrome = Path(
        os.environ.get(
            "CHROME_EXECUTABLE", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
    )
    if not chrome.exists():
        pytest.skip("Installed Chrome required; set CHROME_EXECUTABLE")
    if not (ROOT / "braemon/node_modules").exists():
        pytest.skip("Run npm --prefix braemon ci before this optional browser test")
    backend_port, frontend_port = free_port(), free_port()
    backend_url, frontend_url = (
        f"http://127.0.0.1:{backend_port}",
        f"http://127.0.0.1:{frontend_port}",
    )
    database_path = tmp_path / "react.db"
    env = {
        **os.environ,
        "DATABASE_PATH": str(database_path),
        "LANGCHAIN_CHROMA_PERSIST_DIR": str(tmp_path / "chroma"),
        "CHAINLIT_LOCAL_USERNAME": "local",
        "CHAINLIT_LOCAL_PASSWORD": "local",
        "VITE_BACKEND_URL": backend_url,
    }
    processes = []
    with (
        (tmp_path / "backend.log").open("w") as backend_log,
        (tmp_path / "frontend.log").open("w") as frontend_log,
    ):
        try:
            backend = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "chainlit",
                    "run",
                    "tests/e2e/product_behavior_chainlit_app.py",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(backend_port),
                    "--headless",
                ],
                cwd=ROOT,
                env=env,
                stdout=backend_log,
                stderr=subprocess.STDOUT,
            )
            processes.append(backend)
            frontend = subprocess.Popen(
                [
                    "npm",
                    "run",
                    "dev",
                    "--",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(frontend_port),
                    "--strictPort",
                ],
                cwd=ROOT / "braemon",
                env=env,
                stdout=frontend_log,
                stderr=subprocess.STDOUT,
            )
            processes.append(frontend)
            wait_for_server(backend_url, backend)
            wait_for_server(frontend_url, frontend)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=str(chrome), headless=True)
                try:
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    page.set_default_timeout(15000)
                    page.set_default_navigation_timeout(15000)
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(frontend_url)
                    expect(
                        page.get_by_role("heading", name="Technical Retrieval Workspace")
                    ).to_be_visible()
                    assert page.request.get(frontend_url + "/api/models/status").json()["ready"]
                    page.get_by_text("New Chat", exact=True).click()
                    page.wait_for_url("**/chat/*")
                    chat_id = page.url.rsplit("/", 1)[-1]
                    composer = page.locator("input[placeholder]").last
                    expect(composer).to_be_enabled()
                    composer.fill("Synthetic portfolio smoke: cobalt.")
                    composer.press("Enter")
                    expect(page.get_by_text("Deterministic answer:", exact=False).last).to_be_visible()
                    assert not errors, errors
                    page.screenshot(path=str(tmp_path / "react-chat.png"), full_page=True)
                    screenshot = os.environ.get("PORTFOLIO_SCREENSHOT_PATH")
                    if screenshot:
                        page.screenshot(path=screenshot, full_page=True)
                    page.get_by_role("button", name="End Chat", exact=False).click()
                    page.wait_for_url("**/chats")
                    database = Database(database_path)
                    assert not database.is_chat_active(chat_id)
                    assert database.chat_gists_for_chat(chat_id, "previous_chat_gist")
                    assert any(m.role == "assistant" for m in database.messages_for_chat(chat_id))
                finally:
                    browser.close()
        finally:
            for process in reversed(processes):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
