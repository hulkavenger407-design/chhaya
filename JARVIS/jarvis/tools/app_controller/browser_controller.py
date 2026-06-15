"""
jarvis/tools/app_controller/browser_controller.py

Controls Microsoft Edge browser using pyautogui + pygetwindow.
Opens URLs, clicks, types, scrolls, takes screenshots.
No Selenium needed — pure UI automation, works with any site.
"""

import time
import subprocess
import pyautogui
import pygetwindow as gw
from pathlib import Path

# Safety margin so mouse can't fly into a corner and lock up
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.4   # 400ms between actions — feels natural


class BrowserController:
    """Controls Microsoft Edge (primary browser)."""

    BROWSER_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    WINDOW_TITLE_KEYWORD = "Edge"

    def __init__(self):
        self._window = None

    # ── Window management ──────────────────────────────────────

    def _find_window(self) -> bool:
        """Find an open Edge window."""
        windows = gw.getWindowsWithTitle(self.WINDOW_TITLE_KEYWORD)
        if windows:
            self._window = windows[0]
            return True
        return False

    def open_browser(self, url: str = "about:newtab") -> bool:
        """Open Edge. If already open, bring it to front and navigate."""
        if self._find_window():
            self._window.activate()
            time.sleep(0.5)
            self.navigate(url)
            return True
        try:
            subprocess.Popen([self.BROWSER_EXE, url])
            time.sleep(3)
            return self._find_window()
        except FileNotFoundError:
            # Try generic command
            subprocess.Popen(["start", "msedge", url], shell=True)
            time.sleep(3)
            return self._find_window()

    def navigate(self, url: str):
        """Type a URL into the address bar and go."""
        if not self._find_window():
            self.open_browser(url)
            return
        self._window.activate()
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "l")          # focus address bar
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "a")          # select all
        pyautogui.typewrite(url, interval=0.03)
        pyautogui.press("enter")
        time.sleep(2)

    def new_tab(self, url: str = "about:newtab"):
        """Open a new tab."""
        if not self._find_window():
            self.open_browser(url)
            return
        self._window.activate()
        pyautogui.hotkey("ctrl", "t")
        time.sleep(0.5)
        if url != "about:newtab":
            self.navigate(url)

    def close_tab(self):
        """Close the current tab."""
        if self._find_window():
            self._window.activate()
            pyautogui.hotkey("ctrl", "w")

    # ── Interaction ────────────────────────────────────────────

    def click(self, x: int, y: int):
        pyautogui.click(x, y)

    def type_text(self, text: str):
        pyautogui.typewrite(text, interval=0.04)

    def press_enter(self):
        pyautogui.press("enter")

    def scroll(self, direction: str = "down", amount: int = 3):
        clicks = amount if direction == "down" else -amount
        pyautogui.scroll(clicks)

    def search_on_page(self, query: str):
        """Use Ctrl+F to find text on current page."""
        if self._find_window():
            self._window.activate()
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.3)
            pyautogui.typewrite(query, interval=0.04)

    def screenshot(self, save_path: str = None) -> str:
        """Take a screenshot. Returns path to saved file."""
        if save_path is None:
            save_path = str(Path.home() / "JARVIS_screenshot.png")
        img = pyautogui.screenshot()
        img.save(save_path)
        return save_path

    def download_file(self, url: str, filename: str = None):
        """Navigate to a direct download URL — Edge handles the rest."""
        self.navigate(url)
        time.sleep(2)   # wait for download dialog


# Singleton
_browser = None

def get_browser() -> BrowserController:
    global _browser
    if _browser is None:
        _browser = BrowserController()
    return _browser
