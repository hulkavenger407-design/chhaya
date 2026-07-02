"""
Agent Registry for Chhaya.
Provides a domain-specific wrapper around the StorageProvider for AgentBlueprints.
"""

from typing import List, Optional
import structlog

from chhaya.domain.models import AgentBlueprint
from chhaya.interfaces.storage_provider import StorageProvider

logger = structlog.get_logger(__name__)


class AgentRegistry:
    """
    Manages the persistence and retrieval of AgentBlueprint objects.
    Maintains versions so previous blueprints are never silently overwritten.
    """

    COLLECTION_NAME = "agent_blueprints"

    def __init__(self, storage_provider: StorageProvider):
        """
        Initializes the AgentRegistry.

        Args:
            storage_provider: The underlying persistence mechanism.
        """
        self.storage = storage_provider

    def save_blueprint(self, blueprint: AgentBlueprint) -> None:
        """
        Saves an AgentBlueprint in the registry.
        Uses a composite key of {name}_v{version} to ensure diffable version history.
        Also updates the 'latest' pointer for easy retrieval.
        """
        data = blueprint.model_dump(mode="json")

        versioned_key = f"{blueprint.name}_v{blueprint.version}"
        self.storage.save(self.COLLECTION_NAME, versioned_key, data)

        # Update the pointer to the latest version
        self.storage.save(self.COLLECTION_NAME, blueprint.name, data)

        logger.info("Saved agent blueprint", agent_name=blueprint.name, version=blueprint.version, key=versioned_key)

    def load_blueprint(self, name: str, version: Optional[int] = None) -> Optional[AgentBlueprint]:
        """
        Retrieves an AgentBlueprint by name. If version is provided, fetches that specific version.
        Otherwise fetches the latest.
        """
        key = f"{name}_v{version}" if version else name
        data = self.storage.load(self.COLLECTION_NAME, key)

        if data:
            try:
                return AgentBlueprint(**data)
            except Exception as e:
                logger.error("Failed to parse AgentBlueprint from storage", key=key, error=str(e))
                return None

        return None

    def list_blueprints(self) -> List[AgentBlueprint]:
        """
        Retrieves all latest AgentBlueprints from the registry.
        """
        data_list = self.storage.list(self.COLLECTION_NAME)
        latest_versions = {}

        for data in data_list:
            try:
                bp = AgentBlueprint(**data)
                # Keep only the highest version per agent name
                if bp.name not in latest_versions or bp.version > latest_versions[bp.name].version:
                    latest_versions[bp.name] = bp
            except Exception:
                pass

        return list(latest_versions.values())
