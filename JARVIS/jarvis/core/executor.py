"""
jarvis/core/executor.py — JARVIS v2

Dispatcher — calls the right tool or LLM based on task type.
Handles both Ollama LLMs and AppControllerLLM (desktop/web apps).
"""

import time
import re
from jarvis.core.state      import JARVISState
from jarvis.brain.selector  import get_current_llm, get_current_mode, get_current_name, _mark_cooldown
from jarvis.memory.memory   import get_memory

JARVIS_SYSTEM_PROMPT = """You are JARVIS, personal AI assistant to Yogi.
Address user as Sir until you know their name. Then use only their name (not Sir+name together).
Be concise, max 3 lines unless asked for detail.
Never say I cannot. Never break character. Never mention the underlying model.
One direct answer. Stop. No disclaimers. No repetition. You are JARVIS."""

# Phrases that mean the AI hit its usage limit
LIMIT_PHRASES = [
    "you've reached your limit", "rate limit", "too many requests",
    "usage limit", "message limit", "try again in", "upgrade your plan",
    "you can't send more", "free tier", "quota exceeded",
    "you've hit the", "slow down", "please wait before",
]


def _check_limit_in_response(response: str, ai_name: str) -> bool:
    """If response contains a limit message, mark that AI in cooldown."""
    r_lower = response.lower()
    for phrase in LIMIT_PHRASES:
        if phrase in r_lower:
            _mark_cooldown(ai_name)
            return True
    return False


def _invoke_llm(user_input: str, task_type: str, memory_ctx: str,
                recent: list, user_name: str) -> str:
    """
    Universal LLM invoke — works for both Ollama LLMs and AppControllerLLM.
    """
    llm  = get_current_llm()
    mode = get_current_mode()
    name = get_current_name()

    if llm is None:
        return "Error: No brain loaded. Run setup.py first."

    # Build system + messages
    system = JARVIS_SYSTEM_PROMPT
    if user_name and user_name != "Sir":
        system += f"\nUser's name is {user_name}. Address them as {user_name}."
    if memory_ctx:
        system += f"\n\nRelevant memory:\n{memory_ctx}"

    messages = [("system", system)]
    for role, content in recent:
        messages.append((role, content))
    messages.append(("human", user_input))

    # Ollama needs the stop instruction
    if mode == "offline":
        messages.append(("system", "Give ONE response only. Stop after your answer."))

    try:
        # AppControllerLLM — let it handle everything
        if mode in ("desktop-app", "web-app"):
            print(f"  [Executor] Sending to {name} ({mode})...")
            response = llm.invoke(messages)
            answer   = response.content.strip()

            # Check for limit message
            if _check_limit_in_response(answer, name):
                print(f"  [Executor] {name} hit limit — retrying with next AI...")
                # Retry once with next available AI
                from jarvis.brain.selector import get_best_llm, check_internet
                online = check_internet()
                new_llm, new_mode, new_name = get_best_llm(task_type, online)
                from jarvis.brain import selector as sel
                sel._current_llm  = new_llm
                sel._current_mode = new_mode
                sel._current_name = new_name
                return _invoke_llm(user_input, task_type, memory_ctx, recent, user_name)

            return answer

        # API or Offline (Ollama) — standard invoke
        else:
            from langchain_ollama import ChatOllama
            # For Ollama, re-init with proper options
            if mode == "offline":
                actual_model = getattr(llm, "model", "phi3.5")
                llm_call = ChatOllama(
                    model=actual_model,
                    temperature=0.1,
                    timeout=30,
                    num_predict=150,
                )
            else:
                llm_call = llm   # API LLM — use as-is

            response = llm_call.invoke(messages)
            answer   = response.content.strip()

            # Cut off model self-conversation loops
            for stop in ["Sir:", "User:", "Human:", "JARVIS:", "---\n", "\n\n---"]:
                if stop in answer:
                    answer = answer.split(stop)[0].strip()

            return answer

    except Exception as e:
        return f"Brain error: {str(e)}"


# ── Tool handlers ──────────────────────────────────────────────

def _handle_web_search(user_input: str) -> str:
    try:
        from jarvis.tools.web_search.searcher import web_search_tool
        fetch = any(w in user_input.lower() for w in ["read", "open", "content", "details", "fetch"])
        query = re.sub(r"(search for|search|find|look up|google|browse|internet pe|web pe)\s+",
                       "", user_input, flags=re.IGNORECASE).strip()
        return web_search_tool(query, fetch_content=fetch)
    except Exception as e:
        return f"Web search error: {e}"


