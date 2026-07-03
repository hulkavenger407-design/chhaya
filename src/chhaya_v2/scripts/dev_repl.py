import asyncio
from chhaya_v2.core.graph.jarvis_graph import jarvis_app
from chhaya_v2.core.graph.state import Message

async def main():
    print("JARVIS V3 Dev REPL (Type 'exit' to quit)")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        initial_state = {
            "messages": [Message(role="user", content=user_input)]
        }

        result = await jarvis_app.ainvoke(initial_state)

        # Print only the assistant's response
        messages = result.get("messages", [])
        if messages:
            print(f"JARVIS: {messages[-1].content}")

if __name__ == "__main__":
    asyncio.run(main())
