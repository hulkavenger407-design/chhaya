"""
Tests for Chhaya SQLite Storage Provider.
"""

import tempfile
import os
import pytest

from chhaya.infrastructure.storage.sqlite import SQLiteStorageProvider


@pytest.fixture
def temp_db_url():
    """Provides a temporary SQLite database URL for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{path}"

    yield db_url

    # Cleanup after test
    if os.path.exists(path):
        os.unlink(path)


def test_sqlite_storage_save_and_load(temp_db_url):
    """Test saving data and retrieving it."""
    storage = SQLiteStorageProvider(database_url=temp_db_url)

    test_collection = "agents"
    test_key = "agent_001"
    test_data = {
        "name": "TestAgent",
        "role": "Helper",
        "version": 1
    }

    # Ensure it's not there initially
    assert storage.load(test_collection, test_key) is None

    # Save the data
    storage.save(test_collection, test_key, test_data)

    # Load the data
    loaded_data = storage.load(test_collection, test_key)

    assert loaded_data is not None
    assert loaded_data["name"] == "TestAgent"
    assert loaded_data["role"] == "Helper"
    assert loaded_data["version"] == 1


def test_sqlite_storage_update(temp_db_url):
    """Test that saving to an existing collection/key updates the record."""
    storage = SQLiteStorageProvider(database_url=temp_db_url)

    test_collection = "config"
    test_key = "global"

    # Initial save
    storage.save(test_collection, test_key, {"theme": "dark"})
    assert storage.load(test_collection, test_key)["theme"] == "dark"

    # Update save
    storage.save(test_collection, test_key, {"theme": "light", "version": 2})

    updated_data = storage.load(test_collection, test_key)
    assert updated_data["theme"] == "light"
    assert updated_data["version"] == 2
