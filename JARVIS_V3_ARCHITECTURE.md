# JARVIS V3 — Complete Architecture Audit, Design & Implementation Roadmap

**Prepared by:** Chief AI Architect  
**For:** user 
**Classification:** CONFIDENTIAL — Internal Architecture Document  
**Status:** AWAITING APPROVAL BEFORE IMPLEMENTATION  

---

## TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Audit Scope](#audit-scope)
3. [Part 1: Architecture Audit of JARVIS V2](#part-1-architecture-audit)
4. [Part 2: Weakness Report](#part-2-weakness-report)
5. [Part 3: JARVIS V3 Architecture Design](#part-3-jarvis-v3-design)
6. [Part 4: Complete Folder Structure](#part-4-folder-structure)
7. [Part 5: Technology Stack](#part-5-technology-stack)
8. [Part 6: Implementation Roadmap](#part-6-implementation-roadmap)
9. [Risk Analysis](#risk-analysis)
10. [Testing Strategy](#testing-strategy)

---

## EXECUTIVE SUMMARY

Sir, I have completed a full audit of the JARVIS V2 codebase. My assessment is direct:

**V2 is a functional proof-of-concept, not a production system.**

The architecture has the right instincts — LangGraph, Ollama, ChromaDB, voice pipeline — but the execution has critical bugs, no async architecture, a terminal-based UI, hardcoded paths, a trivially bypassable security system, and an incomplete ZIP submission that omits the core modules entirely.

**My recommendation:** Do not patch V2. Redesign from scratch using V2 as a reference, preserving none of its structural patterns. The only thing worth preserving is the SQLite log schema (extended significantly) and the general concept of the LangGraph pipeline.

The V3 architecture proposed in this document will deliver a system that is:
- A real desktop application (not a terminal)
- Always-on voice (not opt-in)
- Async from top to bottom (no blocking calls)
- Multi-process (isolated, crash-resilient)
- Genuinely modular (skills, tools, providers as plugins)
- Self-improving in a controlled, auditable way
- Remotely controllable via Telegram
- Production-grade on your specific hardware

---

## AUDIT SCOPE

**What was provided in the ZIP:**

| File | Status |
|------|--------|
| `main.py` | Present — Terminal REPL |
| `setup.py` | Present — Dependency installer |
| `.env.txt` | Present — Config template |
| `README.md` | Present — Documentation |
| `jarvis/voice/voice_pipeline.py` | Present — Full implementation |
| `jarvis/safety/guard.py` | Present — Full implementation |
| `jarvis/self_edit/self_editor.py` | Present — Full implementation |
| `jarvis/data/logs/jarvis_log.db` | Present — SQLite with 8 log entries |
| `jarvis/__init__.py` (×4) | Present — Empty package markers |

**What is MISSING from the ZIP (referenced in README but not included):**

| Missing Module | Significance |
|---|---|
| `jarvis/brain/selector.py` | Brain/model selector — CORE |
| `jarvis/core/graph.py` | LangGraph definition — CORE |
| `jarvis/core/router.py` | Task routing logic — CORE |
| `jarvis/core/executor.py` | Tool executor — CORE |
| `jarvis/core/state.py` | LangGraph state — CORE |
| `jarvis/memory/memory.py` | ChromaDB + SQLite memory — CORE |
| `jarvis/tools/app_controller/` | AI app automation — CRITICAL |
| `jarvis/tools/code_executor/` | Code sandbox — IMPORTANT |
| `jarvis/tools/file_creator/` | PDF/PPTX/DOCX — IMPORTANT |
| `jarvis/tools/github_tool/` | GitHub integration — IMPORTANT |
| `jarvis/tools/web_search/` | Web search — IMPORTANT |

**The ZIP represents approximately 25-30% of the actual codebase.** 

Despite this, the provided files expose enough about the architectural philosophy, coding patterns, and design decisions to perform a complete audit. The SQLite log also reveals live usage patterns.

---

## PART 1: ARCHITECTURE AUDIT

### 1.1 Current Architecture (From README + Code Analysis)

```
JARVIS V2 Architecture:

User Types → Terminal (input()) → main.py (blocking loop)
                                      ↓
                              get_jarvis_graph()   ← LangGraph
                                      ↓
                              ┌─── input_processor
                              ├─── task_router       (keyword + LLM)
                              ├─── brain_selector    (offline/online)
                              ├─── executor          (tools + LLM)
                              └─── output            (print to terminal)
                              
Voice: Optional background thread
       → OpenWakeWord → Whisper → callback → same blocking graph

Memory: ChromaDB (vectors) + SQLite (logs/profile)

Security: Keyword-matching guard with terminal confirmation prompts

Self-Edit: Read → LLM suggest → Diff → Apply → Syntax check
```

**Observed from SQLite logs:**

The 8 logged interactions show JARVIS was tested on June 11, 2026. Response times ranged from 2.2 to 7.8 seconds. All 8 succeeded. Task types were only 'assistant' and 'chat' — no routing differentiation was observed in the logs, suggesting the router classified most things as generic chat.

**Observed from .env.txt:**

- Ollama runs on port 11435 (non-default, to avoid svchost conflict — good decision)
- Only phi3.5 is configured as default (single-model, no fallback)
- Voice is OFF by default
- Security level defaults to 1 (AI apps only)

### 1.2 Module-by-Module Analysis

#### main.py

**What it does:** Terminal REPL that accepts text input and passes it to LangGraph.

**Issues found:**
- `input()` is blocking — the entire application stalls waiting for user input
- Voice is activated manually with "voice on" command — not always-on as required
- No async architecture whatsoever
- `os.system("cls")` for clear is acceptable but primitive
- Signal handling (`SIGINT`) is correct in concept but `sys.exit(0)` in a signal handler is unsafe — it skips cleanup
- Emergency stop = "move mouse to top-left" is a PyAutoGUI failsafe, not a real emergency stop
- BANNER is hardcoded text — no dynamic status information

**Verdict:** Complete replacement required. This must become a proper async event loop with a desktop app frontend.

---

#### jarvis/voice/voice_pipeline.py

**What it does:** Wake word detection + Whisper STT + Piper TTS.

**Issues found (CRITICAL):**

**Bug #1 — Audio Feedback Loop:**
```python
def _record_utterance(self) -> str:
    # ...opens microphone stream...
    self.speak_sync("Yes Sir?")  # ← PLAYS AUDIO WHILE MIC IS OPEN
```
The microphone is open when `speak_sync` is called. On most consumer setups, the speakers will feed back into the microphone, causing "Yes Sir?" to be transcribed as part of the user's command.

**Bug #2 — Non-Thread-Safe Singleton:**
```python
_pipeline: Optional[VoicePipeline] = None

def get_voice_pipeline(callback: Callable = None) -> VoicePipeline:
    global _pipeline
    if _pipeline is None:          # ← Race condition here
        _pipeline = VoicePipeline(on_wake_word=callback)
```
Two threads calling simultaneously can create two VoicePipeline instances.

**Bug #3 — Hardcoded Windows Path:**
```python
PIPER_EXE        = r"C:\JARVIS_v1_AgentCore\JARVIS\piper\piper.exe"
PIPER_MODEL_PATH = r"C:\JARVIS_v1_AgentCore\JARVIS\piper\voices\en_US-amy-medium.onnx"
```
Breaks on any machine that isn't the original development machine. Also breaks if you move the JARVIS folder.

**Bug #4 — pyttsx3 Reinstantiated Every Call:**
```python
def _speak_piper(self, text: str):
    # ...piper fails...
    import pyttsx3
    engine = pyttsx3.init()   # ← Creates new engine instance EVERY call
    engine.say(text)
    engine.runAndWait()
    # engine is never stored — leaked
```
pyttsx3 is initialized fresh on every TTS call. The engine instance leaks. On Windows, this eventually causes COM errors.

**Bug #5 — Wake Word Score Logic:**
```python
activated = any(
    score > 0.5
    for scores in prediction.values()
    for score in (scores if isinstance(scores, (list, tuple)) else [scores])
)
```
This threshold is hardcoded. OpenWakeWord score distributions vary significantly by model and acoustic environment. 0.5 may be too sensitive (false activations) or too restrictive (misses real wake words).

**Bug #6 — No State Machine:**
There is no state management. JARVIS can be simultaneously:
- Listening for wake word
- Recording utterance  
- Speaking TTS output

These states should be mutually exclusive. Without state management, the pipeline can enter undefined states.

**Bug #7 — Thread Join Timeout:**
```python
def stop(self):
    self._running = False
    if self._thread:
        self._thread.join(timeout=2)   # ← 2 second timeout
```
The listener thread reads from `sounddevice` which may block. If the audio device is unresponsive, the join returns after 2 seconds but the thread keeps running. This creates zombie threads.

**Verdict:** Complete rewrite required. The architecture (wake word → STT → TTS) is correct but every implementation detail needs fixing.

---

#### jarvis/safety/guard.py

**What it does:** 3-level security system based on keyword matching.

**Issues found (CRITICAL):**

**Bug #1 — Trivially Bypassable:**
```python
L2_KEYWORDS = ["delete file", "remove file", "write to", ...]
L3_KEYWORDS = ["registry", "regedit", "format", ...]
```
Simple substring matching. The following bypasses are trivial:
- "Remove the document" → not caught (only "remove file" is checked)
- "wipe the folder" → not caught
- "modify HKLM" → not caught (only "registry" and "regedit")
- "net  user" → not caught (double space)

**Bug #2 — Console Confirmation Breaks Voice Mode:**
```python
def console_confirm(level: SecurityLevel, description: str) -> bool:
    # ...
    reply = input("  Confirm? (yes/no): ").strip().lower()
```
When JARVIS is operating in voice mode, there is no terminal to type into. This hangs indefinitely.

**Bug #3 — No Audit Log:**
Security events are printed to terminal and forgotten. No persistent audit trail.

**Bug #4 — No Sandbox:**
The guard checks permission but doesn't isolate execution. Even if an operation is permitted, it runs in the same Python process with full OS access.

**Bug #5 — No Risk Scoring:**
Binary: either L1 (always allowed) or L2/L3 (confirmation required). No nuance for "slightly risky" vs "very risky" within a level.

**Verdict:** The concept is right (multi-level security) but the implementation is dangerously naive. Full redesign required.

---

#### jarvis/self_edit/self_editor.py

**What it does:** JARVIS reads its own code, asks LLM to suggest improvements, diffs and applies changes.

**Issues found:**

**Bug #1 — No Import Testing:**
```python
def validate_syntax(self, code: str) -> Tuple[bool, str]:
    try:
        ast.parse(code)
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
```
Only checks Python syntax. A file can pass syntax validation but fail to import because of a missing dependency, a wrong function call, or a logic error. No import test is performed after applying the edit.

**Bug #2 — Backup Directory in Project:**
```python
BACKUP_DIR  = JARVIS_ROOT / "jarvis" / "data" / "backups"
```
Backups stored inside the project directory. If the project is deleted or moved, backups are lost. No git versioning.

**Bug #3 — No Change Quantity Limit:**
Nothing prevents JARVIS from editing 20 files in succession. With a bad LLM response, this could corrupt the entire codebase.

**Bug #4 — JARVIS_ROOT Is Fragile:**
```python
JARVIS_ROOT = Path(__file__).parent.parent.parent
```
This is `self_editor.py → self_edit/ → jarvis/ → JARVIS/`. Correct in the current structure. But if the file is ever moved, this silently points to the wrong directory and JARVIS edits the wrong files.

**Bug #5 — Protected Module List Is Static:**
```python
PROTECTED_PATHS = ["jarvis/safety", "jarvis/memory", "jarvis/core/graph.py"]
```
Hardcoded. As JARVIS grows, new critical modules must be manually added to this list. Easy to forget.

**Verdict:** Redesign needed. Core concept (self-improvement with rollback) is correct. But it needs git versioning, import testing, rate limiting, and dynamic protected path detection.

---

#### setup.py

**Issues found:**

- Not a proper `setuptools` setup.py — it's a custom installation script masquerading as one
- No version pinning on any dependency — `pip install langchain` will install whatever is latest
- Silent failure during pip install (errors suppressed with `DEVNULL`)
- No virtual environment creation
- Checks Ollama on `11435` but the URL is wrong: `urllib.request.urlopen("http://127.0.0.1:11435")` — this is a TCP connection, not an HTTP check, and will fail even if Ollama is running (Ollama's `/api/tags` endpoint needs to be hit)
- No `requirements.txt` generated
- No `.gitignore` generated

**Verdict:** Replace with a proper `pyproject.toml` + `install.py` script.

---

### 1.3 What's Missing That Must Be Built From Scratch

The following critical systems have no implementation in V2 (or the ZIP was incomplete):

1. **Desktop Application** — No GUI whatsoever
2. **Multi-Model Router** — phi3.5 is hardcoded
3. **Agent Architecture** — No specialized agents (Planner, Researcher, Coder, etc.)
4. **Learning System** — No skill acquisition
5. **Remote Control** — No Telegram/web dashboard
6. **Memory Consolidation** — SQLite stores logs but no semantic retrieval
7. **Async Architecture** — Everything is synchronous/blocking
8. **Process Management** — No subprocess isolation
9. **Model Registry** — No auto-discovery of Ollama models
10. **Skill System** — No installable/removable skills

---

## PART 2: WEAKNESS REPORT

### P0 — Critical Bugs (Must Fix Before Shipping)

| ID | Module | Issue | Impact |
|----|--------|--------|--------|
| P0-01 | voice_pipeline.py | Audio feedback loop during "Yes Sir?" | Corrupts all voice transcriptions |
| P0-02 | voice_pipeline.py | Hardcoded C:\JARVIS_v1_AgentCore path | Breaks on any non-dev machine |
| P0-03 | voice_pipeline.py | pyttsx3 COM engine leaked every call | Memory leak → eventual crash |
| P0-04 | guard.py | Console `input()` called in voice mode | Hangs JARVIS indefinitely |
| P0-05 | guard.py | Keyword bypass (trivial prompt injection) | Security system is non-functional |
| P0-06 | main.py | Blocking `input()` in main loop | UI freezes, voice blocked |
| P0-07 | voice_pipeline.py | No state machine | Undefined concurrent behavior |
| P0-08 | self_editor.py | No import test after syntax check | Bad edit can permanently break JARVIS |

### P1 — Architectural Issues

| ID | Issue | Impact |
|----|--------|--------|
| P1-01 | Terminal REPL instead of desktop app | Violates non-negotiable requirement |
| P1-02 | Voice is opt-in, not always-on | Violates non-negotiable requirement |
| P1-03 | Monolithic single process | One tool crash kills all of JARVIS |
| P1-04 | Zero async throughout | Cannot handle concurrent voice + processing |
| P1-05 | No model routing | phi3.5 for everything regardless of task type |
| P1-06 | Missing entire tools layer | App controller, code executor, etc. not in ZIP |
| P1-07 | No remote control | Violates non-negotiable requirement |
| P1-08 | Security confirmation not voice-capable | Cannot run in headless/voice-only mode |

### P2 — Technical Debt

| ID | Issue | Impact |
|----|--------|--------|
| P2-01 | No dependency pinning | Any `pip install` could break the system |
| P2-02 | No virtual environment in setup | Dependency conflicts with system packages |
| P2-03 | Print statements for all logging | No structured log, no log levels, no rotation |
| P2-04 | Magic strings everywhere | Hard to maintain, easy to make typos |
| P2-05 | No configuration validation | Bad .env values silently cause runtime errors |
| P2-06 | No error monitoring | Failures are invisible unless user watches terminal |
| P2-07 | Singletons without thread safety | Race conditions under concurrent access |
| P2-08 | No git versioning for self-edits | Backups are flat files, no history graph |
| P2-09 | Wake word threshold hardcoded | Cannot tune without code change |

### P3 — Scalability Limitations

| ID | Issue | Impact |
|----|--------|--------|
| P3-01 | Single model (phi3.5) | Cannot route coding tasks to code model |
| P3-02 | No skill plugin system | Adding capabilities requires code modification |
| P3-03 | No agent specialization | General LLM handles everything suboptimally |
| P3-04 | No model auto-discovery | New Ollama models require manual config |
| P3-05 | No benchmark system | Cannot know which model is best for a task |
| P3-06 | ChromaDB per-run | No persistent cross-session learning |
| P3-07 | No learning architecture | "JARVIS learn X" not implemented |
| P3-08 | No knowledge base | Each session starts from scratch |

---

## PART 3: JARVIS V3 ARCHITECTURE DESIGN

### 3.1 Core Design Philosophy

JARVIS V3 is designed around five principles:

**1. Process Isolation** — Every subsystem runs in its own process. A crashed tool cannot bring down the core JARVIS engine.

**2. Async-First** — Every I/O operation is async. The UI never freezes. Voice and thinking happen in parallel where appropriate.

**3. Event-Driven** — All components communicate through a central event bus. No direct coupling between modules.

**4. Plugin Architecture** — Skills, tools, voice backends, LLM providers, and UI panels are all plugins. JARVIS can grow without touching core code.

**5. State Machine Everything** — Voice has states. Agents have states. Tasks have states. Nothing operates without knowing what state it is in.

---

### 3.2 High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        JARVIS V3 SYSTEM                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    DESKTOP APPLICATION                        │  │
│  │  (PySide6/Qt6 — Iron Man Glassmorphism Theme)                │  │
│  │                                                               │  │
│  │  [Chat Panel] [Voice Indicator] [Agent Status] [Memory Panel] │  │
│  │  [Tool Execution Viz] [Settings] [Skill Panel] [Model Panel]  │  │
│  └──────────────────┬───────────────────────────────────────────┘  │
│                     │ WebSocket (asyncio)                          │
│  ┌──────────────────▼───────────────────────────────────────────┐  │
│  │                    CORE ENGINE (Process 1)                    │  │
│  │                                                               │  │
│  │  ┌─────────────────────────────────────────────────────┐    │  │
│  │  │              EVENT BUS (asyncio pubsub)              │    │  │
│  │  └──────┬────────────┬──────────────┬───────────────────┘   │  │
│  │         │            │              │                        │  │
│  │  ┌──────▼──────┐ ┌───▼────────┐ ┌──▼─────────────────┐    │  │
│  │  │ LANGGRAPH   │ │  MEMORY    │ │   SECURITY GUARD    │    │  │
│  │  │   ENGINE    │ │  MANAGER   │ │   (Risk Scorer)     │    │  │
│  │  │             │ │            │ │                     │    │  │
│  │  │ Coordinator │ │ Short-term │ │ Audit Logger        │    │  │
│  │  │ Agent       │ │ Long-term  │ │ Permission System   │    │  │
│  │  │ Planner     │ │ Semantic   │ │ Sandbox Enforcer    │    │  │
│  │  │ Researcher  │ │ Skill Mem  │ │                     │    │  │
│  │  │ Coder       │ │ Episodic   │ │                     │    │  │
│  │  │ Debugger    │ └────────────┘ └─────────────────────┘   │  │
│  │  │ Learner     │                                           │  │
│  │  │ Memory Agt  │  ┌────────────────────────────────────┐  │  │
│  │  └─────────────┘  │         TOOL REGISTRY              │  │  │
│  │                   │  web/ files/ system/ ai_apps/       │  │  │
│  │                   │  code/ github/ skills/              │  │  │
│  │                   └────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   BRAIN (Process 2)                          │   │
│  │                                                               │   │
│  │  ┌──────────────────┐   ┌──────────────────────────────┐    │   │
│  │  │  MODEL ROUTER    │   │     MODEL REGISTRY           │    │   │
│  │  │  Intent → Model  │   │  Auto-discovers Ollama models│    │   │
│  │  │  Task scoring    │   │  Benchmarks + capability map │    │   │
│  │  └────────┬─────────┘   └──────────────────────────────┘    │   │
│  │           │                                                  │   │
│  │  ┌────────▼─────────────────────────────────────────────┐   │   │
│  │  │              LLM PROVIDERS                            │   │   │
│  │  │  Ollama (phi/qwen/deepseek/gemma/mistral/llama)       │   │   │
│  │  │  Anthropic API (optional)  │  OpenAI API (optional)   │   │   │
│  │  └───────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────┐   ┌──────────────────────────────┐   │
│  │   VOICE (Process 3)      │   │   REMOTE (Process 4)         │   │
│  │                          │   │                              │   │
│  │  Wake Word (OpenWakeWord)│   │  Telegram Bot                │   │
│  │  STT (faster-whisper)    │   │  WebSocket Server            │   │
│  │  TTS (MeloTTS/Piper)    │   │  REST API (FastAPI)          │   │
│  │  Voice State Machine     │   │  Phone notifications         │   │
│  └──────────────────────────┘   └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 LangGraph Agent Architecture

```
User Input (text or voice)
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     LANGGRAPH STATE MACHINE                          │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    INPUT PROCESSOR NODE                       │   │
│  │  - Normalize text (clean, language detect, intent extract)    │   │
│  │  - Classify input type (query, command, conversation, learn)  │   │
│  │  - Attach context from memory                                 │   │
│  │  - Security pre-check                                         │   │
│  └─────────────────────┬────────────────────────────────────────┘   │
│                         │                                            │
│  ┌──────────────────────▼────────────────────────────────────────┐  │
│  │                    PLANNER AGENT NODE                          │  │
│  │  - Decompose complex tasks into subtasks                       │  │
│  │  - Create execution plan                                       │  │
│  │  - Estimate resource needs                                     │  │
│  │  - Route to appropriate agent                                  │  │
│  └──────┬──────────────────────────────────────────────────────┬─┘  │
│         │                                                       │    │
│  ┌──────▼────────────────┐              ┌──────────────────────▼─┐  │
│  │  SIMPLE TASK (direct) │              │  COMPLEX TASK (multi)  │  │
│  │  → Coordinator        │              │  → Coordinator spawns  │  │
│  │    dispatches to      │              │    multiple agents     │  │
│  │    single agent       │              │    in parallel/series  │  │
│  └───────────────────────┘              └────────────────────────┘  │
│                                                                      │
│  ┌─────────────┐ ┌────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │ RESEARCHER  │ │   CODER    │ │   LEARNER    │ │ TOOL AGENT  │  │
│  │ Agent       │ │   Agent    │ │   Agent      │ │  Agent      │  │
│  │             │ │            │ │              │ │             │  │
│  │ Web search  │ │ Write code │ │ Research new │ │ Execute     │  │
│  │ Summarize   │ │ Debug code │ │ skill domain │ │ system tools│  │
│  │ Synthesize  │ │ Test code  │ │ Build KB     │ │ App control │  │
│  │ Cite        │ │ Explain    │ │ Validate     │ │ File ops    │  │
│  └──────┬──────┘ └──────┬─────┘ └──────┬───────┘ └──────┬──────┘  │
│         │               │              │                  │         │
│  ┌──────▼───────────────▼──────────────▼──────────────────▼──────┐  │
│  │                     COORDINATOR AGENT                           │  │
│  │  - Collects results from all agents                             │  │
│  │  - Validates results                                            │  │
│  │  - Requests retries if needed                                   │  │
│  │  - Synthesizes final response                                   │  │
│  └──────────────────────────────────────────────────────────────┬─┘  │
│                                                                  │   │
│  ┌───────────────────────────────────────────────────────────────▼─┐  │
│  │                        OUTPUT NODE                               │  │
│  │  - Format response (Hinglish, Sir-addressed)                     │  │
│  │  - Store to memory                                               │  │
│  │  - Send to voice pipeline (if voice active)                      │  │
│  │  - Update UI                                                     │  │
│  │  - Log to audit trail                                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.4 LangGraph State Definition

```python
# core/graph/state.py — Complete state structure for V3

from typing import TypedDict, Literal, Optional, Any
from enum import Enum

class TaskType(str, Enum):
    CONVERSATION  = "conversation"
    CODING        = "coding"
    RESEARCH      = "research"
    LEARNING      = "learning"
    SYSTEM        = "system"    # file ops, app control
    AUTOMATION    = "automation"
    SELF_IMPROVE  = "self_improve"
    MEMORY        = "memory"
    REMOTE        = "remote"

class AgentStatus(str, Enum):
    IDLE      = "idle"
    THINKING  = "thinking"
    SEARCHING = "searching"
    CODING    = "coding"
    EXECUTING = "executing"
    SPEAKING  = "speaking"
    LISTENING = "listening"
    LEARNING  = "learning"
    ERROR     = "error"

class SecurityClearance(str, Enum):
    CLEARED   = "cleared"
    DENIED    = "denied"
    PENDING   = "pending"   # awaiting human approval

class JarvisState(TypedDict):
    # Input
    raw_input:       str
    input_mode:      Literal["text", "voice", "remote", "internal"]
    language:        str   # detected language
    
    # Planning
    task_type:       TaskType
    intent:          str    # LLM-extracted intent summary
    subtasks:        list   # list of subtask dicts
    plan:            dict   # full execution plan
    
    # Routing
    selected_model:  str    # which LLM will handle this
    selected_agents: list   # which agents are invoked
    
    # Security
    security_level:  int     # 1, 2, or 3
    security_score:  float   # 0.0–1.0 risk score
    clearance:       SecurityClearance
    security_reason: str
    
    # Memory context
    memory_context:  list    # retrieved memories
    user_profile:    dict    # user preferences, name, etc.
    
    # Execution
    agent_results:   dict    # {agent_name: result}
    tool_calls:      list    # [{tool, args, result, duration_ms}]
    error_count:     int
    retry_count:     int
    
    # Output
    final_response:  str
    response_for_voice: str  # shorter version for TTS
    
    # Status
    status:          AgentStatus
    is_complete:     bool
    total_duration:  float   # ms
```

### 3.5 Voice Architecture (State Machine)

```
Voice States and Transitions:

    ┌──────────────────────────────────────────────────────────┐
    │                    VOICE STATE MACHINE                    │
    │                                                           │
    │                      ┌──────────┐                        │
    │           ┌──────────►  SLEEPING │◄──────────────────┐   │
    │           │          └────┬─────┘                    │   │
    │           │ user types    │ app opens               │   │
    │           │ "sleep"       │ (auto wake)             │   │
    │           │               ▼                          │   │
    │           │          ┌──────────┐    wake word       │   │
    │           │   ┌──────► IDLE /   ├────not detected    │   │
    │           │   │      │ WATCHING │    (loops back)    │   │
    │           │   │      └────┬─────┘                    │   │
    │           │   │           │ wake word detected        │   │
    │           │   │           ▼                           │   │
    │           │   │      ┌──────────┐   audio stream      │   │
    │           │   │      │ ACTIVATED │───────────────►    │   │
    │           │   │      └────┬─────┘                    │   │
    │           │   │           │ "Yes Sir?" + mic mute    │   │
    │           │   │           ▼                           │   │
    │           │   │      ┌──────────┐   silence 2s       │   │
    │           │   │      │ RECORDING│────────────────►   │   │
    │           │   │      └────┬─────┘   or max 30s       │   │
    │           │   │           │ audio captured            │   │
    │           │   │           ▼                           │   │
    │           │   │      ┌──────────┐                    │   │
    │           │   │      │  STT     │                    │   │
    │           │   │      │ PROCESS  │                    │   │
    │           │   │      └────┬─────┘                    │   │
    │           │   │           │ text transcribed          │   │
    │           │   │           ▼                           │   │
    │           │   │      ┌──────────┐                    │   │
    │           │   │      │  SENT TO │                    │   │
    │           │   │      │  ENGINE  │                    │   │
    │           │   │      └────┬─────┘                    │   │
    │           │   │           │ engine processing         │   │
    │           │   │           ▼                           │   │
    │           │   │      ┌──────────┐   JARVIS speaks    │   │
    │           │   │      │ SPEAKING │────────────────────┘   │
    │           │   │      └──────────┘   (returns to IDLE)    │
    │           │   │                                           │
    │           │   └───────────────────────────────────────────┘
    │           │              user says "hey jarvis" while speaking
    │           │              → interrupts TTS, goes to ACTIVATED
    │           │                                               │
    │           └───────────────────────────────────────────────┘
    └──────────────────────────────────────────────────────────┘

Key fixes vs V2:
- Mic MUTED before speaking (eliminates feedback loop)
- State explicitly managed (no concurrent states)
- Interruption supported (user can talk over JARVIS)
- "Sleep" command supported for power saving
```

### 3.6 Memory Architecture (V3)

```
┌──────────────────────────────────────────────────────────────────┐
│                     MEMORY MANAGER V3                             │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ SHORT-TERM   │  │  EPISODIC    │  │   LONG-TERM          │  │
│  │ (In-Memory)  │  │  (SQLite)    │  │   (ChromaDB)         │  │
│  │              │  │              │  │                      │  │
│  │ Ring buffer  │  │ Full convers-│  │ Semantic embeddings  │  │
│  │ Last 20 msgs │  │ ation log    │  │ Searchable by        │  │
│  │ Fast O(1)    │  │ Timestamps   │  │ meaning not keyword  │  │
│  │ No disk I/O  │  │ Task types   │  │ sentence-transformers│  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                       │              │
│  ┌──────▼─────────────────▼───────────────────────▼──────────┐  │
│  │                  UNIFIED RETRIEVER                          │  │
│  │                                                             │  │
│  │  Query → Semantic search + Keyword search + Recency rank   │  │
│  │  Scoring: relevance(40%) + recency(30%) + importance(30%)  │  │
│  │  Returns: ranked list of memories with provenance          │  │
│  └──────────────────────────────────────────────────────────┬─┘  │
│                                                              │    │
│  ┌───────────────────────────────────────────────────────────▼─┐  │
│  │                  MEMORY CONSOLIDATOR                          │  │
│  │  Runs nightly (or on demand)                                 │  │
│  │  - Groups related memories                                   │  │
│  │  - Generates summaries of past sessions                      │  │
│  │  - Removes duplicates                                        │  │
│  │  - Promotes important short-term to long-term                │  │
│  │  - Prunes old, low-importance memories                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  SPECIALIZED MEMORY STORES                                  │   │
│  │                                                             │   │
│  │  ┌────────────┐ ┌────────────┐ ┌─────────────────────┐   │   │
│  │  │  SKILL MEM │ │ PROJECT    │ │  USER PREFERENCE    │   │   │
│  │  │            │ │  MEMORY    │ │  MEMORY             │   │   │
│  │  │ Learned    │ │            │ │                     │   │   │
│  │  │ skills     │ │ Active     │ │ Communication style │   │   │
│  │  │ Capability │ │ projects   │ │ Preferred tools     │   │   │
│  │  │ profiles   │ │ Context    │ │ Work patterns       │   │   │
│  │  └────────────┘ └────────────┘ └─────────────────────┘   │   │
│  └────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 3.7 Brain / Model Router Architecture

```
User Input + Task Context
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BRAIN ROUTER V3                             │
│                                                                  │
│  STEP 1: Intent Analysis                                         │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Fast classifier (regex + keyword):                     │    │
│  │  "write a function" → CODING                           │    │
│  │  "search for" → RESEARCH                               │    │
│  │  "what is X" → KNOWLEDGE (fast model)                  │    │
│  │  If ambiguous → LLM classifier (phi3.5 minimum)        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 2: Model Selection Matrix                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Task Type         │ Priority Model      │ Fallback    │    │
│  │  CODING            │ qwen2.5-coder:7b    │ deepseek-r1 │    │
│  │  REASONING/PLAN    │ deepseek-r1:7b      │ qwen2.5     │    │
│  │  CONVERSATION      │ phi3.5              │ llama3.2    │    │
│  │  RESEARCH          │ qwen2.5:14b         │ gemma2      │    │
│  │  MATH/LOGIC        │ deepseek-r1         │ qwen2.5     │    │
│  │  CREATIVE          │ mistral             │ llama3.2    │    │
│  │  FAST_RESPONSE     │ phi3.5 (3.8B)       │ qwen2.5:3b  │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 3: Availability Check                                      │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  1. Check Model Registry (auto-discovered Ollama list)  │    │
│  │  2. Check current VRAM budget                           │    │
│  │  3. Check model's avg response time (from benchmarks)   │    │
│  │  4. If online: check optional API providers             │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 4: Model Selection Decision                                │
│  Priority model available + VRAM budget → use it                 │
│  Priority model missing → try next in fallback chain             │
│  All local models unavailable → desktop AI app (Claude/ChatGPT)  │
│  Online provider configured → use API                            │
│  Absolute fallback → phi3.5 (always available)                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.8 Self-Improvement Architecture (V3)

```
"JARVIS, learn AutoCAD"
         │
         ▼
┌───────────────────────────────────────────────────────────────────┐
│                   LEARNING ENGINE V3                               │
│                                                                    │
│  PHASE 1: RESEARCH (Learner Agent)                                 │
│  ├── Web search: "{topic} documentation", "{topic} tutorials"      │
│  ├── GitHub search: "{topic} examples", "{topic} library"          │
│  ├── Download & process: READMEs, docs, code examples              │
│  └── Output: raw_knowledge_corpus (text + code)                    │
│                                                                    │
│  PHASE 2: SYNTHESIS (Research Agent + LLM)                         │
│  ├── Chunk corpus into semantic segments                           │
│  ├── Generate embeddings for each chunk                            │
│  ├── Create skill summary (what is this, how to use it)            │
│  ├── Create action plan (what JARVIS can now do with this skill)   │
│  └── Output: skill_profile.json + knowledge_vectors               │
│                                                                    │
│  PHASE 3: TOOL GENERATION (Coder Agent)                            │
│  ├── Analyze what tools are needed for this skill domain           │
│  ├── Generate tool module (Python code)                            │
│  ├── Validate syntax + import test                                 │
│  ├── Unit test generated tool in sandbox                           │
│  └── Output: skills/{skill_name}/tool.py (if tool needed)          │
│                                                                    │
│  PHASE 4: VALIDATION (Debugger Agent)                              │
│  ├── Run self-quiz: generate 10 questions, answer them             │
│  ├── Score quiz against known answers                              │
│  ├── If score < 70%: loop back to PHASE 1 with gaps identified     │
│  └── Output: validation_report.json                               │
│                                                                    │
│  PHASE 5: REGISTRATION (Memory Agent)                              │
│  ├── Store skill_profile in skill memory                           │
│  ├── Store knowledge vectors in ChromaDB                           │
│  ├── Update tool registry (if new tool generated)                  │
│  ├── Update capability map in model router                         │
│  └── Notify user: "Sir, AutoCAD skill acquired."                   │
│                                                                    │
│  FUTURE USE:                                                       │
│  "JARVIS, create an AutoCAD drawing"                               │
│  → Router detects AutoCAD task                                     │
│  → Loads AutoCAD skill profile from memory                         │
│  → Retrieves relevant knowledge from ChromaDB                      │
│  → Uses learned tool if available                                  │
│  → Executes task with full context                                 │
└───────────────────────────────────────────────────────────────────┘
```

### 3.9 Security Architecture (V3)

```
┌──────────────────────────────────────────────────────────────────┐
│                    SECURITY SYSTEM V3                             │
│                                                                   │
│  LAYER 1: INTENT ANALYSIS                                         │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  LLM-powered intent classifier (not keyword matching)   │     │
│  │  Assigns: operation_type, target_scope, reversibility   │     │
│  │  Cannot be bypassed by rephrasing                       │     │
│  └─────────────────────────────┬──────────────────────────┘     │
│                                 │                                 │
│  LAYER 2: RISK SCORING ENGINE                                     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  risk_score = Σ(weight × factor) / total_weight        │     │
│  │                                                         │     │
│  │  Factors:                                               │     │
│  │  - Reversibility: can this be undone?     (×0.30)      │     │
│  │  - Scope: how many files/processes?       (×0.25)      │     │
│  │  - System access: kernel/registry/network?(×0.25)      │     │
│  │  - Data sensitivity: PII/secrets touched? (×0.20)      │     │
│  │                                                         │     │
│  │  Score 0.0–0.3: AUTO APPROVE                            │     │
│  │  Score 0.3–0.6: SINGLE VOICE CONFIRMATION              │     │
│  │  Score 0.6–0.9: EXPLICIT VOICE + UI CONFIRM            │     │
│  │  Score 0.9–1.0: BLOCKED (requires manual enable)        │     │
│  └─────────────────────────────┬──────────────────────────┘     │
│                                 │                                 │
│  LAYER 3: SANDBOX EXECUTION                                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Code execution: RestrictedPython + resource limits     │     │
│  │  File ops: restricted to approved directories           │     │
│  │  Network: domain allowlist enforced                     │     │
│  │  System: subprocess wrapped with timeout + kill switch  │     │
│  └─────────────────────────────┬──────────────────────────┘     │
│                                 │                                 │
│  LAYER 4: AUDIT LOG                                               │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Every operation logged: timestamp, risk_score, user    │     │
│  │  decision, output, duration, success/failure            │     │
│  │  Logs are append-only (no JARVIS self-modification)     │     │
│  │  Rotated daily, kept 90 days                            │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
│  EMERGENCY STOP: F12 (global hotkey) OR Telegram "/stop"          │
│  - Kills all running subprocesses                                 │
│  - Stops voice pipeline                                           │
│  - Saves current state                                            │
│  - Enters safe mode (no tools, chat only)                         │
└──────────────────────────────────────────────────────────────────┘
```

### 3.10 App Controller Architecture (V3)

The V2 PyAutoGUI approach is fragile. V3 uses a priority hierarchy:

```
App Control Priority Stack:

PRIORITY 1: Official API
  → Claude API (if key provided)
  → OpenAI API (if key provided)
  → GitHub API (for GitHub operations)
  → YouTube Data API (for YouTube)
  → Direct HTTP where available

PRIORITY 2: Browser DevTools Protocol (CDP)
  → Playwright → Chrome DevTools Protocol
  → Full DOM access, no screen coordinates
  → Works even if window is minimized
  → Works on any resolution
  → Handles dynamic content

PRIORITY 3: Windows UI Automation (UIAutomation)
  → pywinauto → Windows Accessibility API
  → Works with native Win32/UWP apps
  → Reads UI tree, not pixel coordinates
  → Reliable even if UI is resized

PRIORITY 4: Electron IPC (for Electron apps)
  → Inject JavaScript into Electron app's webContents
  → Only for Claude Desktop, ChatGPT Desktop
  → Most reliable for Electron apps

PRIORITY 5: PyAutoGUI (last resort)
  → Screen coordinates + pixel detection
  → Only when all above fail
  → With retry logic + screenshot validation
  → With OCR via Tesseract for text verification

Selection Algorithm:
  1. Identify app type (web, native, electron, API)
  2. Try Priority 1 → 5 in order
  3. On failure: log error, try next priority
  4. On all failure: report to user, request guidance
  5. Learn from failure: store which method works for which app
```

### 3.11 Remote Control Architecture

```
REMOTE CONTROL via Telegram Bot:

Phone (Telegram App)
         │
         ▼ (HTTPS — Telegram's servers)
    Telegram Bot API
         │
         ▼ (polling / webhook)
┌──────────────────────────────────────────────────────────┐
│               JARVIS TELEGRAM INTERFACE                   │
│                                                           │
│  Commands:                                                │
│  /status    → JARVIS status, active tasks                 │
│  /stop      → Emergency stop all operations               │
│  /ask [msg] → Send text command to JARVIS                 │
│  /memory    → Show recent memories                        │
│  /tasks     → Show pending/running tasks                  │
│  /models    → Show available models                       │
│  /skill     → List installed skills                       │
│  /learn [X] → Start learning a new skill                  │
│  /file [X]  → Request a file from JARVIS laptop           │
│                                                           │
│  Notifications pushed automatically:                      │
│  - Task completed                                         │
│  - Task failed                                            │
│  - Permission required (with inline approve/deny buttons) │
│  - JARVIS ready                                           │
│  - System alerts                                          │
│                                                           │
│  Voice messages:                                          │
│  → Telegram sends audio to JARVIS                         │
│  → JARVIS transcribes with Whisper                        │
│  → Processes as normal voice command                      │
│  → Responds with text (and optional voice note)           │
└──────────────────────────────────────────────────────────┘
```

---

## PART 4: COMPLETE FOLDER STRUCTURE

```
jarvis-v3/
│
├── pyproject.toml              # Proper Python package definition
├── requirements.txt            # Pinned dependencies
├── requirements-dev.txt        # Dev/test dependencies
├── .env.example                # Config template (not .env.txt)
├── .gitignore
├── README.md
│
├── scripts/
│   ├── install.py              # One-click installer
│   ├── install_models.py       # Download recommended Ollama models
│   ├── install_voice.py        # Download Piper/MeloTTS models
│   ├── health_check.py         # Verify system is working
│   └── migrate_v2.py           # Migrate V2 data to V3
│
├── apps/
│   └── desktop/                # Desktop Application
│       ├── __main__.py         # Entry point: python -m apps.desktop
│       ├── app.py              # QApplication + main window setup
│       ├── launcher.py         # System tray + process manager
│       │
│       ├── ui/
│       │   ├── main_window.py  # Main JARVIS window
│       │   ├── widgets/
│       │   │   ├── chat_widget.py          # Chat display
│       │   │   ├── voice_indicator.py      # Animated voice status
│       │   │   ├── thinking_animation.py   # Arc reactor style animation
│       │   │   ├── agent_status_panel.py   # Live agent activity
│       │   │   ├── tool_execution_viz.py   # Tool call visualization
│       │   │   ├── memory_panel.py         # Memory browser
│       │   │   ├── skill_panel.py          # Skill manager
│       │   │   ├── model_panel.py          # Model selector
│       │   │   └── settings_panel.py       # Config UI
│       │   │
│       │   └── themes/
│       │       ├── jarvis_dark.qss         # Iron Man dark glassmorphism
│       │       ├── jarvis_colors.py        # Color constants
│       │       └── fonts/                  # Custom fonts (Rajdhani, Orbitron)
│       │
│       └── assets/
│           ├── icons/          # App icons
│           ├── sounds/         # UI sound effects
│           └── animations/     # Lottie/GIF animations
│
├── core/
│   ├── __init__.py
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── jarvis.py           # Main JARVIS orchestrator class
│   │   ├── event_bus.py        # Async pub/sub event system
│   │   ├── process_manager.py  # Subprocess lifecycle management
│   │   ├── config.py           # Pydantic settings with validation
│   │   └── logger.py           # Structured logging (rotating files)
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py            # JarvisState TypedDict
│   │   ├── jarvis_graph.py     # LangGraph StateGraph definition
│   │   ├── conditions.py       # Edge conditions / routing logic
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── input_node.py   # Input normalization + intent extraction
│   │       ├── planner_node.py # Task decomposition
│   │       ├── router_node.py  # Agent + model selection
│   │       ├── executor_node.py# Agent dispatch
│   │       ├── memory_node.py  # Memory retrieval + storage
│   │       └── output_node.py  # Response formatting + delivery
│   │
│   └── agents/
│       ├── __init__.py
│       ├── base_agent.py       # Abstract base agent
│       ├── coordinator.py      # Orchestrates multi-agent tasks
│       ├── planner.py          # Task planner
│       ├── researcher.py       # Web research agent
│       ├── coder.py            # Code writing + debugging
│       ├── debugger.py         # Error analysis + fixes
│       ├── learner.py          # New skill acquisition
│       ├── memory_agent.py     # Memory operations
│       ├── tool_agent.py       # Tool execution
│       └── security_agent.py   # Security review (pre-execution)
│
├── brain/
│   ├── __init__.py
│   ├── router.py               # Intelligent model router
│   ├── registry.py             # Auto-discovers + registers Ollama models
│   ├── benchmarker.py          # Benchmarks models on standard tasks
│   ├── capability_map.py       # Maps task types to model capabilities
│   └── providers/
│       ├── __init__.py
│       ├── base_provider.py    # Abstract provider interface
│       ├── ollama_provider.py  # Ollama local provider
│       ├── anthropic_provider.py # Claude API (optional)
│       ├── openai_provider.py  # OpenAI API (optional)
│       └── app_provider.py     # Desktop AI app fallback
│
├── memory/
│   ├── __init__.py
│   ├── manager.py              # Unified memory interface
│   ├── retriever.py            # Multi-source ranked retrieval
│   ├── consolidator.py         # Nightly memory consolidation
│   └── stores/
│       ├── __init__.py
│       ├── short_term.py       # In-memory ring buffer (20 msgs)
│       ├── episodic.py         # SQLite conversation log
│       ├── semantic.py         # ChromaDB vector store
│       ├── skill_memory.py     # Skill profiles (SQLite + JSON)
│       ├── project_memory.py   # Project context store
│       └── preference.py       # User preference store
│
├── voice/
│   ├── __init__.py
│   ├── pipeline.py             # Orchestrates all voice components
│   ├── state_machine.py        # Voice state machine (IDLE/ACTIVATED/etc.)
│   │
│   ├── wake_word/
│   │   ├── __init__.py
│   │   ├── detector.py         # OpenWakeWord wrapper
│   │   ├── custom_model.py     # Custom wake word training support
│   │   └── models/             # ONNX wake word models
│   │
│   ├── stt/
│   │   ├── __init__.py
│   │   ├── engine.py           # STT dispatcher
│   │   ├── whisper_engine.py   # Faster-Whisper backend
│   │   └── vad.py              # Voice activity detection
│   │
│   └── tts/
│       ├── __init__.py
│       ├── engine.py           # TTS dispatcher
│       ├── piper_backend.py    # Piper TTS
│       ├── melo_backend.py     # MeloTTS (higher quality)
│       ├── stream.py           # Streaming TTS output
│       └── models/             # TTS ONNX models
│
├── tools/
│   ├── __init__.py
│   ├── registry.py             # Auto-discovers + registers tools
│   ├── base_tool.py            # Abstract Tool interface (LangChain compatible)
│   │
│   ├── web/
│   │   ├── __init__.py
│   │   ├── searcher.py         # DuckDuckGo + Bing + SearXNG
│   │   └── scraper.py          # Playwright async scraper
│   │
│   ├── files/
│   │   ├── __init__.py
│   │   ├── manager.py          # Read, write, move, delete (with perms)
│   │   ├── pdf_tool.py         # PDF creation + reading (reportlab + pypdf)
│   │   ├── office_tool.py      # DOCX + PPTX + XLSX (python-docx/pptx/openpyxl)
│   │   └── code_tool.py        # Code file operations
│   │
│   ├── system/
│   │   ├── __init__.py
│   │   ├── app_controller.py   # Multi-priority app control
│   │   ├── process_tool.py     # Process management
│   │   ├── clipboard_tool.py   # Safe clipboard operations
│   │   └── windows_automation.py # pywinauto wrapper
│   │
│   ├── ai_apps/
│   │   ├── __init__.py
│   │   ├── base_app.py         # Abstract AI app interface
│   │   ├── claude_app.py       # Claude Desktop automation
│   │   ├── chatgpt_app.py      # ChatGPT Desktop automation
│   │   └── browser_ai.py       # Browser-based AI (Gemini, Grok, DeepSeek)
│   │
│   ├── github/
│   │   ├── __init__.py
│   │   └── github_tool.py      # GitHub search, clone, read
│   │
│   └── code/
│       ├── __init__.py
│       ├── executor.py         # Sandboxed code execution
│       └── sandbox.py          # RestrictedPython + subprocess isolation
│
├── skills/
│   ├── __init__.py
│   ├── manager.py              # Install/update/remove skills
│   ├── learner.py              # Skill acquisition orchestrator
│   ├── validator.py            # Skill validation + self-quiz
│   └── builtin/
│       ├── __init__.py
│       ├── research/           # Research skill
│       │   ├── skill.json
│       │   └── tools.py
│       ├── coding/             # Software development skill
│       │   ├── skill.json
│       │   └── tools.py
│       └── automation/         # System automation skill
│           ├── skill.json
│           └── tools.py
│
├── security/
│   ├── __init__.py
│   ├── guard.py                # Enhanced security guard (V3)
│   ├── risk_scorer.py          # LLM-powered risk assessment
│   ├── audit.py                # Append-only audit log
│   ├── sandbox.py              # Execution sandbox
│   └── permissions.py          # Permission system
│
├── remote/
│   ├── __init__.py
│   ├── telegram_bot.py         # Telegram remote control
│   ├── api_server.py           # FastAPI REST + WebSocket
│   └── notifications.py        # Push notification system
│
├── self_improve/
│   ├── __init__.py
│   ├── editor.py               # Enhanced self-editor
│   ├── tester.py               # Automated test runner
│   ├── validator.py            # Change validation pipeline
│   └── git_manager.py          # Git versioning for self-edits
│
└── data/
    ├── memory/                 # ChromaDB storage
    ├── skills/                 # Installed skill data + knowledge
    ├── models/                 # Model configs + benchmark results
    ├── logs/                   # Audit + operation logs (SQLite + files)
    ├── backups/                # Self-edit backups (git repo)
    └── cache/                  # Temporary cache (auto-cleaned)
```

---

## PART 5: TECHNOLOGY STACK

### Decision Rationale

All technology decisions are made against these criteria, in priority order:
1. Offline-capable (no mandatory internet)
2. Runs on 4GB VRAM (quantized where needed)
3. Actively maintained open-source
4. Python-native where possible (ease of self-modification)
5. Production quality

### Complete Stack

| Layer | Choice | Version | Reason |
|-------|--------|---------|--------|
| **Python** | Python 3.11 | 3.11.x | Best balance of features + performance. 3.12 has breaking changes in some LangChain deps. |
| **Package Mgmt** | uv | latest | 10-100x faster than pip. Modern replacement for pip + venv. |
| **Desktop UI** | PySide6 | 6.7.x | Qt6 via Python. Glassmorphism via QGraphicsEffect. No Node.js. 32MB app size vs 150MB Electron. Native Windows APIs. |
| **Agent Framework** | LangGraph | 0.2.x | Stateful graph execution. Handles cycles, conditional edges, parallel agents. Best for multi-agent orchestration. |
| **LLM Orchestration** | LangChain | 0.3.x | Tool definitions, prompt templates, provider abstraction. |
| **Local LLMs** | Ollama | latest | REST API + GPU acceleration. Auto-discovers models. Handles quantization. |
| **Primary Model** | Qwen2.5:7B | q4 quant | Best 7B model as of 2025. Excellent instruction following. ~4GB VRAM in q4. |
| **Code Model** | Qwen2.5-Coder:7B | q4 quant | Purpose-built for code. Outperforms CodeLlama. Same VRAM footprint. |
| **Reasoning Model** | DeepSeek-R1:7B | q4 quant | Chain-of-thought reasoning. Good for planning + analysis. |
| **Fast Model** | Phi-3.5:3.8B | q4 quant | Fast responses for simple queries. 2GB VRAM. |
| **Vector Store** | ChromaDB | 0.5.x | Embedded, no server needed. Good Python API. HNSW indexing. |
| **SQL Store** | SQLite | via SQLAlchemy 2.0 | Episodic memory, audit logs, user profile. |
| **Embeddings** | sentence-transformers | 3.x | all-MiniLM-L6-v2 (fast) or all-mpnet-base-v2 (quality). CPU inference. |
| **Async** | asyncio | stdlib | All I/O is async. No threading for I/O (use async). Threads only for CPU-bound. |
| **HTTP** | aiohttp | 3.x | Async HTTP client for Ollama API + web scraping. |
| **API Server** | FastAPI | 0.11x | WebSocket + REST for remote control + UI communication. |
| **Wake Word** | OpenWakeWord | latest | ONNX inference. Low CPU. Offline. Custom model support. |
| **STT** | faster-whisper | 1.x | CUDA-accelerated Whisper. base.en for speed, small.en for accuracy. |
| **TTS** | MeloTTS | latest | More natural than Piper. Supports emotions. Python-native. Female voice (EN-US). |
| **TTS Fallback** | Piper | latest | Still excellent. Faster than MeloTTS. Piper as backup. |
| **Audio I/O** | sounddevice | latest | Low-latency audio. PortAudio backend. |
| **Web Scraping** | Playwright | 1.x | Full browser automation. Handles JS. Better than BeautifulSoup. |
| **Desktop Automation** | pywinauto | latest | Windows UI Automation. Works on any resolution. |
| **Remote Control** | python-telegram-bot | 21.x | Async Telegram Bot. Inline keyboards for approval prompts. |
| **Sandboxing** | RestrictedPython | 7.x | Safe Python execution. |
| **Config** | Pydantic-settings | 2.x | Config validation. Type-safe .env loading. |
| **Logging** | structlog | 24.x | Structured logs (JSON). Rotation. Log levels. |
| **Testing** | pytest + pytest-asyncio | 8.x | Async test support. |
| **Git** | GitPython | latest | For self-edit versioning. |

### Hardware Budget (4GB VRAM)

| Component | VRAM Usage | Notes |
|-----------|-----------|-------|
| Qwen2.5:7B (q4) | ~4.0 GB | Primary reasoning |
| Qwen2.5-Coder:7B (q4) | ~4.0 GB | Cannot run simultaneously |
| Phi-3.5:3.8B (q4) | ~2.2 GB | Can co-exist with small tools |
| Whisper base.en | ~150 MB | Always loaded |
| Sentence-transformers | ~90 MB | Always loaded |
| MeloTTS | ~200 MB | Loaded on demand |

**Strategy:** Only one large model loaded at a time. Phi-3.5 stays resident for quick responses. Larger models loaded/unloaded per task via Ollama. Whisper + embeddings always in VRAM.

---

## PART 6: IMPLEMENTATION ROADMAP

### Phase 0 — Foundation (Week 1)
*Prerequisites: uv installed, Python 3.11, Ollama running*

**Goals:**
- Project scaffolding
- Configuration system (Pydantic settings)
- Structured logging
- Event bus
- Process manager
- Health check script

**Deliverables:**
- `pyproject.toml` with all pinned dependencies
- `core/engine/config.py` — validated config loading
- `core/engine/event_bus.py` — async pub/sub
- `core/engine/logger.py` — structured logging
- `scripts/install.py` — one-click setup
- `scripts/health_check.py` — validates installation

**Success Criteria:**
- `python -m scripts.health_check` passes all checks
- Config loads from .env with validation errors on bad values
- Event bus handles 1000+ events/sec without blocking

---

### Phase 1 — Core Intelligence (Weeks 2-4)
*Build the brain before the face*

**Goals:**
- LangGraph state machine (complete)
- Basic LLM conversation (Ollama)
- Memory V2 (short-term + episodic)
- Model registry + router (basic)
- Text-based REPL (temporary, for testing)

**Deliverables:**
- `core/graph/state.py` — JarvisState
- `core/graph/jarvis_graph.py` — Full LangGraph definition
- `core/graph/nodes/` — All 6 nodes
- `core/agents/base_agent.py` + `coordinator.py`
- `brain/registry.py` — Ollama model auto-discovery
- `brain/router.py` — Basic task-to-model routing
- `memory/stores/short_term.py` — Ring buffer
- `memory/stores/episodic.py` — SQLite store
- `memory/manager.py` — Unified interface
- Temporary `dev_repl.py` — Test CLI (not production)

**Success Criteria:**
- Multi-turn conversation with memory ("what did I say earlier")
- Router correctly picks phi3.5 for chat, qwen-coder for code
- New Ollama models auto-detected within 30 seconds

---

### Phase 2 — Voice Pipeline (Weeks 5-6)
*Make JARVIS speak and listen*

**Goals:**
- Complete voice state machine
- Wake word (OpenWakeWord)
- STT (faster-whisper)
- TTS (MeloTTS)
- No audio feedback bug
- Interrupt support

**Deliverables:**
- `voice/state_machine.py` — Full state machine
- `voice/wake_word/detector.py` — Fixed OpenWakeWord wrapper
- `voice/stt/whisper_engine.py` — Async Whisper
- `voice/tts/melo_backend.py` — MeloTTS integration
- `voice/tts/piper_backend.py` — Piper fallback
- `voice/pipeline.py` — Orchestrator

**Success Criteria:**
- Wake word works offline
- No audio feedback on activation ("Yes Sir?" plays with mic muted)
- User can interrupt JARVIS mid-sentence
- TTS sounds natural (MeloTTS female voice)
- Voice pipeline survives 4+ hours without crash

---

### Phase 3 — Desktop Application (Weeks 7-9)
*Build the Iron Man UI*

**Goals:**
- PySide6 desktop app
- Iron Man glassmorphism theme
- Chat interface
- Voice indicator (animated)
- Agent status panel
- System tray integration

**Deliverables:**
- `apps/desktop/app.py` — Main app
- `apps/desktop/ui/main_window.py` — Main window
- `apps/desktop/ui/widgets/chat_widget.py`
- `apps/desktop/ui/widgets/voice_indicator.py`
- `apps/desktop/ui/widgets/agent_status_panel.py`
- `apps/desktop/ui/widgets/thinking_animation.py`
- `apps/desktop/ui/themes/jarvis_dark.qss`
- `apps/desktop/launcher.py` — System tray + auto-start

**Visual Requirements:**
- Dark background (#0A0E1A — deep navy)
- Accent: Electric blue (#00D4FF) + cyan glow (#00FFCC)
- Glass panels: rgba(255,255,255,0.05) with blur
- Font: Rajdhani (technical) for body, Orbitron (sci-fi) for headers
- Animated arc reactor pulse on thinking
- Waveform animation on speaking
- Particle/line animation on idle

**Success Criteria:**
- App launches automatically on Windows startup
- Chat works (text + voice)
- Voice indicator shows correct state in real-time
- UI never freezes (async guaranteed)

---

### Phase 4 — Tools & App Controller (Weeks 10-12)
*Give JARVIS hands*

**Goals:**
- Web search (DuckDuckGo + Playwright)
- File operations
- Code execution (sandboxed)
- App controller (multi-priority hierarchy)
- GitHub tool

**Deliverables:**
- `tools/web/searcher.py` + `scraper.py`
- `tools/files/manager.py` + all file tools
- `tools/code/executor.py` + `sandbox.py`
- `tools/system/app_controller.py` (all 5 priority methods)
- `tools/ai_apps/claude_app.py` + `chatgpt_app.py`
- `tools/github/github_tool.py`
- `security/guard.py` V3 (LLM-powered risk scoring)
- `security/audit.py` (append-only log)

**Success Criteria:**
- App controller works with Claude Desktop (CDP method)
- Security guard cannot be bypassed by rephrasing
- Code execution is isolated (cannot touch JARVIS files)
- All operations logged to audit trail

---

### Phase 5 — Memory V3 + Self-Improvement (Weeks 13-14)
*Give JARVIS a mind and the ability to grow*

**Goals:**
- Semantic memory (ChromaDB + embeddings)
- Memory consolidation
- Self-editor V3 (git-backed)
- Learning engine (basic: research + store)

**Deliverables:**
- `memory/stores/semantic.py`
- `memory/retriever.py` — Ranked multi-source retrieval
- `memory/consolidator.py`
- `self_improve/editor.py` — Git-backed self-editor
- `self_improve/tester.py` — Import + unit test after edit
- `skills/learner.py` — "JARVIS learn X" pipeline

**Success Criteria:**
- "What did I tell you about Monday?" returns correct memory
- Self-edit creates git commit before and after change
- Self-edit rolls back if import test fails
- "JARVIS learn Python asyncio" builds a usable knowledge base

---

### Phase 6 — Remote Control (Week 15)
*Control JARVIS from phone*

**Goals:**
- Telegram bot
- Remote commands
- Push notifications
- Remote voice messages
- Permission approval via Telegram

**Deliverables:**
- `remote/telegram_bot.py`
- `remote/api_server.py` (FastAPI)
- `remote/notifications.py`

**Success Criteria:**
- `/status` shows current JARVIS state from phone
- `/ask create a file called test.txt` works remotely
- Security confirmations show up as Telegram inline buttons
- Voice message from phone transcribed and processed

---

### Phase 7 — Multi-Agent Specialization (Week 16-17)
*Deploy the full agent team*

**Goals:**
- Planner agent
- Researcher agent
- Coder agent
- Debugger agent
- Learner agent
- Memory agent

**Deliverables:**
- `core/agents/planner.py`
- `core/agents/researcher.py`
- `core/agents/coder.py`
- `core/agents/debugger.py`
- `core/agents/learner.py`
- `core/agents/memory_agent.py`

**Success Criteria:**
- "Research the latest developments in transformer architecture and write a 5-page report" runs correctly through Planner → Researcher → Coder → Output
- Parallel agent execution for independent subtasks
- Coder can write, test, and fix its own code in a loop

---

### Phase 8 — Skill System + Model Benchmarks (Week 18)
*Make JARVIS extensible*

**Goals:**
- Skill install/uninstall
- Skill discovery
- Model benchmarking
- Capability map

**Deliverables:**
- `skills/manager.py`
- `brain/benchmarker.py`
- `brain/capability_map.py`
- Builtin skills: research, coding, automation

**Success Criteria:**
- "JARVIS, install the cybersecurity skill" downloads and activates it
- Model benchmark runs on first startup, results stored
- Router uses benchmark data to improve routing decisions

---

### Phase 9 — Production Polish (Weeks 19-20)
*Harden everything*

**Goals:**
- Error monitoring
- Crash recovery
- Performance profiling
- Full test suite
- Documentation

**Deliverables:**
- Full `tests/` suite (unit + integration + e2e)
- Crash recovery: JARVIS restarts automatically after crash
- Performance dashboard (response times, model usage)
- Comprehensive README + per-module docs

---

## RISK ANALYSIS

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Ollama VRAM overflow when switching models | HIGH | HIGH | Explicit model unload before loading new model. VRAM monitoring. |
| Wake word false positives in noisy environment | MEDIUM | MEDIUM | Tunable threshold. "Confidence" mode that requires 2 detections. |
| MeloTTS quality regression on some voices | MEDIUM | LOW | Piper fallback always available. |
| LangGraph cycle detection (infinite agent loops) | MEDIUM | HIGH | Max iterations per agent (default 10). Circuit breaker pattern. |
| Self-edit breaks JARVIS on bad LLM suggestion | MEDIUM | CRITICAL | Git backup + import test + rollback. Protected critical modules. |
| Telegram bot token exposed | LOW | HIGH | Token stored in .env only. Not committed to git. |
| PySide6 rendering issues on some GPU drivers | LOW | MEDIUM | Software rendering fallback. Test on target hardware. |
| ChromaDB corruption | LOW | HIGH | Regular SQLite backups. ChromaDB export on shutdown. |
| Playwright fingerprinting detection (AI apps block bot) | MEDIUM | MEDIUM | Realistic mouse movements. CDP stealth mode. API fallback. |

---

## TESTING STRATEGY

### Unit Tests (per module)
- Every public function tested in isolation
- Mock Ollama, ChromaDB, sounddevice
- Parametrized tests for router decisions
- Security guard tested with 50+ bypass attempts

### Integration Tests
- Voice pipeline end-to-end (mock audio input)
- LangGraph state transitions
- Memory store + retrieval round-trip
- Tool execution with real file system (temp dir)

### E2E Tests (automated JARVIS conversations)
- "What is my name?" → correct memory retrieval
- "Write a Python function to sort a list" → code output
- "Search for latest AI news" → web search + summary
- Self-edit cycle → backup → apply → rollback

### Hardware Tests (manual, on your machine)
- 4-hour voice session stability
- VRAM usage under sustained load
- Response time benchmarks per model
- App controller vs Claude Desktop

---

## NEXT STEPS

Sir, this document is complete. Before I begin implementation, I need your approval on two specific decisions:

**Decision 1: Desktop UI Framework**
I recommend **PySide6** (Qt6 — pure Python, no Node.js, easier for you to modify). Alternative is Electron + React (better CSS animations but requires Node.js). Which do you prefer?

**Decision 2: TTS Primary Voice**
I recommend **MeloTTS** as primary (more natural, emotion support, female voice). Piper as fallback. Alternatively, Piper-only is faster to set up. Do you want MeloTTS as primary, or Piper only?

Once you approve the architecture and answer these two questions, I will begin Phase 0 implementation immediately.
```

---
*Document prepared by Chief AI Architect — JARVIS V3 Project*
*All design decisions are justified, challengeable, and open to revision.*
