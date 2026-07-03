from chhaya_v2.brain.router import TaskRouter
from chhaya_v2.core.engine.config import settings

def test_router_picks_code_model():
    router = TaskRouter()
    assert router.route("write a python script") == settings.default_code_model
    assert router.route("how do I code this?") == settings.default_code_model

def test_router_picks_chat_model():
    router = TaskRouter()
    assert router.route("hello there") == settings.default_chat_model
    assert router.route("what is the weather?") == settings.default_chat_model
