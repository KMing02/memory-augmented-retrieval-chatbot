# Verification

## Default offline suite

```bash
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run python -m compileall -q app.py src evals tests scripts
node --check public/product-navigation.js
git diff --check
```

Latest complete run: **689 passed, 0 failed, 0 skipped, 15 deselected**
(36.77 seconds). The deselected checks are optional browser/local-server tests.
Dependency deprecation warnings remain.

Pytest collects `tests/`. Browser and live markers are excluded by default.
`tests/conftest.py` installs safe defaults **before application imports**:

- fresh temporary SQLite/Chroma paths;
- disabled dotenv loading and dummy provider credentials;
- external socket connections blocked, loopback retained;
- Hugging Face/dataset offline mode (no model downloads);
- child `uv` commands reuse the active Python environment without syncing it.

Tests inject deterministic model, document and embedding doubles at their
boundaries. They still exercise real SQLite persistence, routing, context
assembly, failure handling and lifecycle code. The sqlite-vec lifecycle regression
uses the real extension with tiny deterministic vectors, not a mocked index.
The PDF regression uses the declared PyMuPDF runtime dependency.

The 39 original failing IDs and their dispositions are recorded in
[TEST_TRIAGE.json](TEST_TRIAGE.json). Fixes include legacy namespace reads,
canonical extraction fixtures, explicit injected-manager isolation, preserved gist
provenance, an obsolete adapter configuration reference, and source-specific
assertions that had accidentally asserted on unrelated retrieval sources.

The verification environment used Python 3.12 and an existing local dependency
environment. `uv sync --locked --dry-run --offline` resolved the lockfile, but a
fresh full Python installation was not performed. No historical answer-quality
benchmark or paid provider request was run.

## Primary React SPA smoke

```bash
uv run pytest -q tests/e2e/test_react_smoke.py -m browser
```

Latest result: **1 passed** (22.57 seconds). This launches the actual Vite React
SPA and a Chainlit backend on temporary ports, with fresh SQLite/Chroma paths and
synthetic credentials. The existing backend fixture injects deterministic
inference, memory and document doubles. No paid model is involved.

The smoke verifies Home, automatic authentication, New Chat, the proxied backend
API, a displayed response over the real WebSocket path, and End Chat. It checks
that the conversation is inactive afterward, retains an assistant message, and
has a finalized previous-chat gist. A reviewed synthetic-data capture is in
[screenshots](screenshots/README.md).

Installed Chrome is required; set `CHROME_EXECUTABLE` if it is not at the default
macOS location. Install frontend dependencies first. Local port binding and
browser launch permissions are required. `VITE_BACKEND_URL` selects the proxy
backend; `startup.py --port PORT` propagates it automatically.

## Legacy Chainlit compatibility checks

The bare Chainlit UI on port 8000 is a compatibility surface, not the primary
product UI. Its separate suite can be requested explicitly:

```bash
uv run pytest -q tests/e2e/test_product_behavior_browser.py -m browser -x
```

The bounded attempt returned **1 passed, 1 setup error**: synthetic `/login` and
`/user` authentication succeeded, then the expected legacy
`#memory-chatbot-home` element did not appear. No production auth was bypassed.
These checks remain outside default verification and are not claimed as passing.
The earlier unbounded attempt was stopped and has no complete result.

The separate localhost infrastructure check is:

```bash
uv run pytest -q tests/test_test_isolation.py -m browser
```

## Frontend

```bash
PUPPETEER_SKIP_DOWNLOAD=true npm --prefix braemon ci --ignore-scripts
npm --prefix braemon run build
npm --prefix braemon run lint
```

Locked install and production build passed. Oxlint exits successfully with
existing warnings. Vite reports a bundle-size warning. React type packages match
React 18; browser test packages are dev dependencies. npm reports dependency
advisories; this prototype has not undergone a production security audit.

## Optional live-provider smoke test

Not part of pytest; **not executed** in this update. Run only after deliberately
choosing a provider/key in `.env`. A hosted request can incur a charge.

```bash
uv run python -c 'from src.config import AppConfig; from src.model_wrapper import ModelWrapper; print(ModelWrapper(AppConfig.load()).chat([{"role":"user","content":"Reply with OK."}]))'
```

Ollama needs an already running server and an installed model. No Ollama server
responded during this update, so no local live-generation result is claimed.
Configuration parsing/sharing is covered by offline provider unit tests. Actual
model quality and structured/tool-call compatibility need a separate smoke run.
