from chhaya_v2.memory.stores.short_term import ShortTermMemory
from chhaya_v2.core.graph.state import Message

def test_short_term_memory():
    mem = ShortTermMemory(max_size=2)
    mem.add(Message(role="user", content="a"))
    mem.add(Message(role="user", content="b"))
    mem.add(Message(role="user", content="c"))

    msgs = mem.get_all()
    assert len(msgs) == 2
    assert msgs[0].content == "b"
    assert msgs[1].content == "c"
