"""
Tests for Chhaya ChromaDB Memory Provider.
"""

import pytest
import chromadb

from chhaya_v1.infrastructure.memory.chroma import ChromaMemoryProvider
from chhaya_v1.interfaces.memory_provider import MemoryRecord


@pytest.fixture
def ephemeral_chroma_provider():
    """Provides a memory provider backed by an ephemeral (in-memory) Chroma client."""
    client = chromadb.EphemeralClient()
    return ChromaMemoryProvider(client=client)


def test_chroma_memory_store_and_search(ephemeral_chroma_provider):
    provider = ephemeral_chroma_provider
    namespace = "test_agent_memory"

    record1 = MemoryRecord(id="mem1", text="The capital of France is Paris.", metadata={"type": "fact"})
    record2 = MemoryRecord(id="mem2", text="The user likes blue.", metadata={"type": "preference"})
    record3 = MemoryRecord(id="mem3", text="Python is a programming language.", metadata={"type": "fact"})

    # Store
    provider.store(namespace, record1)
    provider.store(namespace, record2)
    provider.store(namespace, record3)

    # Search (Semantic matching)
    # The default Chroma embedding model is all-MiniLM-L6-v2 which should map these easily.
    results = provider.search(namespace, "What does the user like?", limit=1)

    assert len(results) == 1
    assert results[0].id == "mem2"
    assert "blue" in results[0].text
    assert results[0].metadata["type"] == "preference"


def test_chroma_memory_isolation(ephemeral_chroma_provider):
    """Test that namespaces are isolated."""
    provider = ephemeral_chroma_provider

    ns1 = "agent_1"
    ns2 = "agent_2"

    provider.store(ns1, MemoryRecord(id="secret1", text="Agent 1 secret formula."))
    provider.store(ns2, MemoryRecord(id="secret2", text="Agent 2 secret formula."))

    # Agent 1 searches for formulas
    results_ns1 = provider.search(ns1, "secret formula")
    assert len(results_ns1) == 1
    assert results_ns1[0].id == "secret1"

    # Agent 2 searches for formulas
    results_ns2 = provider.search(ns2, "secret formula")
    assert len(results_ns2) == 1
    assert results_ns2[0].id == "secret2"


def test_chroma_memory_delete(ephemeral_chroma_provider):
    provider = ephemeral_chroma_provider
    namespace = "temp_ns"

    provider.store(namespace, MemoryRecord(id="temp1", text="Temporary memory."))

    # Exists?
    results = provider.search(namespace, "temp")
    assert len(results) == 1

    # Delete
    deleted = provider.delete(namespace, "temp1")
    assert deleted is True

    # Should not exist
    results_after = provider.search(namespace, "temp")
    assert len(results_after) == 0

    # Delete non-existent
    deleted_again = provider.delete(namespace, "temp1")
    assert deleted_again is False
