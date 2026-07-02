"""
Storage Provider Interface for Chhaya.
Provides abstractions for persisting data like blueprints and memory.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class StorageProvider(ABC):
    """
    Abstract Base Class for data storage.
    Allows swapping out SQLite for other databases in the future.
    """

    @abstractmethod
    def save(self, collection: str, key: str, data: dict[str, Any]) -> None:
        """
        Saves data to a specified collection with a key.

        Args:
            collection (str): The name of the collection or table.
            key (str): The unique identifier for the data record.
            data (dict[str, Any]): The data to save.
        """
        pass

    @abstractmethod
    def load(self, collection: str, key: str) -> Optional[dict[str, Any]]:
        """
        Loads data from a specified collection by key.

        Args:
            collection (str): The name of the collection or table.
            key (str): The unique identifier for the data record.

        Returns:
            Optional[dict[str, Any]]: The loaded data, or None if not found.
        """
        pass

    @abstractmethod
    def list(self, collection: str) -> List[dict[str, Any]]:
        """
        Retrieves all records from a specified collection.

        Args:
            collection (str): The name of the collection.

        Returns:
            List[dict[str, Any]]: A list of all stored data records.
        """
        pass
