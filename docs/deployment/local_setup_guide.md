# Local Deployment Guide: Chhaya (JARVIS V3)

This guide will walk you through deploying Chhaya locally on your Windows machine using WSL2.

## 1. Prerequisites

Before starting, ensure you have the following installed on your system:
- **Windows + WSL2:** A working installation of Windows Subsystem for Linux (WSL2) running Ubuntu.
- **Python:** Python 3.11 or higher.
- **Git:** For version control and syncing updates.
- **uv:** Ultra-fast Python package installer (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **pnpm:** Fast, disk space efficient package manager for Node.js (`npm install -g pnpm`).
- **Ollama:** Local LLM runner. Install via [ollama.com](https://ollama.com/download).

### Optional System Packages (WSL/Ubuntu)
If you intend to run the Voice Pipeline locally or execute headless UI tests, you will need to install system dependencies within WSL:
```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio xvfb libxcb-cursor0 libxkbcommon-x11-0 libgl1-mesa-glx
```

## 2. Repository setup

Open your WSL2 terminal and follow these steps:

1. **Clone repository:**
   ```bash
   git clone https://github.com/your-username/chhaya.git
   cd chhaya
   ```

2. **Create virtual environment & Install Python packages:**
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e .[dev]
   ```

3. **Install Node packages:**
   *(For frontend Playwright components or React tools)*
   ```bash
   pnpm install
   ```

## 3. Environment configuration

1. **Copy .env.example:**
   ```bash
   cp .env.example .env
   ```

2. **Configure required variables:**
   Open `.env` in your preferred editor (`nano .env`) and configure the settings. Ensure the following are set:
   ```env
   ENVIRONMENT=development
   DEFAULT_CHAT_MODEL=phi3.5
   DEFAULT_CODE_MODEL=qwen-coder
   OLLAMA_BASE_URL=http://localhost:11434
   MASTER_KEY=your_secure_password_here
   TTS_BACKEND=melo
   ```

## 4. Running Chhaya

1. **Start Ollama:**
   Ensure Ollama is running in the background. If using the Windows client, ensure the tray icon is active. If running natively in WSL:
   ```bash
   ollama serve &
   ```
   *Note: Pull required models via `ollama pull phi3.5` and `ollama pull qwen-coder`.*

2. **Start backend:**
   Launch the core Chhaya backend intelligence and FastAPI services (if applicable):
   ```bash
   python -m chhaya_v2.scripts.install
   ```

3. **Verify health endpoints:**
   Run the pre-configured health check script to ensure the environment, vector storage directories, and configs are successfully mapped:
   ```bash
   python -m chhaya_v2.scripts.health_check
   ```
   If successful, the console will output `health_check_passed`.

4. **Start frontend:**
   Launch the JARVIS V3 PySide6 desktop UI application:
   ```bash
   python -m chhaya_v2.apps.desktop.app
   ```

## 5. Troubleshooting

- **Audio Feedback / PortAudio Errors:** If the application crashes on startup with PyAudio errors, verify you installed `portaudio19-dev` via apt before running `uv pip install`.
- **UI Fails to Load in WSL:** Ensure you have WSLg correctly installed, or you are exporting the display correctly (`export DISPLAY=:0`). If testing headlessly, use `xvfb-run -a python ...`.
- **GitHub Sync Fails:** If the internal Chhaya GitHub updater fails, ensure your local repository has no conflicting unstashed changes and that your SSH keys/Git credentials are set up within the WSL environment.
- **Ollama Connection Refused:** Verify that `OLLAMA_BASE_URL` in `.env` is set correctly. If Ollama is running natively on Windows and Chhaya is in WSL2, you may need to point `OLLAMA_BASE_URL` to `http://<YOUR_WINDOWS_IP>:11434` instead of `localhost`.
