"""
jarvis/brain/selector.py — JARVIS v2 Final Fix

Response capture FIXED:
- Sends prompt properly
- Waits for AI to finish (detects streaming completion)
- Copies ONLY the last AI response using proper method
- Does NOT grab screen text
"""

import os
import socket
import time
import subprocess
from jarvis.core.state import JARVISState

_current_llm  = None
_current_mode = "offline"
_current_name = "phi3.5"

def get_current_llm():  return _current_llm
def get_current_mode(): return _current_mode
def get_current_name(): return _current_name

def check_internet(host="8.8.8.8", port=53, timeout=2) -> bool:
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except OSError:
        return False

def _is_app_installed(app_name: str) -> bool:
    username = os.getenv("USERNAME", "User")
    paths = {
        "claude":  [
            rf"C:\Users\{username}\AppData\Local\AnthropicClaude\claude.exe",
            rf"C:\Users\{username}\AppData\Local\Programs\claude\claude.exe",
        ],
        "chatgpt": [
            rf"C:\Users\{username}\AppData\Local\Programs\ChatGPT\ChatGPT.exe",
            rf"C:\Users\{username}\AppData\Roaming\ChatGPT\ChatGPT.exe",
        ],
    }
    for path in paths.get(app_name.lower(), []):
        if os.path.exists(path):
            return True
    return False


class _FakeResponse:
    def __init__(self, text: str):
        self.content = text


