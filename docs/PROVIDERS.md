# Model providers

`LLM_PROVIDER=ollama|deepseek|custom` resolves to one URL, key, and model.
The existing OpenAI-compatible wrapper supplies final answers, routing, LLM
reranking, document summaries and previous-chat gists. LangMem's LangChain
client uses the same resolver for structured-memory extraction. Connection
checks use the resolved URL too. No university endpoint is required.

- **Ollama:** `OLLAMA_BASE_URL=http://localhost:11434/v1`,
  `OLLAMA_MODEL=qwen2.5:3b`. The client uses a dummy key. Install/pull a model
  yourself; startup does not provision Ollama models.
- **DeepSeek:** `DEEPSEEK_API_KEY` is required;
  `DEEPSEEK_MODEL=deepseek-flash` is the default. Endpoint and model names were
  checked against [official documentation](https://api-docs.deepseek.com/).
  No paid live request was made for this portfolio cleanup.
- **Custom:** `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `MODEL_NAME`. If
  `LLM_PROVIDER` is absent, this legacy configuration still works.

Configuration is read after `.env` loading; existing environment values win.
Do not commit `.env`. Changing providers requires restarting the application.
The registered Gemma context profile is historical. Other models use a
conservative fallback unless `ENDPOINT_CONTEXT_WINDOW` is supplied; inspect
context/token diagnostics rather than assuming advertised model capacity.

Evaluation answer clients use `AppConfig` too. Judge runners deliberately
support a separate model/URL/key through their documented command-line judge
arguments. These are explicit evaluation-only overrides, not a hidden memory
provider. Shell evaluation wrappers retain their legacy `OPENAI_*`,
`ANSWER_MODEL`, and `JUDGE_*` arguments; they are opt-in live tools, not the
normal verification command.
