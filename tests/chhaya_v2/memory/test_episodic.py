import pytest
import sqlite3
import os
from chhaya_v2.memory.stores.episodic import EpisodicMemory

@pytest.fixture
def test_db():
    db_path = "test_episodic.db"
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

def test_episodic_memory(test_db):
    mem = EpisodicMemory(db_path=test_db)

    mem.store("Episode 1")
    mem.store("Episode 2")
    mem.store("Episode 3")

    retrieved = mem.retrieve(limit=2)
    assert len(retrieved) == 2
    assert "Episode 3" in retrieved
    assert "Episode 2" in retrieved