def _handle_file_creation(user_input: str, memory_ctx: str, recent: list, user_name: str) -> str:
    try:
        from jarvis.tools.file_creator.file_maker import create_file_tool
        text_lower = user_input.lower()

        # Detect file type
        if any(w in text_lower for w in ["pdf"]):
            file_type = "pdf"
        elif any(w in text_lower for w in ["ppt", "presentation", "slide", "powerpoint"]):
            file_type = "pptx"
        elif any(w in text_lower for w in ["doc", "word"]):
            file_type = "docx"
        elif any(w in text_lower for w in ["excel", "xlsx", "spreadsheet"]):
            file_type = "xlsx"
        else:
            file_type = "pdf"

        # Extract title from request
        title_match = re.search(
            r"(?:about|on|titled?|called?|jisme|mein|pe|par)\s+['\"]?(.+?)['\"]?\s*(?:ke|ka|ki|likha|bana|create|make|$)",
            user_input, re.IGNORECASE
        )
        if title_match:
            title = title_match.group(1).strip()
        else:
            # Fallback: take last meaningful part
            title = re.sub(r"(bana ke de|create|make|ek|a |an |the )", "", user_input, flags=re.IGNORECASE).strip()
            title = title[:60]

        print(f"  [Executor] Generating content for: '{title}' ({file_type})")

        # Ask LLM to generate the actual content
        content_prompt = (
            f"Write detailed, well-structured content for a {file_type.upper()} document titled: '{title}'. "
            f"Include headings, dates, places, and important facts. "
            f"Format with ## headings and proper paragraphs. "
            f"Write at least 400 words."
        )
        content = _invoke_llm(content_prompt, "file_creation", memory_ctx, recent, user_name)

        # For PPTX, convert content into slides
        if file_type == "pptx":
            slides = []
            current_title = ""
            current_bullets = []
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("## "):
                    if current_title:
                        slides.append({"title": current_title, "content": "\n".join(current_bullets)})
                    current_title = line[3:]
                    current_bullets = []
                elif line:
                    current_bullets.append(line)
            if current_title:
                slides.append({"title": current_title, "content": "\n".join(current_bullets)})
            if not slides:
                slides = [{"title": title, "content": content}]
            path = create_file_tool("pptx", title, slides)
        else:
            path = create_file_tool(file_type, title, content)

        return f"✅ File created successfully!\nLocation: {path}"
    except Exception as e:
        return f"File creation error: {e}"


def _handle_code(user_input: str, memory_ctx: str, recent: list, user_name: str) -> str:
    """Run code block if present, else ask LLM to write/explain code."""
    try:
        from jarvis.tools.code_executor.executor import code_executor_tool
        code_match = re.search(r"```(?:python|py)?\s*\n(.*?)```", user_input, re.DOTALL)
        if code_match:
            code = code_match.group(1).strip()
            print(f"  [Executor] Running Python code...")
            return code_executor_tool(code, "python")
    except Exception as e:
        return f"Code exec error: {e}"
    # No code block — ask LLM
    return _invoke_llm(user_input, "coding", memory_ctx, recent, user_name)


def _handle_self_edit(user_input: str) -> str:
    try:
        from jarvis.self_edit.self_editor import get_self_editor
        editor = get_self_editor()
        text_lower = user_input.lower()
        if "list" in text_lower and ("module" in text_lower or "file" in text_lower):
            return "JARVIS modules:\n" + "\n".join(editor.list_modules())
        mod_match = re.search(r"(jarvis/[\w/]+\.py)", user_input)
        if mod_match:
            return f"```python\n{editor.read_module(mod_match.group(1))[:2000]}\n```"
        return _invoke_llm(user_input, "self_edit", "", [], "Sir")
    except Exception as e:
        return f"Self-edit error: {e}"


def _handle_github(user_input: str) -> str:
    try:
        from jarvis.tools.github_tool.github_tool import github_tool
        text_lower = user_input.lower()
        if "trending" in text_lower:
            lang_match = re.search(r"trending\s+(\w+)", text_lower)
            lang = lang_match.group(1) if lang_match else ""
            return github_tool("trending", language=lang)
        query = re.sub(r"(search|find|github|repo|repository)\s*", "", text_lower).strip()
        return github_tool("search", query=query)
    except Exception as e:
        return f"GitHub error: {e}"


# ── Main executor node ─────────────────────────────────────────

def executor(state: JARVISState) -> JARVISState:
    memory     = get_memory()
    user_input = state.get("raw_input", "")
    task_type  = state.get("task_type", "chat")
    memory_ctx = memory.get_context(user_input)
    recent     = memory.get_recent_messages(6)
    user_name  = memory.user_name

    start  = time.time()
    answer = None

    try:
        if task_type == "web_search":
            answer = _handle_web_search(user_input)

        elif task_type == "file_creation":
            answer = _handle_file_creation(user_input, memory_ctx, recent, user_name)

        elif task_type == "coding":
            answer = _handle_code(user_input, memory_ctx, recent, user_name)

        elif task_type == "self_edit":
            answer = _handle_self_edit(user_input)

        elif task_type == "github":
            answer = _handle_github(user_input)

        else:
            # chat / assistant / memory_query
            answer = _invoke_llm(user_input, task_type, memory_ctx, recent, user_name)

        duration_ms = int((time.time() - start) * 1000)
        print(f"  [Executor] Done in {duration_ms}ms")

        state["final_response"] = answer or "No response."
        state["llm_response"]   = answer or ""
        state["error"]          = None
        memory.add_exchange(user_input, answer or "", task_type, True, duration_ms)

    except Exception as e:
        import traceback
        print(f"  [Executor] ERROR: {e}")
        print(traceback.format_exc())
        state["error"]          = str(e)
        state["final_response"] = f"Error: {str(e)}"

    return state
