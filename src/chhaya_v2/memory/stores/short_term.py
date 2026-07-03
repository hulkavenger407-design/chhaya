from collections import deque
from chhaya_v2.core.graph.state import Message

class ShortTermMemory:
    """Ring buffer for short-term memory."""
    def __init__(self, max_size: int = 10):
        self.buffer = deque(maxlen=max_size)

    def add(self, message: Message):
        self.buffer.append(message)

    def get_all(self) -> list[Message]:
        return list(self.buffer)

    def clear(self):
        self.buffer.clear()
