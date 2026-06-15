"""
jarvis/core/router.py — JARVIS v2 Final

Fixes:
- file_creation HIGH PRIORITY (pdf/doc/excel etc always wins)
- "ask claude X" / "ask chatgpt X" → forces that specific AI
- Hindi keywords supported
"""

from jarvis.core.state import JARVISState

TASK_TYPES = {
    "coding":        "Write, debug, explain, or run code",
    "web_search":    "Search the web, browse, download",
    "file_creation": "Create PDF, PPTX, DOCX, XLSX files",
    "assistant":     "Reminders, tasks, scheduling, personal management",
    "self_edit":     "JARVIS edits or improves its own source code",
    "memory_query":  "Recall something from past sessions",
    "github":        "Search GitHub, read repos, clone, learn from open source",
    "chat":          "General conversation, questions, explanations",
}

# ── HIGH PRIORITY — checked first, override everything ─────────
HIGH_PRIORITY = {
    "file_creation": [
        "pdf", "ppt", "pptx", "docx", "doc", "xlsx", "xls",
        "excel", "spreadsheet", "powerpoint", "presentation",
        "word document", "word file", "slides", "slide deck",
        "make a file", "create a file", "generate a file",
        "bana", "banao", "bana ke", "bana do", "de do",
        "report bana", "file bana", "pdf bana", "doc bana",
    ],
    "coding": [
        "```python", "```js", "```bash", "run this code",
        "execute this", "debug this", "fix this code",
    ],
    "self_edit": [
        "improve yourself", "edit your code", "fix yourself",
        "upgrade yourself", "list modules", "show module",
        "show jarvis/", "apna code",
    ],
    "github": [
        "github", "git clone", "trending repos", "open source repo",
    ],
}

# ── "ask claude X" → force claude as brain ────────────────────
AI_FORCE_MAP = {
    "ask claude":   "claude",
    "use claude":   "claude",
    "claude se":    "claude",
    "claude ko":    "claude",
    "tell claude":  "claude",
    "ask chatgpt":  "chatgpt",
    "use chatgpt":  "chatgpt",
    "chatgpt se":   "chatgpt",
    "ask deepseek": "deepseek",
    "deepseek se":  "deepseek",
    "ask gemini":   "gemini",
    "gemini se":    "gemini",
    "ask grok":     "grok",
}

# ── Normal scoring keywords ────────────────────────────────────
KEYWORD_MAP = {
    "web_search": [
        "search", "find online", "look up", "browse", "google",
        "download", "website", "web", "internet", "latest news",
        "what is happening", "current events", "news today",
        "price of", "go to", "navigate to", "youtube", "bing",
        "dhundh", "khoj", "search kar",
    ],
    "assistant": [
        "remind me", "schedule", "calendar", "to-do", "todo",
        "task list", "set a reminder", "add a task",
        "note", "remember to", "yaad dilao", "reminder set",
    ],
    "memory_query": [
        "what did i ask", "do you remember", "recall",
        "last time", "previously", "what was that",
        "earlier today", "yesterday", "last week",
        "pehle", "yaad he", "bataya tha", "humne",
    ],
    "chat": [
        "how are you", "what do you think", "tell me about",
        "explain", "what is", "who is", "why does", "how does",
        "can you", "could you", "would you", "i need help",
        "help me understand", "what are", "describe", "bata",
        "samjhao", "kya he", "kaun he", "kya hai",
    ],
}


def extract_forced_ai(text: str):
    """
    If user says 'ask claude X', returns ('claude', 'X').
    Used to force a specific AI regardless of task routing.
    """
    text_lower = text.lower()
    for phrase, ai_name in AI_FORCE_MAP.items():
        if phrase in text_lower:
            # Remove "ask claude" prefix, keep the actual question
            idx   = text_lower.index(phrase)
            clean = text[idx + len(phrase):].strip()
            return ai_name, clean if clean else text
    return None, text


def keyword_route(text: str) -> str | None:
    text_lower = text.lower()

    # Step 1: High priority — file/code/self_edit/github always wins
    for task, keywords in HIGH_PRIORITY.items():
        for kw in keywords:
            if kw in text_lower:
                return task

    # Step 2: Score normal keywords
    scores = {task: 0 for task in KEYWORD_MAP}
    for task, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                scores[task] += 1

    best_task  = max(scores, key=scores.get)
    best_score = scores[best_task]
    if best_score >= 1:
        return best_task

    return None


def llm_route(text: str, llm) -> str:
    prompt = (
        f"Classify into EXACTLY ONE: coding|web_search|file_creation|assistant|self_edit|github|memory_query|chat\n"
        f"RULE: If user wants to CREATE any file (pdf/doc/ppt/excel/report/slides) → file_creation\n"
        f"Command: \"{text}\"\n"
        f"Reply with ONLY the category word."
    )
    try:
        response = llm.invoke(prompt)
        result   = response.content.strip().lower()
        if result in TASK_TYPES:
            return result
    except Exception:
        pass
    return "chat"


def task_router(state: JARVISState, llm=None) -> JARVISState:
    user_input = state["raw_input"]

    # Check if user forced a specific AI ("ask claude X")
    forced_ai, clean_input = extract_forced_ai(user_input)
    if forced_ai:
        # Store forced AI so brain_selector can use it
        state["forced_ai"]  = forced_ai
        state["raw_input"]  = clean_input   # use cleaned question
        user_input          = clean_input
        print(f"\n  [Router] Forced AI: {forced_ai}")
    else:
        state["forced_ai"] = ""

    # Route the task
    task = keyword_route(user_input)
    if task is None and llm is not None:
        task = llm_route(user_input, llm)
    elif task is None:
        task = "chat"

    print(f"\n  [Router] '{user_input[:55]}' → {task}")
    state["task_type"] = task
    return state


def route_decision(state: JARVISState) -> str:
    return state["task_type"]
