from chhaya_v2.core.graph.state import Message, append_messages

def test_append_messages():
    existing = [Message(role="user", content="hi")]
    new_msg = Message(role="assistant", content="hello")
    new_list = append_messages(existing, new_msg)

    assert len(new_list) == 2
    assert new_list[1].role == "assistant"

    new_msgs = [Message(role="user", content="msg 1"), Message(role="assistant", content="msg 2")]
    new_list2 = append_messages(existing, new_msgs)
    assert len(new_list2) == 3
