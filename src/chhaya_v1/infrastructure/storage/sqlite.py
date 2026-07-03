"""
SQLite Storage Provider Implementation.
Uses SQLModel to persist data.
"""

import json
from typing import Any, List, Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import UniqueConstraint
import structlog

from chhaya_v1.interfaces.storage_provider import StorageProvider
from chhaya_v1.core.config import settings

logger = structlog.get_logger(__name__)


class GenericRecord(SQLModel, table=True):
    """
    A generic key-value store table mapping to collections.
    We use JSON strings to store arbitrary dict data, aligning with the interface.
    """
    __table_args__ = (UniqueConstraint("collection", "key", name="uix_collection_key"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    collection: str = Field(index=True)
    key: str = Field(index=True)
    data_json: str


class SQLiteStorageProvider(StorageProvider):
    """
    Concrete implementation of StorageProvider using SQLite (via SQLModel).
    """

    def __init__(self, database_url: str | None = None) -> None:
        """
        Initializes the SQLite Storage Provider.

        Args:
            database_url: The SQLAlchemy database URL. Defaults to config settings.
        """
        self.database_url = database_url or settings.storage.database_url
        self.engine = create_engine(self.database_url, connect_args={"check_same_thread": False})
        # Automatically create tables if they don't exist
        SQLModel.metadata.create_all(self.engine)
        logger.info("Initialized SQLite Storage Provider", database_url=self.database_url)

    def save(self, collection: str, key: str, data: dict[str, Any]) -> None:
        """
        Saves data to a specified collection with a key.
        Upserts the data if the collection+key already exists.
        """
        data_json = json.dumps(data)

        with Session(self.engine) as session:
            statement = select(GenericRecord).where(
                GenericRecord.collection == collection,
                GenericRecord.key == key
            )
            existing_record = session.exec(statement).first()

            if existing_record:
                existing_record.data_json = data_json
                session.add(existing_record)
                logger.debug("Updated existing record", collection=collection, key=key)
            else:
                new_record = GenericRecord(collection=collection, key=key, data_json=data_json)
                session.add(new_record)
                logger.debug("Created new record", collection=collection, key=key)

            try:
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error("Failed to commit to generic record", collection=collection, key=key, error=str(e))
                raise

    def load(self, collection: str, key: str) -> Optional[dict[str, Any]]:
        """
        Loads data from a specified collection by key.
        """
        with Session(self.engine) as session:
            statement = select(GenericRecord).where(
                GenericRecord.collection == collection,
                GenericRecord.key == key
            )
            record = session.exec(statement).first()

            if record:
                try:
                    return json.loads(record.data_json)
                except json.JSONDecodeError as e:
                    logger.error("Failed to decode JSON data", collection=collection, key=key, error=str(e))
                    return None

            return None

    def list(self, collection: str) -> List[dict[str, Any]]:
        """
        Retrieves all records from a specified collection.
        """
        results = []
        with Session(self.engine) as session:
            statement = select(GenericRecord).where(GenericRecord.collection == collection)
            records = session.exec(statement).all()

            for record in records:
                try:
                    results.append(json.loads(record.data_json))
                except json.JSONDecodeError as e:
                    logger.error("Failed to decode JSON data in list", collection=collection, key=record.key, error=str(e))

        return results
