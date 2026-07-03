"""
ChromaDB Memory Provider Implementation.
"""

from typing import List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
import structlog

from chhaya_v1.interfaces.memory_provider import MemoryProvider, MemoryRecord
from chhaya_v1.core.config import settings

logger = structlog.get_logger(__name__)


class ChromaMemoryProvider(MemoryProvider):
    """
    Concrete implementation of MemoryProvider using local ChromaDB.
    """

    def __init__(self, persist_directory: str | None = None, client: Optional[chromadb.ClientAPI] = None):
        """
        Initializes the ChromaDB Memory Provider.

        Args:
            persist_directory: Path to store ChromaDB data. Defaults to config settings.
            client: An existing ChromaDB client to use (mostly for testing).
        """
        if client:
            self.client = client
        else:
            self.persist_directory = persist_directory or settings.memory.path
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            logger.info("Initialized ChromaDB Persistent Client", path=self.persist_directory)

    def _get_or_create_collection(self, namespace: str):
        """Helper to get or create a collection (namespace)."""
        return self.client.get_or_create_collection(name=namespace)

    def store(self, namespace: str, record: MemoryRecord) -> None:
        """
        Stores a memory record in ChromaDB.
        Chroma automatically handles embedding generation if no embedding function is provided.
        """
        try:
            collection = self._get_or_create_collection(namespace)

            # Chroma expects IDs to be strings
            collection.add(
                ids=[record.id],
                documents=[record.text],
                metadatas=[record.metadata] if record.metadata else None
            )
            logger.debug("Stored memory", namespace=namespace, record_id=record.id)
        except Exception as e:
            logger.error("Failed to store memory in ChromaDB", namespace=namespace, error=str(e))
            raise

    def search(self, namespace: str, query: str, limit: int = 5) -> List[MemoryRecord]:
        """
        Searches ChromaDB for semantic matches.
        """
        try:
            collection = self._get_or_create_collection(namespace)

            results = collection.query(
                query_texts=[query],
                n_results=limit
            )

            records = []
            # Chroma returns lists of lists (one list per query string)
            if results and results.get("ids") and results["ids"][0]:
                ids = results["ids"][0]
                documents = results["documents"][0] if results.get("documents") else []
                metadatas = results["metadatas"][0] if results.get("metadatas") else []

                for i in range(len(ids)):
                    doc = documents[i] if i < len(documents) else ""
                    meta = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
                    records.append(MemoryRecord(id=ids[i], text=doc, metadata=meta))

            return records
        except Exception as e:
            logger.error("Failed to search memory in ChromaDB", namespace=namespace, error=str(e))
            raise

    def delete(self, namespace: str, record_id: str) -> bool:
        """
        Deletes a record from ChromaDB.
        """
        try:
            collection = self._get_or_create_collection(namespace)

            # Check if it exists first
            res = collection.get(ids=[record_id])
            if not res or not res.get("ids"):
                return False

            collection.delete(ids=[record_id])
            logger.debug("Deleted memory", namespace=namespace, record_id=record_id)
            return True
        except Exception as e:
            logger.error("Failed to delete memory from ChromaDB", namespace=namespace, error=str(e))
            raise
