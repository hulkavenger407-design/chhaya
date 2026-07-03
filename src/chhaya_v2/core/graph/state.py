from typing import Annotated, TypedDict
import operator
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: str
    content: str

def append_messages(existing: list[Message], new: list[Message] | Message) -> list[Message]:
    if isinstance(new, Message):
        return existing + [new]
    return existing + new

class JarvisState(TypedDict):
    messages: Annotated[list[Message], append_messages]
    task_type: str | None
    selected_model: str | None
    memory_context: str | None
