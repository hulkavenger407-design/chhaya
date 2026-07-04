# Chhaya: Self-Learning AI Agent Factory

"Chhaya" (Hindi/Sanskrit for "shadow/reflection") is a self-improving, autonomous agent factory. It designs, builds, runs, evaluates, and improves specialized agents on demand across any domain.

## Core Principles
1. **Modular by design**: Agents are defined by a structured "Agent Blueprint", not hardcoded logic.
2. **Local-first inference**: Built around Ollama (14B for reasoning, 7B for execution), behind a swappable interface.
3. **Self-improvement is real but bounded**: Proposes changes to prompts and tools; changes are versioned and diffable. No silent overwrites.
4. **Autonomy with guardrails**: External-facing actions require explicit user approval.
5. **Ship incrementally**: Building working, testable vertical slices.

## Advanced Architecture (Clean Architecture & SOLID)
- **Event-Driven**: Internal event bus for decoupled component communication.
- **Provider Abstractions**: Swappable interfaces for LLMs (`LLMProvider`) and Storage (`StorageProvider`).
- **Plugin System**: Dynamically load new custom tools via the `ToolPlugin` interface.
- **Isolated Workspaces**: Every agent operates within its own `Workspace` to prevent cross-contamination.
- **Configuration**: YAML-based configuration (`config/config.yaml`) alongside environment variables.

## Tech Stack
Python 3.11+, FastAPI, SQLModel (SQLite), ChromaDB, Typer, Pydantic, pytest, structlog.

## Setup Instructions
1. Install Python 3.11+
2. Clone the repository.
3. Install dependencies: `pip install -e .[dev]`
4. Copy `.env.example` to `.env` and configure your endpoints (e.g., Ollama).
5. Review `config/config.yaml`.
6. Run tests: `pytest`
