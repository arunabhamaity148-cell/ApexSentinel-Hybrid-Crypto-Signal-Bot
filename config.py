from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Binance
    BINANCE_API_KEY: str = Field(default="")
    BINANCE_API_SECRET: str = Field(default="")
    USE_TESTNET: bool = Field(default=True)

    # Telegram
    TELEGRAM_TOKEN: str = Field(..., description="Telegram Bot Token")
    TELEGRAM_CHAT_ID: str = Field(..., description="Signal channel ID")
    TELEGRAM_ADMIN_ID: int = Field(..., description="Admin user ID")

    # Core Pairs
    CORE_PAIRS: List[str] = Field(
        default_factory=lambda: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "LINKUSDT", "AVAXUSDT"]
    )
    DYNAMIC_PAIR_LIMIT: int = Field(default=5, ge=0, le=10)
    MIN_24H_VOLUME_USDT: float = Field(default=50_000_000.0)

    # Timeframes
    HTF: str = "4h"
    MTF: str = "1h"
    LTF: str = "15m"
    HISTORY_LIMIT: int = Field(default=500, ge=100)

    # Risk & Safety
    MAX_RISK_PER_TRADE: float = Field(default=0.005, ge=0.001, le=0.02)
    DAILY_LOSS_LIMIT_PCT: float = Field(default=2.0)
    WEEKLY_LOSS_LIMIT_PCT: float = Field(default=5.0)
    MAX_CONCURRENT_SIGNALS: int = Field(default=3)
    MIN_RR: float = Field(default=2.0, ge=1.5)

    # Session
    DEAD_ZONE_HOURS: List[int] = Field(default_factory=lambda: list(range(0, 7)))

    # Performance
    SCAN_INTERVAL_MINUTES: int = Field(default=5, ge=1, le=15)
    HEALTH_PORT: int = 8000
    ENABLE_SAFE_MODE: bool = True

    # Paths
    DB_PATH: str = Field(default="data/journal.db")
    LOG_PATH: str = Field(default="logs/bot_{time:YYYY-MM-DD}.log")

    @field_validator("CORE_PAIRS")
    @classmethod
    def validate_pairs(cls, v: List[str]) -> List[str]:
        return [p.upper() for p in v]

    def get_db_path(self) -> Path:
        path = Path(self.DB_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()