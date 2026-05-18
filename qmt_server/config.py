"""Configuration management for QMT Server"""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """QMT Server configuration loaded from env vars and config.json"""

    # Server settings
    host: str = Field(default="0.0.0.0", alias="QMT_SERVER_HOST")
    port: int = Field(default=8080, alias="QMT_SERVER_PORT")
    log_level: str = Field(default="INFO", alias="QMT_LOG_LEVEL")

    # QMT paths
    xtquant_path: str = Field(default="", alias="QMT_XTQUANT_PATH")
    userdata_path: str = Field(default="", alias="QMT_USERDATA_PATH")

    # Account settings
    account_id: str = Field(default="", alias="QMT_ACCOUNT_ID")
    account_type: str = Field(default="STOCK", alias="QMT_ACCOUNT_TYPE")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, alias="QMT_RATE_LIMIT_ENABLED")
    rate_limit_rpm: int = Field(default=60, alias="QMT_RATE_LIMIT_RPM")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Reload configuration from environment"""
    global _config
    _config = Config()
    return _config