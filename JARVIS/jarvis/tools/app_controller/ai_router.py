"""
jarvis/tools/app_controller/ai_router.py

Controls Claude Desktop App, ChatGPT Desktop App, and browser-based
DeepSeek / Gemini / Grok — all through UI automation (no API keys).

AI Priority sequence:
  coding / self_edit  → Claude → ChatGPT → DeepSeek → Gemini → Grok
  general / chat      → ChatGPT → DeepSeek → Gemini → Claude → Grok
  reasoning           → DeepSeek → ChatGPT → Claude

Limit detection: watches for common "limit reached" phrases and
auto-rotates to the next AI.
"""

import time
import re
import subprocess
import pyautogui
import pygetwindow as gw
from enum import Enum
from typing import Optional


class AI(Enum):
    CLAUDE    = "claude"
    CHATGPT   = "chatgpt"
    DEEPSEEK  = "deepseek"
    GEMINI    = "gemini"
    GROK      = "grok"


# App window title keywords (partial match)
APP_TITLES = {
    AI.CLAUDE:  "Claude",
    AI.CHATGPT: "ChatGPT",
}

# Browser URLs for web-based AIs
WEB_URLS = {
    AI.DEEPSEEK: "https://chat.deepseek.com",
    AI.GEMINI:   "https://gemini.google.com",
    AI.GROK:     "https://grok.com",
}

# Desktop app exe paths (Windows)
APP_EXES = {
    AI.CLAUDE:  r"C:\Users\{user}\AppData\Local\AnthropicClaude\claude.exe",
    AI.CHATGPT: r"C:\Users\{user}\AppData\Local\Programs\ChatGPT\ChatGPT.exe",
}

# Phrases that indicate a rate limit or usage cap
LIMIT_PHRASES = [
    "you've reached your limit",
    "rate limit",
    "too many requests",
    "usage limit",
    "message limit",
    "try again in",
    "you've hit the",
    "quota exceeded",
    "upgrade your plan",
    "you can't send",
    "please wait",
    "slow down",
    "pro plan",
]

# Task → AI priority sequence
TASK_ROUTING = {
    "coding":        [AI.CLAUDE, AI.CHATGPT, AI.DEEPSEEK, AI.GEMINI, AI.GROK],
    "self_edit":     [AI.CLAUDE, AI.CHATGPT, AI.DEEPSEEK, AI.GEMINI, AI.GROK],
    "file_creation": [AI.CLAUDE, AI.CHATGPT, AI.DEEPSEEK, AI.GEMINI, AI.GROK],
    "web_search":    [AI.CHATGPT, AI.DEEPSEEK, AI.GEMINI, AI.CLAUDE, AI.GROK],
    "reasoning":     [AI.DEEPSEEK, AI.CHATGPT, AI.CLAUDE, AI.GEMINI, AI.GROK],
    "chat":          [AI.CHATGPT, AI.DEEPSEEK, AI.GEMINI, AI.CLAUDE, AI.GROK],
    "assistant":     [AI.CHATGPT, AI.CLAUDE, AI.DEEPSEEK, AI.GEMINI, AI.GROK],
    "memory_query":  [AI.CHATGPT, AI.CLAUDE, AI.DEEPSEEK, AI.GEMINI, AI.GROK],
}

DEFAULT_SEQUENCE = [AI.CLAUDE, AI.CHATGPT, AI.DEEPSEEK, AI.GEMINI, AI.GROK]

# Track which AIs are currently in cooldown (limit reached)
_cooldown: dict[AI, float] = {}
COOLDOWN_SECONDS = 3600   # 1 hour cooldown after hitting limit


