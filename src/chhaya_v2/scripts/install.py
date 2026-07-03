import sys
import os
import subprocess

def main():
    print("Starting JARVIS V3 One-Click Setup...")

    # Check Python version
    if sys.version_info < (3, 11):
        print("Error: Python 3.11+ is required.")
        sys.exit(1)

    print("Python version OK.")

    # Create Data Directories
    dirs = [
        "data/vector_db",
        "data/logs"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"Created directory: {d}")

    # Generate .env if missing
    if not os.path.exists(".env"):
        print("Generating default .env file...")
        with open(".env", "w") as f:
            f.write("ENVIRONMENT=development\n")
            f.write("DEFAULT_CHAT_MODEL=phi3.5\n")

    print("Checking dependencies...")
    try:
        import structlog
        import pydantic_settings
        print("Dependencies OK.")
    except ImportError:
        print("Dependencies missing. Please run `pip install -e .` or `uv sync`.")
        sys.exit(1)

    print("Installation Complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
