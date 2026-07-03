# High-Level System Architecture

This diagram illustrates the macro-level architecture of Chhaya (JARVIS V3), highlighting the separation of interfaces, core intelligence, and external integrations.

```mermaid
graph TD
    User([User])

    subgraph Interfaces [Phase 3 & 6: Interfaces]
        Desktop[Desktop UI - PySide6]
        CLI[Terminal CLI]
        Remote[Telegram / Mobile]
        Voice[Voice Pipeline - STT/TTS]
    end

    subgraph Brain [Phase 1: Core Intelligence]
        Router[Task Router]
        Registry[Ollama Registry]
        LangGraph[LangGraph State Machine]
        Coordinator[Coordinator Agent]
    end

    subgraph Tools [Phase 4: Tool System]
        Web[Web Search & Scrape]
        Files[File Operations]
        System[App Controller]
        Code[Sandboxed Executor]
    end

    subgraph Memory [Phase 5: Memory V3]
        ShortTerm[(Ring Buffer)]
        Episodic[(SQLite)]
        Semantic[(ChromaDB)]
    end

    subgraph Guard [Phase 4: Security]
        Audit[(Audit Log)]
        Risk[LLM Guard]
    end

    User -->|Voice/Text| Interfaces
    Interfaces -->|Payload| Brain
    Brain <-->|State Update| Memory
    Brain -->|Execute| Guard
    Guard -->|Approve| Tools
    Tools -->|Result| Brain
    Brain -->|Response| Interfaces
```
