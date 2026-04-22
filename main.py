import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI
from loguru import logger

from config import settings
from data.binance_client import BinanceDataClient
from strategy.signals import SignalEngine
from risk.manager import RiskManager
from tracking.journal import TradeJournal
from notification.telegram_bot import TelegramNotifier

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 ApexSentinel Hybrid Signal Bot starting... (Safe Mode: {})", settings.ENABLE_SAFE_MODE)

    app.state.data_client = BinanceDataClient()
    app.state.journal = TradeJournal()
    app.state.risk_manager = RiskManager(app.state.journal)
    app.state.notifier = TelegramNotifier()
    app.state.signal_engine = SignalEngine(
        data_client=app.state.data_client,
        journal=app.state.journal,
        notifier=app.state.notifier,
        risk_manager=app.state.risk_manager
    )

    await app.state.data_client.initialize()
    await app.state.notifier.send_startup()

    app.state.scanner_task = asyncio.create_task(app.state.signal_engine.start_scanner())

    yield

    logger.info("🛑 Shutting down ApexSentinel Bot...")
    if hasattr(app.state, "scanner_task"):
        app.state.scanner_task.cancel()
    await app.state.data_client.close()
    app.state.journal.close()

app = FastAPI(title="ApexSentinel Hybrid Signal Bot", lifespan=lifespan)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "safe_mode": settings.ENABLE_SAFE_MODE,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/readiness")
async def readiness():
    return {"status": "ready" if app.state.data_client.is_healthy() else "not_ready"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.HEALTH_PORT) 
