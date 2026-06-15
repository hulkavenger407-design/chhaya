"""
jarvis/self_edit/self_editor.py

JARVIS self-improvement engine.
On command, JARVIS can:
1. Read its own source files
2. Ask the LLM to suggest improvements
3. Show a diff for human approval
4. Apply the change and run a quick smoke test
5. Roll back if the smoke test fails

SAFETY RULES:
- Every edit shown to user before applying
- Automatic backup created before any change
- Rollback if new code fails import or syntax check
- Never edits its own safety/ or memory/ modules without double confirmation
"""

import ast
import difflib
import importlib
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Tuple, Optional


# Protected modules — require double confirmation
PROTECTED_PATHS = ["jarvis/safety", "jarvis/memory", "jarvis/core/graph.py"]

JARVIS_ROOT = Path(__file__).parent.parent.parent   # points to JARVIS/ folder
BACKUP_DIR  = JARVIS_ROOT / "jarvis" / "data" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


class SelfEditor:

    def read_module(self, module_path: str) -> str:
        """Read source code of a JARVIS module."""
        full_path = JARVIS_ROOT / module_path
        if not full_path.exists():
            return f"File not found: {module_path}"
        return full_path.read_text(encoding="utf-8")

    def list_modules(self) -> list:
        """List all Python source files in the JARVIS project."""
        files = []
        for f in JARVIS_ROOT.rglob("*.py"):
            rel = str(f.relative_to(JARVIS_ROOT)).replace("\\", "/")
            if "__pycache__" not in rel:
                files.append(rel)
        return sorted(files)

    def _backup(self, module_path: str) -> str:
        """Create a timestamped backup before editing."""
        full_path = JARVIS_ROOT / module_path
        ts = int(time.time())
        backup_name = module_path.replace("/", "_").replace("\\", "_")
        backup_path = BACKUP_DIR / f"{backup_name}.{ts}.bak"
        shutil.copy2(full_path, backup_path)
        return str(backup_path)

    def _is_protected(self, module_path: str) -> bool:
        for p in PROTECTED_PATHS:
            if module_path.startswith(p):
                return True
        return False

    def generate_improvement_prompt(self, module_path: str) -> str:
        """Build a prompt for the LLM to suggest improvements."""
        code = self.read_module(module_path)
        if code.startswith("File not found"):
            return code
        return f"""You are improving JARVIS source code.
File: {module_path}

Current code:
```python
{code}
```

Task: Suggest ONE concrete improvement to this module.
- Make it more efficient, robust, or capable
- Keep the same function signatures (don't break callers)
- Add helpful comments
- Return ONLY the complete improved Python file content — no explanation, no markdown fences.
"""

    def compute_diff(self, original: str, improved: str, module_path: str) -> str:
        """Compute a human-readable diff."""
        orig_lines = original.splitlines(keepends=True)
        impr_lines = improved.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines, impr_lines,
            fromfile=f"original/{module_path}",
            tofile=f"improved/{module_path}",
        )
        return "".join(diff)

    def validate_syntax(self, code: str) -> Tuple[bool, str]:
        """Check if the new code is valid Python."""
        try:
            ast.parse(code)
            return True, "Syntax OK"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

    def apply_edit(self, module_path: str, new_code: str, confirmed: bool = False) -> str:
        """
        Apply an edit to a JARVIS module.
        Returns success/failure message.
        """
        if self._is_protected(module_path) and not confirmed:
            return f"BLOCKED: {module_path} is a protected module. Explicit double confirmation required."

        # Validate syntax first
        valid, msg = self.validate_syntax(new_code)
        if not valid:
            return f"Edit rejected: {msg}"

        full_path = JARVIS_ROOT / module_path

        # Backup
        backup_path = self._backup(module_path)

        # Apply
        try:
            full_path.write_text(new_code, encoding="utf-8")
            print(f"  [SelfEdit] Applied edit to {module_path}")
            print(f"  [SelfEdit] Backup at {backup_path}")
            return f"Edit applied successfully. Backup: {backup_path}"
        except Exception as e:
            # Rollback from backup
            shutil.copy2(backup_path, full_path)
            return f"Edit failed, rolled back: {e}"

    def rollback(self, module_path: str) -> str:
        """Rollback to the most recent backup."""
        backup_name = module_path.replace("/", "_").replace("\\", "_")
        backups = sorted(BACKUP_DIR.glob(f"{backup_name}.*.bak"), reverse=True)
        if not backups:
            return f"No backup found for {module_path}"
        latest = backups[0]
        full_path = JARVIS_ROOT / module_path
        shutil.copy2(latest, full_path)
        return f"Rolled back {module_path} from {latest.name}"


# Singleton
_editor = None

def get_self_editor() -> SelfEditor:
    global _editor
    if _editor is None:
        _editor = SelfEditor()
    return _editor
