from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List
from pathlib import Path
import os
from dotenv import load_dotenv
from loguru import logger

# Load .env for local development + fallback
load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Telegram (Required)
    TELEGRAM_TOKEN: str = Field(..., description="Telegram Bot Token")
    TELEGRAM_CHAT_ID: str = Field(..., description="Telegram Channel/Group ID")
    TELEGRAM_ADMIN_ID: int = Field(..., description="Your Telegram User ID (number only)")

    # Binance
    BINANCE_API_KEY: str = Field(default="")
    BINANCE_API_SECRET: str = Field(default="")
    USE_TESTNET: bool = Field(default=True)

    # Core Pairs & Risk
    CORE_PAIRS: List[str] = Field(
        default_factory=lambda: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "LINKUSDT", "AVAXUSDT"]
    )
    DYNAMIC_PAIR_LIMIT: int = Field(default=5, ge=0, le=10)
    MIN_24H_VOLUME_USDT: float = Field(default=50_000_000.0)

    MAX_RISK_PER_TRADE: float = Field(default=0.005)
    DAILY_LOSS_LIMIT_PCT: float = Field(default=2.0)
    WEEKLY_LOSS_LIMIT_PCT: float = Field(default=5.0)
    MAX_CONCURRENT_SIGNALS: int = Field(default=3)
    MIN_RR: float = Field(default=2.0)

    DEAD_ZONE_HOURS: List[int] = Field(default_factory=lambda: list(range(0, 7)))

    SCAN_INTERVAL_MINUTES: int = Field(default=5)
    HEALTH_PORT: int = 8000
    ENABLE_SAFE_MODE: bool = Field(default=True)

    DB_PATH: str = Field(default="data/journal.db")
    LOG_PATH: str = Field(default="logs/bot_{time:YYYY-MM-DD}.log")

    @field_validator("TELEGRAM_ADMIN_ID")
    @classmethod
    def validate_admin_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("TELEGRAM_ADMIN_ID must be a positive integer")
        return v

    def get_db_path(self) -> Path:
        path = Path(self.DB_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


# Global instance
settings = Settings()

logger.add(
    settings.LOG_PATH,
    rotation="00:00",
    retention="7 days",
    level="INFO",
    enqueue=True
)

logger.info("✅ Config loaded successfully | Safe Mode: {} | Testnet: {}", 
            settings.ENABLE_SAFE_MODE, settings.USE_TESTNET)