"""
jarvis/tools/code_executor/executor.py

Safely executes Python code and shell commands.
- Python: runs in a subprocess with timeout + output capture
- Shell: runs cmd.exe or bash commands
- Security: Level 1 (safe) by default — dangerous ops need confirmation
"""

import os
import sys
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Tuple

# Dangerous patterns that trigger Level 2/3 security checks
DANGEROUS_PATTERNS = [
    "os.remove", "shutil.rmtree", "os.rmdir", "format c:",
    "del /f", "rm -rf", "subprocess.run", "subprocess.Popen",
    "eval(", "exec(", "__import__", "open(",
]

SYSTEM_PATTERNS = [
    "regedit", "reg delete", "format", "diskpart",
    "net user", "netsh", "sc delete", "bcdedit",
]


def _classify_risk(code: str) -> int:
    """
    Returns:
      0 = safe (read-only, print, math)
      1 = moderate (file read/write in user folders)
      2 = high (system modification)
    """
    code_lower = code.lower()
    for pattern in SYSTEM_PATTERNS:
        if pattern in code_lower:
            return 2
    for pattern in DANGEROUS_PATTERNS:
        if pattern in code_lower:
            return 1
    return 0


def execute_python(code: str, timeout: int = 30, confirm_fn=None) -> Tuple[str, str, int]:
    """
    Execute Python code safely.
    Returns (stdout, stderr, return_code).
    confirm_fn: optional callable(risk_level, code) -> bool for security checks
    """
    risk = _classify_risk(code)

    if risk >= 1 and confirm_fn:
        if not confirm_fn(risk, code):
            return ("", "Execution blocked by user.", 1)
    elif risk >= 2:
        return ("", "BLOCKED: System-level operation requires explicit confirmation.", 1)

    # Write to temp file and run
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True,
            timeout=timeout,
            cwd=str(Path.home())
        )
        return (result.stdout, result.stderr, result.returncode)
    except subprocess.TimeoutExpired:
        return ("", f"Timeout: Code took longer than {timeout}s", 1)
    except Exception as e:
        return ("", str(e), 1)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def execute_shell(command: str, timeout: int = 30, confirm_fn=None) -> Tuple[str, str, int]:
    """
    Execute a shell command.
    On Windows uses cmd.exe, on Linux uses bash.
    """
    risk = _classify_risk(command)

    if risk >= 2 and confirm_fn:
        if not confirm_fn(risk, command):
            return ("", "Blocked by user.", 1)
    elif risk >= 2:
        return ("", "BLOCKED: System-level command requires explicit confirmation.", 1)

    shell = True
    try:
        result = subprocess.run(
            command, shell=shell,
            capture_output=True, text=True,
            timeout=timeout
        )
        return (result.stdout, result.stderr, result.returncode)
    except subprocess.TimeoutExpired:
        return ("", f"Timeout after {timeout}s", 1)
    except Exception as e:
        return ("", str(e), 1)


def format_output(stdout: str, stderr: str, returncode: int) -> str:
    """Format execution output for JARVIS response."""
    parts = []
    if stdout.strip():
        parts.append(f"Output:\n{stdout.strip()}")
    if stderr.strip():
        parts.append(f"Errors:\n{stderr.strip()}")
    if returncode != 0:
        parts.append(f"Exit code: {returncode}")
    if not parts:
        return "Code executed successfully (no output)."
    return "\n\n".join(parts)


def code_executor_tool(code: str, language: str = "python", confirm_fn=None) -> str:
    """
    LangChain-compatible tool entry point.
    language: "python" | "shell" | "bash" | "cmd"
    """
    if language in ("python", "py"):
        stdout, stderr, rc = execute_python(code, confirm_fn=confirm_fn)
    elif language in ("shell", "bash", "cmd", "powershell"):
        stdout, stderr, rc = execute_shell(code, confirm_fn=confirm_fn)
    else:
        return f"Unsupported language: {language}"
    return format_output(stdout, stderr, rc)
