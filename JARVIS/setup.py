"""
setup.py — JARVIS v2 Installation Script

Run this once after cloning/extracting the project:
    python setup.py

This installs all dependencies and verifies the setup.
"""

import subprocess
import sys
import os

print("""
╔══════════════════════════════════════════════════════════╗
║           JARVIS v2 — Setup & Installation               ║
╚══════════════════════════════════════════════════════════╝
""")

# ── Core dependencies ──────────────────────────────────────────
CORE_PACKAGES = [
    "langchain",
    "langchain-core",
    "langgraph",
    "langchain-ollama",
    "langchain-anthropic",
    "langchain-openai",
    "langchain-community",
    "python-dotenv",
    "chromadb",
    "sentence-transformers",
    "requests",
    "beautifulsoup4",
    "duckduckgo-search",
]

# ── File creation dependencies ─────────────────────────────────
FILE_PACKAGES = [
    "reportlab",
    "python-pptx",
    "python-docx",
    "openpyxl",
]

# ── Voice dependencies (optional) ─────────────────────────────
VOICE_PACKAGES = [
    "faster-whisper",
    "openwakeword",
    "sounddevice",
    "soundfile",
    "pyttsx3",
    "pyperclip",
]

# ── UI automation dependencies ─────────────────────────────────
AUTOMATION_PACKAGES = [
    "pyautogui",
    "pygetwindow",
    "pillow",
]

# ── Tool packages ──────────────────────────────────────────────
TOOL_PACKAGES = [
    "pytesseract",
]

def install(packages: list, label: str):
    print(f"\n  Installing {label}...")
    for pkg in packages:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-q", pkg],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print(f"    ✓ {pkg}")
        except subprocess.CalledProcessError:
            print(f"    ✗ {pkg} — FAILED (install manually if needed)")

install(CORE_PACKAGES,       "Core (LangChain, LangGraph, Memory)")
install(FILE_PACKAGES,       "File Creator (PDF, PPTX, DOCX, XLSX)")
install(AUTOMATION_PACKAGES, "UI Automation (PyAutoGUI)")
install(TOOL_PACKAGES,       "Tools (OCR, etc.)")

voice = input("\n  Install voice pipeline? (Whisper + Wake Word) [y/N]: ").strip().lower()
if voice == "y":
    install(VOICE_PACKAGES, "Voice (Faster-Whisper, OpenWakeWord, pyttsx3)")

# ── Verify Ollama ──────────────────────────────────────────────
print("\n  Checking Ollama...")
try:
    import urllib.request
    urllib.request.urlopen("http://127.0.0.1:11435", timeout=2)
    print("  ✓ Ollama is running on port 11435")
except Exception:
    print("  ✗ Ollama not detected on port 11435")
    print("    Start Ollama with: OLLAMA_HOST=127.0.0.1:11435 ollama serve")

# ── Verify phi3.5 ──────────────────────────────────────────────
print("\n  Checking phi3.5 model...")
try:
    import subprocess
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
    if "phi3.5" in result.stdout:
        print("  ✓ phi3.5 model found")
    else:
        print("  ✗ phi3.5 not found — run: ollama pull phi3.5")
except Exception:
    print("  ✗ Could not check Ollama models")

# ── Create .env ────────────────────────────────────────────────
env_file = ".env"
env_template = ".env.txt"
if not os.path.exists(env_file) and os.path.exists(env_template):
    import shutil
    shutil.copy(env_template, env_file)
    print(f"\n  ✓ Created .env from template")
elif os.path.exists(env_file):
    print(f"\n  ✓ .env already exists")

print("""
╔══════════════════════════════════════════════════════════╗
║  Setup complete!                                         ║
║                                                          ║
║  Start JARVIS:                                           ║
║    python main.py                                        ║
║                                                          ║
║  Next steps:                                             ║
║  1. ollama pull phi3.5           (if not done)          ║
║  2. ollama pull qwen2.5-coder:7b (optional, for code)  ║
║  3. python main.py               (launch JARVIS)        ║
╚══════════════════════════════════════════════════════════╝
""")