class AIRouter:
    """Routes tasks to the best available AI app/web."""

    def __init__(self):
        self.current_ai: Optional[AI] = None
        self.browser = None

    def _get_browser(self):
        if self.browser is None:
            from jarvis.tools.app_controller.browser_controller import get_browser
            self.browser = get_browser()
        return self.browser

    def _is_in_cooldown(self, ai: AI) -> bool:
        if ai in _cooldown:
            if time.time() - _cooldown[ai] < COOLDOWN_SECONDS:
                return True
            else:
                del _cooldown[ai]   # cooldown expired
        return False

    def _mark_limit(self, ai: AI):
        print(f"  [AIRouter] {ai.value} limit detected — cooling down for 1 hour.")
        _cooldown[ai] = time.time()

    def _open_desktop_app(self, ai: AI) -> bool:
        """Try to open Claude or ChatGPT desktop app."""
        import os
        username = os.getenv("USERNAME", "User")
        exe_template = APP_EXES.get(ai)
        if not exe_template:
            return False
        exe = exe_template.format(user=username)
        title_keyword = APP_TITLES.get(ai, "")

        # Already open?
        windows = gw.getWindowsWithTitle(title_keyword)
        if windows:
            windows[0].activate()
            time.sleep(0.5)
            return True

        # Try to launch
        try:
            subprocess.Popen([exe])
            time.sleep(4)
            windows = gw.getWindowsWithTitle(title_keyword)
            if windows:
                windows[0].activate()
                return True
        except Exception:
            pass
        return False

    def _open_web_ai(self, ai: AI) -> bool:
        """Open a browser-based AI."""
        url = WEB_URLS.get(ai)
        if not url:
            return False
        browser = self._get_browser()
        browser.navigate(url)
        time.sleep(3)
        return True

    def _focus_ai(self, ai: AI) -> bool:
        """Bring the AI to focus. Returns True if successful."""
        if ai in APP_TITLES:
            return self._open_desktop_app(ai)
        elif ai in WEB_URLS:
            return self._open_web_ai(ai)
        return False

    def _find_chat_input(self) -> bool:
        """
        Click the chat input box.
        Strategy: try known coordinates first, then click near bottom center.
        """
        screen_w, screen_h = pyautogui.size()
        # Most chat UIs have input near bottom center
        candidates = [
            (screen_w // 2, int(screen_h * 0.88)),
            (screen_w // 2, int(screen_h * 0.92)),
            (screen_w // 2, int(screen_h * 0.85)),
        ]
        for x, y in candidates:
            pyautogui.click(x, y)
            time.sleep(0.3)
        return True

    def _send_message(self, message: str):
        """Type and send a message in the active AI chat."""
        self._find_chat_input()
        time.sleep(0.2)
        # Clear any existing text
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        # Type the message
        pyautogui.typewrite(message[:200], interval=0.02)   # typewrite limit
        if len(message) > 200:
            # For longer text, use clipboard
            import pyperclip
            pyperclip.copy(message)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.hotkey("ctrl", "v")
        pyautogui.press("enter")

    def _detect_limit_in_screenshot(self) -> bool:
        """Take a screenshot and check for limit phrases."""
        try:
            import pytesseract
            from PIL import Image
            screenshot = pyautogui.screenshot()
            text = pytesseract.image_to_string(screenshot).lower()
            for phrase in LIMIT_PHRASES:
                if phrase.lower() in text:
                    return True
        except Exception:
            pass
        return False

    def ask(self, task_type: str, message: str, context: str = "") -> str:
        """
        Route a message to the best available AI.
        Returns the AI name used (caller can show this to user).
        """
        sequence = TASK_ROUTING.get(task_type, DEFAULT_SEQUENCE)
        full_message = f"{context}\n\n{message}" if context else message

        for ai in sequence:
            if self._is_in_cooldown(ai):
                print(f"  [AIRouter] {ai.value} in cooldown — skipping.")
                continue

            print(f"  [AIRouter] Trying {ai.value} for task: {task_type}")
            success = self._focus_ai(ai)

            if not success:
                print(f"  [AIRouter] Could not open {ai.value} — skipping.")
                continue

            self.current_ai = ai
            self._send_message(full_message)
            time.sleep(2)

            # Quick limit check
            if self._detect_limit_in_screenshot():
                self._mark_limit(ai)
                continue

            return ai.value

        return "offline"  # All AIs failed — caller should use Ollama


# Singleton
_router = None

def get_ai_router() -> AIRouter:
    global _router
    if _router is None:
        _router = AIRouter()
    return _router
