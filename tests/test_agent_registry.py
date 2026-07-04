"""
Tests for Chhaya Agent Registry.
"""

from typing import Any, Optional
import pytest

from chhaya.core.agent_registry import AgentRegistry
from chhaya.domain.models import AgentBlueprint
from chhaya.interfaces.storage_provider import StorageProvider


class MockStorageProvider(StorageProvider):
    def __init__(self):
        self.store = {}

    def save(self, collection: str, key: str, data: dict[str, Any]) -> None:
        if collection not in self.store:
            self.store[collection] = {}
        self.store[collection][key] = data

    def load(self, collection: str, key: str) -> Optional[dict[str, Any]]:
        return self.store.get(collection, {}).get(key)

    def list(self, collection: str) -> list[dict[str, Any]]:
        return list(self.store.get(collection, {}).values())


@pytest.fixture
def agent_registry():
    storage = MockStorageProvider()
    return AgentRegistry(storage_provider=storage)


def test_agent_registry_save_and_load(agent_registry):
    blueprint = AgentBlueprint(
        name="writer_agent",
        role="Writes poetry",
        system_prompt="You are a poet."
    )

    # Save
    agent_registry.save_blueprint(blueprint)

    # Load latest
    loaded = agent_registry.load_blueprint("writer_agent")

    assert loaded is not None
    assert loaded.name == "writer_agent"
    assert loaded.role == "Writes poetry"
    assert loaded.model_tier == blueprint.model_tier

    # Load specific version
    loaded_v1 = agent_registry.load_blueprint("writer_agent", version=1)
    assert loaded_v1 is not None
    assert loaded_v1.name == "writer_agent"

    # Save a v2
    blueprint_v2 = AgentBlueprint(
        name="writer_agent",
        role="Writes poetry",
        system_prompt="You are a better poet.",
        version=2
    )
    agent_registry.save_blueprint(blueprint_v2)

    loaded_latest = agent_registry.load_blueprint("writer_agent")
    assert loaded_latest.version == 2

    loaded_old = agent_registry.load_blueprint("writer_agent", version=1)
    assert loaded_old.version == 1

def test_agent_registry_load_not_found(agent_registry):
    loaded = agent_registry.load_blueprint("non_existent")
    assert loaded is None


def test_agent_registry_load_invalid_data(agent_registry):
    # Manually insert bad data into the storage provider
    agent_registry.storage.save(
        AgentRegistry.COLLECTION_NAME,
        "bad_agent",
        {"name": "missing_required_fields"}
    )

    loaded = agent_registry.load_blueprint("bad_agent")
    assert loaded is None
