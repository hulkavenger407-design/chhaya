"""
jarvis/core/graph.py — JARVIS v2
LangGraph with github task type added.
"""

from langgraph.graph import StateGraph, END
from jarvis.core.state     import JARVISState
from jarvis.core.router    import task_router, route_decision
from jarvis.core.executor  import executor
from jarvis.brain.selector import brain_selector


def input_processor_node(state: JARVISState) -> JARVISState:
    state["raw_input"]    = state.get("raw_input", "").strip()
    state["retry_count"]  = state.get("retry_count", 0)
    state["plan"]         = state.get("plan", [])
    state["step_results"] = state.get("step_results", [])
    state["approved"]     = state.get("approved", False)
    state["error"]        = None
    print(f"\n  [Input] '{state['raw_input'][:60]}'")
    return state

def router_node(state: JARVISState) -> JARVISState:
    return task_router(state, llm=None)

def brain_selector_node(state: JARVISState) -> JARVISState:
    return brain_selector(state)

def executor_node(state: JARVISState) -> JARVISState:
    return executor(state)

def output_node(state: JARVISState) -> JARVISState:
    response = state.get("final_response", "No response.")
    model    = state.get("model_name", "unknown")
    mode     = state.get("brain_mode", "offline")
    task     = state.get("task_type", "chat")
    print(f"\n  {'─'*56}")
    print(f"  JARVIS [{mode} | {model} | {task}]")
    print(f"  {'─'*56}")
    print(f"\n  {response}\n")
    print(f"  {'─'*56}\n")
    return state


def build_jarvis_graph():
    graph = StateGraph(JARVISState)
    graph.add_node("input_processor", input_processor_node)
    graph.add_node("task_router",     router_node)
    graph.add_node("brain_selector",  brain_selector_node)
    graph.add_node("executor",        executor_node)
    graph.add_node("output",          output_node)

    graph.set_entry_point("input_processor")
    graph.add_edge("input_processor", "task_router")

    graph.add_conditional_edges(
        "task_router", route_decision,
        {
            "coding":        "brain_selector",
            "web_search":    "brain_selector",
            "file_creation": "brain_selector",
            "assistant":     "brain_selector",
            "self_edit":     "brain_selector",
            "memory_query":  "brain_selector",
            "github":        "brain_selector",
            "chat":          "brain_selector",
        }
    )

    graph.add_edge("brain_selector", "executor")
    graph.add_edge("executor",       "output")
    graph.add_edge("output",         END)
    return graph.compile()


_jarvis_graph = None

def get_jarvis_graph():
    global _jarvis_graph
    if _jarvis_graph is None:
        print("  [Graph] Building JARVIS graph...")
        _jarvis_graph = build_jarvis_graph()
        print("  [Graph] Ready.")
    return _jarvis_graph
