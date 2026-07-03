"""
Memory Provider Interface for Chhaya.
Provides abstractions for long-term vector-based semantic memory.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MemoryRecord:
    """
    A unified data structure for a semantic memory.
    """
    def __init__(self, id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.text = text
        self.metadata = metadata or {}


class MemoryProvider(ABC):
    """
    Abstract Base Class for Vector Memory interaction.
    Allows swapping out ChromaDB for other vector databases (e.g., Pinecone, Qdrant, Milvus).
    """

    @abstractmethod
    def store(self, namespace: str, record: MemoryRecord) -> None:
        """
        Stores a semantic memory record into a specific namespace (e.g., agent name).

        Args:
            namespace (str): The collection/namespace to store the memory in.
            record (MemoryRecord): The memory data to store.
        """
        pass

    @abstractmethod
    def search(self, namespace: str, query: str, limit: int = 5) -> List[MemoryRecord]:
        """
        Searches for memories semantically similar to the query.

        Args:
            namespace (str): The collection/namespace to search within.
            query (str): The natural language query.
            limit (int): The maximum number of records to return.

        Returns:
            List[MemoryRecord]: A list of retrieved memory records.
        """
        pass

    @abstractmethod
    def delete(self, namespace: str, record_id: str) -> bool:
        """
        Deletes a specific memory record by ID.

        Args:
            namespace (str): The collection/namespace the record is in.
            record_id (str): The ID of the record to delete.

        Returns:
            bool: True if deleted, False if not found.
        """
        pass
