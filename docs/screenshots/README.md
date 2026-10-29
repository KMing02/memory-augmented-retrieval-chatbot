# React UI capture

[react-chat.png](react-chat.png) is an actual capture from the primary React SPA
smoke test. It uses fresh temporary storage and a synthetic conversation, with a
deterministic test model instead of a live LLM. It is not a generated/mock UI
image and does not establish model answer quality. The same test verified End
Chat persistence and gist finalization after capturing the image.

To capture the primary frontend manually:

1. Follow the README setup with Ollama or an explicitly chosen hosted provider.
2. Start with fresh storage: set `DATABASE_PATH` to an empty temporary SQLite
   path and `LANGCHAIN_CHROMA_PERSIST_DIR` to a fresh temporary directory.
3. Start the app. Open `http://localhost:5173` in a 1440×1000 browser window.
4. Use a synthetic prompt: “Our demo project codename is cobalt. Please remember
   it.” End the chat; create another and ask “What is our demo codename?”
5. Capture the answer and Inspect Answer evidence/provenance panel. Check the
   sidebar, sources, paths and inspector for personal data before saving.
6. Save a reviewed capture as `answer-inspector.png` here and add an image link
   to the README. State the provider/model and whether a test double was used.

Do not copy screenshots from a personal runtime database or include API keys,
local usernames/absolute paths, or real conversation histories.
