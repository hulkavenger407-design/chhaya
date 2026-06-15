"""
jarvis/core/state.py

The JARVISState TypedDict is the single object that flows
through every node in the LangGraph graph.
Every node reads from it and writes back to it.
"""

from typing import TypedDict, Optional


class JARVISState(TypedDict):
    # ── Input ──────────────────────────────────────────────
    raw_input:      str               # exactly what you said or typed
    input_mode:     str               # "voice" or "text"

    # ── Routing ────────────────────────────────────────────
    task_type:      str               # coding / web_search / file_creation /
                                      # assistant / self_edit / memory_query / chat

    # ── Memory ─────────────────────────────────────────────
    memory_context: str               # relevant memories retrieved for this task
    conversation_history: list        # last N messages in current session

    # ── Planning ───────────────────────────────────────────
    plan:           list              # list of step strings
    current_step:   int               # which step we are executing
    step_results:   list              # results from each completed step

    # ── Brain ──────────────────────────────────────────────
    brain_mode:     str               # "offline" or "online"
    model_name:     str               # exact model being used
    llm_response:   str               # raw LLM response

    # ── Tools ──────────────────────────────────────────────
    tool_name:      str               # which tool was called
    tool_input:     dict              # input passed to tool
    tool_output:    str               # result from tool

    # ── Self-edit ──────────────────────────────────────────
    target_module:  str               # file path to edit
    current_code:   str               # code before edit
    new_code:       str               # code after edit
    diff_display:   str               # human-readable diff
    approved:       bool              # human approved the edit?
    sandbox_passed: bool              # sandbox test passed?

    # ── Output ─────────────────────────────────────────────
    final_response: str               # what JARVIS says back to you
    output_mode:    str               # "voice", "text", or "both"

    # ── Error handling ─────────────────────────────────────
    error:          Optional[str]     # error message if something failed
    retry_count:    int               # how many times this step has been retried

# Appended — forced AI override (set by router when user says "ask claude X")
# This is read by brain_selector to skip the normal AI selection logic
JARVIS_FORCED_AI_KEY = "forced_ai"   # value: "claude" | "chatgpt" | "deepseek" | "" 