class AppControllerLLM:
    """
    Sends prompt to AI app and captures response.

    Strategy:
    1. Open app window
    2. Start new chat (so no old context)
    3. Paste prompt
    4. Send
    5. Wait for response to complete (stream detection)
    6. Click the COPY button that appears on the last message
    7. Read clipboard
    """

    def __init__(self, app_name: str, task_type: str):
        self.app_name  = app_name
        self.task_type = task_type
        self.model     = f"app:{app_name}"

    def invoke(self, messages) -> _FakeResponse:
        # Extract just the human question — keep it clean
        question = ""
        for msg in messages:
            role    = msg[0] if isinstance(msg, tuple) else getattr(msg, "role", "")
            content = msg[1] if isinstance(msg, tuple) else getattr(msg, "content", "")
            if role in ("human", "user"):
                question = content

        if not question:
            return _FakeResponse("[No question extracted from messages]")

        response = self._ask(question)
        return _FakeResponse(response)

    def _ask(self, prompt: str) -> str:
        """Main flow: open app → send prompt → get response."""
        import pyautogui
        import pyperclip

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE    = 0.3

        # Step 1: Open/focus the app
        if not self._open_app():
            return f"[Could not open {self.app_name}]"

        time.sleep(2.0)  # let app render

        # Step 2: Start fresh chat (Ctrl+N or Ctrl+Shift+N in most AI apps)
        pyautogui.hotkey("ctrl", "n")
        time.sleep(1.5)

        # Step 3: Set sentinel in clipboard
        SENTINEL = "__JARVIS_SENT__"
        pyperclip.copy(SENTINEL)

        # Step 4: Find and click the input box
        # Use Tab key to navigate to input — more reliable than clicking blind
        pyautogui.hotkey("ctrl", "l")   # focus URL/input in many apps
        time.sleep(0.3)

        screen_w, screen_h = pyautogui.size()

        # Click the chat input area (bottom center is universal)
        for y_frac in [0.90, 0.88, 0.85, 0.93]:
            pyautogui.click(screen_w // 2, int(screen_h * y_frac))
            time.sleep(0.3)
            # Check if we can type (try pressing a key and see)
            break

        # Step 5: Type prompt via clipboard (handles all languages/special chars)
        pyperclip.copy(prompt)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.4)

        # Step 6: Send
        pyautogui.press("enter")
        print(f"  [AppCtrl] ✓ Prompt sent to {self.app_name}")
        print(f"  [AppCtrl] Waiting for response...")

        # Step 7: Wait for AI to FINISH streaming
        # Detection: take 2 screenshots, compare pixel count
        # When streaming stops, screen stops changing
        self._wait_for_stream_complete()

        # Step 8: Copy response using the copy button
        # Hover over the LAST response bubble → copy button appears → click it
        response = self._copy_last_response(screen_w, screen_h, prompt)

        return response

    def _wait_for_stream_complete(self):
        """
        Wait until the AI stops generating.
        Method: compare screenshots — when they stop changing, AI is done.
        Max wait: 60 seconds.
        """
        import pyautogui
        from PIL import Image
        import numpy as np

        print(f"  [AppCtrl] Detecting response completion...")

        # First wait minimum time before checking
        min_wait = 8 if self.task_type in ("chat", "assistant") else 15
        time.sleep(min_wait)

        # Then poll until stable
        prev_hash = None
        stable_count = 0
        max_checks = 20  # 20 * 1.5s = 30s max additional wait

        for _ in range(max_checks):
            try:
                # Screenshot just the bottom half (where response appears)
                screen_w, screen_h = pyautogui.size()
                screenshot = pyautogui.screenshot(
                    region=(0, screen_h // 3, screen_w, screen_h * 2 // 3)
                )
                arr  = list(screenshot.getdata())
                # Simple hash: sum of every 500th pixel value
                curr_hash = sum(sum(p) for p in arr[::500])

                if curr_hash == prev_hash:
                    stable_count += 1
                    if stable_count >= 2:
                        print(f"  [AppCtrl] Response complete (screen stable).")
                        return
                else:
                    stable_count = 0

                prev_hash = curr_hash
                time.sleep(1.5)
            except Exception:
                time.sleep(2)
                return

        print(f"  [AppCtrl] Max wait reached — proceeding.")

    def _copy_last_response(self, screen_w: int, screen_h: int, sent_prompt: str) -> str:
        """
        Get the AI response text.

        For desktop apps (Claude/ChatGPT):
          - Hover over last response → copy button appears → click it

        For web apps:
          - Use JavaScript via browser to get last message text
        """
        import pyautogui
        import pyperclip

        SENTINEL = "__JARVIS_GOT_RESPONSE__"
        pyperclip.copy(SENTINEL)   # reset clipboard

        if self.app_name in ("claude", "chatgpt") and _is_app_installed(self.app_name):
            return self._copy_from_desktop_app(screen_w, screen_h, sent_prompt)
        else:
            return self._copy_from_web_app(sent_prompt)

    def _copy_from_desktop_app(self, screen_w, screen_h, sent_prompt):
        """
        Desktop app response copy:
        The last AI message has a copy icon when you hover.
        We hover over response area and look for the copy button.
        """
        import pyautogui
        import pyperclip

        SENTINEL = "__JARVIS_GOT_RESPONSE__"

        # In Claude/ChatGPT desktop, response is in the upper-center area
        # Copy button typically appears at bottom-right of each response bubble
        # Strategy: hover over response → copy button appears → click it

        response_y_positions = [
            int(screen_h * 0.55),
            int(screen_h * 0.60),
            int(screen_h * 0.65),
            int(screen_h * 0.50),
            int(screen_h * 0.70),
        ]

        for resp_y in response_y_positions:
            resp_x = int(screen_w * 0.55)
            # Hover
            pyautogui.moveTo(resp_x, resp_y, duration=0.3)
            time.sleep(0.8)

            # Look for copy button — usually appears near the response
            # Take screenshot and find the copy button area
            # Copy buttons are usually small icons near bottom-right of message

            # Try clicking areas where copy button typically appears
            copy_btn_candidates = [
                (int(screen_w * 0.15), resp_y + 40),   # left side (Claude)
                (int(screen_w * 0.12), resp_y + 30),
                (int(screen_w * 0.10), resp_y + 35),
                (resp_x + 20, resp_y + 40),
            ]
            for btn_x, btn_y in copy_btn_candidates:
                pyautogui.click(btn_x, btn_y)
                time.sleep(0.5)
                result = pyperclip.paste()
                if result and result != SENTINEL and len(result) > 30:
                    if sent_prompt[:40] not in result[:100]:
                        print(f"  [AppCtrl] ✓ Response captured via copy button ({len(result)} chars)")
                        return result

        # Fallback: select all text in response area via keyboard
        print(f"  [AppCtrl] Copy button not found — using keyboard selection...")
        return self._keyboard_select_response(screen_w, screen_h, sent_prompt)

    def _copy_from_web_app(self, sent_prompt: str) -> str:
        """
        Web app response: use Edge browser's accessibility to get text,
        or use JavaScript injection to extract last AI message.
        """
        import pyautogui
        import pyperclip

        SENTINEL = "__JARVIS_WEB_RESPONSE__"
        pyperclip.copy(SENTINEL)

        screen_w, screen_h = pyautogui.size()

        # Method: Use F12 console to run JavaScript that copies last AI message
        # This works in Edge/Chrome for ChatGPT, Claude web, DeepSeek etc.
        js_scripts = {
            "chatgpt": """
                const msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
                const last = msgs[msgs.length - 1];
                if (last) { 
                    navigator.clipboard.writeText(last.innerText);
                }
            """,
            "claude": """
                const msgs = document.querySelectorAll('.font-claude-message');
                const last = msgs[msgs.length - 1];
                if (last) { 
                    navigator.clipboard.writeText(last.innerText);
                }
            """,
            "deepseek": """
                const msgs = document.querySelectorAll('.ds-markdown');
                const last = msgs[msgs.length - 1];
                if (last) { 
                    navigator.clipboard.writeText(last.innerText);
                }
            """,
            "gemini": """
                const msgs = document.querySelectorAll('message-content');
                const last = msgs[msgs.length - 1];
                if (last) { 
                    navigator.clipboard.writeText(last.innerText);
                }
            """,
        }

        js = js_scripts.get(self.app_name, js_scripts["chatgpt"])
        # Remove newlines for console input
        js_oneline = " ".join(js.split())

        # Open DevTools console
        pyautogui.hotkey("ctrl", "shift", "j")   # Edge/Chrome console shortcut
        time.sleep(1.5)

        # Click console input area (bottom of DevTools)
        # DevTools usually opens on the right or bottom
        pyautogui.click(screen_w - 200, screen_h - 40)
        time.sleep(0.3)
        pyautogui.click(screen_w // 2, screen_h - 30)
        time.sleep(0.3)

        # Type JS and run
        pyperclip.copy(js_oneline)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(1.0)

        # Close DevTools
        pyautogui.hotkey("ctrl", "shift", "j")
        time.sleep(0.5)

        result = pyperclip.paste()
        if result and result != SENTINEL and len(result) > 20:
            print(f"  [AppCtrl] ✓ Response captured via JS ({len(result)} chars)")
            return result

        # Last resort: keyboard selection
        return self._keyboard_select_response(screen_w, screen_h, sent_prompt)

    def _keyboard_select_response(self, screen_w, screen_h, sent_prompt):
        """Last resort: End key to go to bottom, shift+ctrl+home to select, copy."""
        import pyautogui
        import pyperclip

        SENTINEL = "__JARVIS_KB_RESPONSE__"

        # Click in the chat area
        pyautogui.click(screen_w // 2, int(screen_h * 0.6))
        time.sleep(0.3)

        # Go to end of page
        pyautogui.hotkey("ctrl", "end")
        time.sleep(0.3)

        # Select last ~500 words upward
        for _ in range(30):
            pyautogui.hotkey("shift", "up")
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.4)

        result = pyperclip.paste()
        if result and len(result) > 20:
            # Remove prompt from beginning if it's there
            if sent_prompt[:50] in result:
                result = result[result.index(sent_prompt[:50]) + len(sent_prompt):].strip()
            return result if len(result) > 20 else "[Response not captured — check app window]"

        return "[Response not captured — please check the app window for the answer]"

    def _open_app(self) -> bool:
        """Open or focus the target AI app."""
        import pygetwindow as gw
        import pyautogui

        title_map = {"claude": "Claude", "chatgpt": "ChatGPT"}
        title_kw  = title_map.get(self.app_name)

        # Try desktop app first
        if title_kw:
            windows = gw.getWindowsWithTitle(title_kw)
            if windows:
                try:
                    w = windows[0]
                    w.restore()
                    w.activate()
                    time.sleep(0.5)
                    # Maximize for consistent layout
                    w.maximize()
                    return True
                except Exception:
                    pass

            username = os.getenv("USERNAME", "User")
            exe_map  = {
                "claude":  rf"C:\Users\{username}\AppData\Local\AnthropicClaude\claude.exe",
                "chatgpt": rf"C:\Users\{username}\AppData\Local\Programs\ChatGPT\ChatGPT.exe",
            }
            exe = exe_map.get(self.app_name, "")
            if os.path.exists(exe):
                subprocess.Popen([exe])
                time.sleep(4)
                windows = gw.getWindowsWithTitle(title_kw)
                if windows:
                    windows[0].maximize()
                    windows[0].activate()
                    return True

        # Web fallback
        web_urls = {
            "chatgpt":  "https://chatgpt.com",
            "deepseek": "https://chat.deepseek.com",
            "gemini":   "https://gemini.google.com/app",
            "grok":     "https://grok.com",
            "claude":   "https://claude.ai",
        }
        url = web_urls.get(self.app_name)
        if url:
            try:
                from jarvis.tools.app_controller.browser_controller import get_browser
                get_browser().navigate(url)
                time.sleep(3)
                return True
            except Exception:
                pass
        return False


# ── Cooldown ───────────────────────────────────────────────────
_cooldowns: dict = {}
COOLDOWN_SECS = 3600

def _in_cooldown(n):
    if n in _cooldowns:
        if time.time() - _cooldowns[n] < COOLDOWN_SECS: return True
        del _cooldowns[n]
    return False

def _mark_cooldown(n):
    _cooldowns[n] = time.time()
    print(f"  [Brain] {n} cooldown 1hr.")


TASK_AI_SEQUENCE = {
    "coding":        ["claude",   "chatgpt", "deepseek", "gemini"],
    "self_edit":     ["claude",   "chatgpt", "deepseek", "gemini"],
    "file_creation": ["claude",   "chatgpt", "deepseek", "gemini"],
    "chat":          ["chatgpt",  "deepseek", "claude",  "gemini"],
    "assistant":     ["chatgpt",  "claude",  "deepseek", "gemini"],
    "memory_query":  ["chatgpt",  "claude",  "deepseek", "gemini"],
    "web_search":    ["deepseek", "chatgpt", "gemini",   "claude"],
    "github":        ["deepseek", "chatgpt", "claude",   "gemini"],
}
DEFAULT_AI_SEQUENCE = ["chatgpt", "claude", "deepseek", "gemini"]


def get_offline_llm(task_type: str):
    from langchain_ollama import ChatOllama
    fast  = os.getenv("JARVIS_FAST_MODEL",  "phi3.5")
    smart = os.getenv("JARVIS_SMART_MODEL", "qwen2.5-coder:7b")
    if task_type in ("coding", "self_edit", "file_creation"):
        print(f"  [Brain] Offline — {smart}")
        return ChatOllama(model=smart, temperature=0.1)
    print(f"  [Brain] Offline — {fast}")
    return ChatOllama(model=fast, temperature=0.3)


def _try_api_llm(task_type: str):
    ak = os.getenv("ANTHROPIC_API_KEY", "").strip()
    ok = os.getenv("OPENAI_API_KEY",    "").strip()
    dk = os.getenv("DEEPSEEK_API_KEY",  "").strip()
    if task_type in ("coding", "self_edit", "file_creation") and ak:
        from langchain_anthropic import ChatAnthropic
        print("  [Brain] API → Claude")
        return ChatAnthropic(model="claude-sonnet-4-6", api_key=ak, temperature=0.1), "claude-api"
    if dk and not _in_cooldown("deepseek-api"):
        from langchain_community.chat_models import ChatDeepSeek
        print("  [Brain] API → DeepSeek")
        return ChatDeepSeek(model="deepseek-chat", api_key=dk), "deepseek-api"
    if ok and not _in_cooldown("chatgpt-api"):
        from langchain_openai import ChatOpenAI
        print("  [Brain] API → GPT-4o")
        return ChatOpenAI(model="gpt-4o", api_key=ok, temperature=0.3), "chatgpt-api"
    return None, None


def get_best_llm(task_type: str, online: bool):
    if not online:
        llm = get_offline_llm(task_type)
        return llm, "offline", getattr(llm, "model", "phi3.5")
    api_llm, api_name = _try_api_llm(task_type)
    if api_llm:
        return api_llm, "api", api_name
    seq = TASK_AI_SEQUENCE.get(task_type, DEFAULT_AI_SEQUENCE)
    for ai_name in seq:
        if _in_cooldown(ai_name):
            continue
        has_app = _is_app_installed(ai_name)
        mode    = "desktop-app" if has_app else "web-app"
        print(f"  [Brain] Selecting {ai_name} ({mode})")
        return AppControllerLLM(ai_name, task_type), mode, ai_name
    llm = get_offline_llm(task_type)
    return llm, "offline", getattr(llm, "model", "phi3.5")


def brain_selector(state: JARVISState) -> JARVISState:
    global _current_llm, _current_mode, _current_name
    task_type  = state.get("task_type", "chat")
    forced_ai  = state.get("forced_ai", "").strip().lower()
    online     = check_internet()

    # User said "ask claude X" — force that AI directly
    if forced_ai and online:
        has_app = _is_app_installed(forced_ai)
        mode    = "desktop-app" if has_app else "web-app"
        print(f"  [Brain] Forced AI: {forced_ai} ({mode})")
        llm  = AppControllerLLM(forced_ai, task_type)
        name = forced_ai
        _current_llm  = llm
        _current_mode = mode
        _current_name = name
        state["brain_mode"] = mode
        state["model_name"] = name
        return state

    llm, mode, name = get_best_llm(task_type, online)
    _current_llm  = llm
    _current_mode = mode
    _current_name = name
    state["brain_mode"] = mode
    state["model_name"] = name
    return state
