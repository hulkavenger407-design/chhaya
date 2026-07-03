from langgraph.graph import StateGraph, START, END
from chhaya_v2.core.graph.state import JarvisState, Message
from chhaya_v2.brain.router import TaskRouter
from chhaya_v2.memory.manager import MemoryManager
from chhaya_v2.core.graph.nodes.llm import call_llm

router = TaskRouter()
memory = MemoryManager()

def route_task(state: JarvisState) -> dict:
    last_msg = state["messages"][-1].content if state["messages"] else ""
    model = router.route(last_msg)

    if last_msg:
        memory.add_message(Message(role="user", content=last_msg))

    context = memory.get_context()
    return {"selected_model": model, "memory_context": context}

def update_memory(state: JarvisState) -> dict:
    if state["messages"]:
        last_msg = state["messages"][-1]
        if last_msg.role == "assistant":
            memory.add_message(last_msg)
    return {}

graph = StateGraph(JarvisState)
graph.add_node("route", route_task)
graph.add_node("llm", call_llm)
graph.add_node("update_memory", update_memory)

graph.add_edge(START, "route")
graph.add_edge("route", "llm")
graph.add_edge("llm", "update_memory")
graph.add_edge("update_memory", END)

jarvis_app = graph.compile()
