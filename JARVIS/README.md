# JARVIS v2 — Personal AI Assistant

Iron Man-style AI assistant. Offline-capable. No API keys required.

## Hardware
- Ryzen 7 7000 Series, 32GB RAM, 4GB VRAM NVIDIA
- Windows 11 (primary) / Ubuntu (secondary)

## Quick Start
```
python setup.py    # install dependencies
python main.py     # launch JARVIS
```

## What's New in v2

| Module | Description |
|--------|-------------|
| `tools/web_search/` | DuckDuckGo + Bing fallback, GitHub, Wikipedia |
| `tools/file_creator/` | PDF, PPTX, DOCX, XLSX creation |
| `tools/code_executor/` | Safe Python + shell execution |
| `tools/github_tool/` | Search, read, clone, learn from GitHub repos |
| `tools/app_controller/` | Claude/ChatGPT/DeepSeek/Gemini/Grok automation |
| `voice/` | Wake word + Whisper STT + Piper TTS |
| `self_edit/` | JARVIS improves its own code |
| `safety/` | 3-level security guard |

## Architecture
```
You → main.py → LangGraph
                  input_processor
                  task_router          ← keyword + LLM routing
                  brain_selector       ← offline (Ollama) / online (API/App)
                  executor             ← calls tools or LLM
                  output
```

## Ollama Port
Configured on **11435** (not default 11434 — avoids svchost conflict).

## Tasks JARVIS Can Do
- **Chat** — general Q&A, explanations
- **Web Search** — DuckDuckGo, Bing, Wikipedia, YouTube, GitHub
- **File Creation** — PDF, PPTX, DOCX, XLSX
- **Code** — write, explain, debug, execute Python/shell
- **GitHub** — search repos, read code, clone, learn from open source
- **Memory** — remembers you across sessions (ChromaDB + SQLite)
- **Self-Edit** — reads and improves its own source code
- **Voice** — wake word "JARVIS", Whisper STT, Piper TTS (type "voice on")

## File Structure
```
JARVIS/
├── main.py
├── setup.py
├── .env.txt  (rename to .env)
└── jarvis/
    ├── brain/          selector.py (offline/online LLM routing)
    ├── core/           graph.py, router.py, executor.py, state.py
    ├── memory/         memory.py (ChromaDB + SQLite + short-term)
    ├── safety/         guard.py (3-level security)
    ├── self_edit/      self_editor.py
    ├── tools/
    │   ├── app_controller/   browser, ai_router, context_transfer
    │   ├── code_executor/    executor
    │   ├── file_creator/     file_maker (pdf/pptx/docx/xlsx)
    │   ├── github_tool/      github_tool
    │   └── web_search/       searcher
    ├── voice/          voice_pipeline.py
    └── data/           memory/, logs/, backups/
```

## Voice Setup (Optional)
1. Download Piper from https://github.com/rhasspy/piper/releases
2. Extract to `C:\JARVIS_v1_AgentCore\JARVIS\piper\`
3. Download voice: `en_US-amy-medium.onnx` to `piper\voices\`
4. Type `voice on` in JARVIS

## No API Keys Needed
JARVIS uses:
- Ollama (local, offline)
- Claude Desktop App (screen automation)
- ChatGPT Desktop App (screen automation)
- DeepSeek / Gemini / Grok via browser

---
Built by Yogi. Powered by LangChain + LangGraph + Ollama.
