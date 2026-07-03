from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    """
    Core configuration for JARVIS V3 (Chhaya).
    Loads from environment variables or .env file.
    """
    # System
    environment: str = Field(default="development", description="Environment: development or production")

    # LLM Settings
    ollama_base_url: str = Field(default="http://localhost:11434", description="Base URL for local Ollama instance")
    default_chat_model: str = Field(default="phi3.5", description="Primary small model for chat/reasoning")
    default_code_model: str = Field(default="qwen-coder", description="Primary model for coding tasks")

    # Memory Settings
    chroma_db_dir: str = Field(default="./data/vector_db", description="Directory for ChromaDB storage")
    sqlite_db_path: str = Field(default="./data/jarvis.db", description="Path to SQLite database")

    # Voice Settings
    wake_word_model: str = Field(default="jarvis", description="Wake word to listen for")
    tts_backend: str = Field(default="melo", description="TTS engine: melo or piper")

    # Security
    master_key: Optional[str] = Field(default=None, description="Base64 encoded 32-byte AES key for Secret Manager")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}

# Global config instance
settings = Settings()
