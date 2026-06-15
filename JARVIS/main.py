"""
main.py — JARVIS v2

EMERGENCY STOP: Move mouse to TOP-LEFT corner of screen → PyAutoGUI stops instantly.
Or press Ctrl+C in this terminal window (not in any other window).
"""

import os
import sys
import signal
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

# Set PyAutoGUI failsafe ON before anything else
try:
    import pyautogui
    pyautogui.FAILSAFE = True   # move mouse to top-left corner = emergency stop
    pyautogui.PAUSE    = 0.5
except ImportError:
    pass

from jarvis.core.graph    import get_jarvis_graph
from jarvis.memory.memory import get_memory

BANNER = """
╔══════════════════════════════════════════════════════════╗
║        J A R V I S  v2 — Personal AI Assistant         ║
║                                                          ║
║  Commands:  exit | clear | memory | voice on | help     ║
║                                                          ║
║  ⚠️  EMERGENCY STOP: Move mouse to TOP-LEFT corner      ║
╚══════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
JARVIS v2 — What I can do:
  Web Search    → "search for X"  /  "find X online"
  File Create   → "make a PDF about X"  /  "create slides on X"
  Code Run      → paste code in ```python blocks```
  GitHub        → "search github for X"  /  "trending python repos"
  Self-Edit     → "list modules"  /  "show jarvis/core/router.py"
  Memory        → "what did I ask about X"
  Voice         → type "voice on"  (say JARVIS to wake)

  EMERGENCY STOP → move mouse to screen TOP-LEFT corner
"""

_running = True


def handle_sigint(sig, frame):
    """Ctrl+C handler — clean shutdown."""
    global _running
    print("\n\n  JARVIS: Ctrl+C received. Shutting down cleanly...\n")
    _running = False
    sys.exit(0)


signal.signal(signal.SIGINT, handle_sigint)


def run_command(jarvis, user_input: str):
    return jarvis.invoke({
        "raw_input":   user_input,
        "input_mode":  "text",
        "retry_count": 0,
        "approved":    False,
    })


def run():
    global _running
    print(BANNER)

    jarvis = get_jarvis_graph()
    memory = get_memory()

    print(f"  Memory: {memory.status()}")
    print("  JARVIS v2 ready.\n")

    while _running:
        try:
            user_input = input("  You → ").strip()
            if not user_input:
                continue

            # ── Built-in commands ──────────────────────────────
            if user_input.lower() in ("exit", "quit", "bye"):
                print(f"\n  JARVIS: Goodbye, {memory.user_name}.\n")
                break

            if user_input.lower() == "clear":
                memory.short.clear()
                os.system("cls" if os.name == "nt" else "clear")
                print(BANNER)
                continue

            if user_input.lower() == "memory":
                print(f"\n  {memory.status()}\n")
                continue

            if user_input.lower() == "help":
                print(HELP_TEXT)
                continue

            if user_input.lower() == "voice on":
                try:
                    from jarvis.voice.voice_pipeline import get_voice_pipeline
                    def on_voice(text):
                        print(f"\n  [Voice] Heard: '{text}'")
                        run_command(jarvis, text)
                    vp = get_voice_pipeline(on_voice)
                    vp.start()
                    print("  Voice active. Say 'JARVIS' to wake.\n")
                except Exception as e:
                    print(f"  Voice error: {e}\n")
                continue

            if user_input.lower() == "voice off":
                try:
                    from jarvis.voice.voice_pipeline import get_voice_pipeline
                    get_voice_pipeline().stop()
                    print("  Voice stopped.\n")
                except Exception as e:
                    print(f"  Voice stop error: {e}\n")
                continue

            # ── Run JARVIS ─────────────────────────────────────
            run_command(jarvis, user_input)

        except KeyboardInterrupt:
            print("\n\n  JARVIS: Stopped. Type 'exit' to quit.\n")
            # Do NOT sys.exit here — let user continue if they want
        except EOFError:
            break
        except Exception as e:
            print(f"\n  [ERROR] {str(e)}\n")


if __name__ == "__main__":
    run()
