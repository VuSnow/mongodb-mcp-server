from pathlib import Path
from pydantic import Field
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]

class ServerConfigs(BaseSettings):
    """Configuration for the MongoDB MCP Server."""

    connection_string: str = Field(
        ...,
        alias="MONGODB_CONNECTION_STRING",
        description="MongoDB connection URI, e.g. mongodb://localhost:27017 or mongodb+srv://...",
    )

    read_only: bool = Field(
        True,
        alias="READ_ONLY",
        description="When enabled, only read and metadata operations are allowed.",
    )

    default_timeout_ms: Optional[int] = Field(
        30000,
        alias="DEFAULT_TIMEOUT_MS",
        description="Default timeout in milliseconds for MongoDB operations.",
    )

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

configs = ServerConfigs()