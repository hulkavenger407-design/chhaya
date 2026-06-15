"""
jarvis/safety/guard.py

3-level security system for JARVIS.

Level 1 — AI Apps only (default, auto-allowed)
  Opening Claude/ChatGPT, web search, file creation, code execution (sandbox)

Level 2 — File system access (requires single confirmation)
  Reading/writing files outside JARVIS folder, running scripts, git operations

Level 3 — System-level operations (requires explicit double confirmation)
  Registry edits, system settings, installing software, format/delete system files
"""

from enum import IntEnum
from typing import Optional, Callable


class SecurityLevel(IntEnum):
    L1_AI_APPS = 1       # auto-allowed
    L2_FILES   = 2       # single confirmation
    L3_SYSTEM  = 3       # double confirmation


# Classify operations by security level
L2_KEYWORDS = [
    "delete file", "remove file", "write to", "overwrite",
    "git push", "git commit", "move file", "rename file",
    "save to", "create file in",
]

L3_KEYWORDS = [
    "registry", "regedit", "format", "diskpart", "system32",
    "uninstall", "install software", "net user", "bcdedit",
    "startup", "services", "firewall", "hosts file",
]


def classify_operation(description: str) -> SecurityLevel:
    desc_lower = description.lower()
    for kw in L3_KEYWORDS:
        if kw in desc_lower:
            return SecurityLevel.L3_SYSTEM
    for kw in L2_KEYWORDS:
        if kw in desc_lower:
            return SecurityLevel.L2_FILES
    return SecurityLevel.L1_AI_APPS


def console_confirm(level: SecurityLevel, description: str) -> bool:
    """
    Terminal-based confirmation for dangerous operations.
    In future this will be replaced by a voice/GUI confirmation.
    """
    if level == SecurityLevel.L1_AI_APPS:
        return True

    if level == SecurityLevel.L2_FILES:
        print(f"\n  ⚠️  JARVIS wants to: {description}")
        reply = input("  Confirm? (yes/no): ").strip().lower()
        return reply in ("yes", "y")

    if level == SecurityLevel.L3_SYSTEM:
        print(f"\n  🚨 HIGH RISK: JARVIS wants to: {description}")
        print("  This is a SYSTEM-LEVEL operation.")
        reply1 = input("  First confirmation (yes/no): ").strip().lower()
        if reply1 not in ("yes", "y"):
            return False
        reply2 = input("  Second confirmation — type 'CONFIRM': ").strip()
        return reply2 == "CONFIRM"

    return False


class SecurityGuard:
    """
    Central security check for all JARVIS operations.
    call guard.check(description, operation_fn) to run an operation safely.
    """

    def __init__(self, confirm_fn: Callable = console_confirm):
        self.confirm_fn = confirm_fn

    def check(self, description: str, operation_fn: Callable, *args, **kwargs):
        """
        Check security level for an operation.
        If cleared, execute operation_fn and return its result.
        """
        level = classify_operation(description)
        if self.confirm_fn(level, description):
            return operation_fn(*args, **kwargs)
        return f"Operation blocked: '{description}' — not confirmed."

    def auto_check(self, description: str) -> bool:
        """Just return True/False without executing — for pre-flight checks."""
        level = classify_operation(description)
        return self.confirm_fn(level, description)


# Singleton
_guard = None

def get_guard() -> SecurityGuard:
    global _guard
    if _guard is None:
        _guard = SecurityGuard()
    return _guard
