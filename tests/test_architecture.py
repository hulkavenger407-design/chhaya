"""
Basic architecture tests for Chhaya.
Verifies that the core interfaces are structurally sound and importable.
"""

def test_interfaces_importable():
    from chhaya_v1.interfaces.event_bus import EventBus
    from chhaya_v1.interfaces.llm_provider import LLMProvider
    from chhaya_v1.interfaces.storage_provider import StorageProvider
    from chhaya_v1.interfaces.tool_plugin import ToolPlugin
    from chhaya_v1.interfaces.workspace import Workspace

    # Ensure ABCs cannot be instantiated directly without implementation
    try:
        EventBus()
        assert False, "EventBus should be abstract"
    except TypeError:
        pass

    try:
        LLMProvider()
        assert False, "LLMProvider should be abstract"
    except TypeError:
        pass

    try:
        StorageProvider()
        assert False, "StorageProvider should be abstract"
    except TypeError:
        pass

    try:
        ToolPlugin()
        assert False, "ToolPlugin should be abstract"
    except TypeError:
        pass

    try:
        Workspace()
        assert False, "Workspace should be abstract"
    except TypeError:
        pass
