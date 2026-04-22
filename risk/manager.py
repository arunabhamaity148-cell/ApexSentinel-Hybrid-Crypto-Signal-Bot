from datetime import datetime, timedelta
from typing import Dict
from loguru import logger

from config import settings
from data.models import SignalData
from tracking.journal import TradeJournal

class RiskManager:
    """Institutional risk engine for signal-only bot."""

    def __init__(self, journal: TradeJournal):
        self.journal = journal
        self.daily_pnl: float = 0.0
        self.weekly_pnl: float = 0.0
        self.last_reset_date = datetime.utcnow().date()
        self.pair_cooldown: Dict[str, datetime] = {}
        self.active_signals: Dict[str, SignalData] = {}
        self.kill_switch: bool = False

    def can_trade(self, symbol: str) -> bool:
        """Pre-check before signal generation."""
        if self.kill_switch:
            return False

        if not settings.ENABLE_SAFE_MODE:
            return True

        if self._is_loss_limit_breached():
            return False

        # Pair cooldown (prevent over-trading same setup)
        if symbol in self.pair_cooldown:
            if datetime.utcnow() - self.pair_cooldown[symbol] < timedelta(hours=6):
                return False

        # Max concurrent signals
        if len(self.active_signals) >= settings.MAX_CONCURRENT_SIGNALS:
            return False

        return True

    def accept_signal(self, signal: SignalData) -> bool:
        """Final risk gate before sending to Telegram."""
        if self.kill_switch:
            return False

        if signal.rr < settings.MIN_RR:
            return False

        self.active_signals[signal.symbol] = signal
        logger.info("Risk accepted: {} {} RR:{:.2f}", signal.symbol, signal.direction, signal.rr)
        return True

    def record_outcome(self, symbol: str, outcome: str, realized_rr: float = 0.0):
        """Manual outcome update from Telegram (WIN / LOSS / BREAKEVEN)."""
        if symbol in self.active_signals:
            del self.active_signals[symbol]

        self.pair_cooldown[symbol] = datetime.utcnow()

        if outcome == "WIN":
            self.daily_pnl += realized_rr * settings.MAX_RISK_PER_TRADE
            self.weekly_pnl += realized_rr * settings.MAX_RISK_PER_TRADE
        elif outcome == "LOSS":
            self.daily_pnl -= settings.MAX_RISK_PER_TRADE
            self.weekly_pnl -= settings.MAX_RISK_PER_TRADE

        self._is_loss_limit_breached()
        logger.info("Outcome recorded → {} | {} | RR: {:.2f}", symbol, outcome, realized_rr)

    def _is_loss_limit_breached(self) -> bool:
        """Check daily and weekly limits."""
        today = datetime.utcnow().date()
        if today != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = today

        if self.daily_pnl <= -settings.DAILY_LOSS_LIMIT_PCT / 100.0:
            logger.warning("🚨 DAILY LOSS LIMIT BREACHED - Blocking new signals")
            return True

        if self.weekly_pnl <= -settings.WEEKLY_LOSS_LIMIT_PCT / 100.0:
            logger.critical("🚨 WEEKLY LOSS LIMIT BREACHED - Kill switch ACTIVATED")
            self.kill_switch = True
            return True

        return False

    def toggle_kill_switch(self, state: bool):
        self.kill_switch = state
        status = "ACTIVATED" if state else "DEACTIVATED"
        logger.warning("Kill switch {}", status)

    def get_status(self) -> dict:
        return {
            "kill_switch": self.kill_switch,
            "daily_pnl_pct": round(self.daily_pnl * 100, 2),
            "weekly_pnl_pct": round(self.weekly_pnl * 100, 2),
            "active_signals": len(self.active_signals),
            "cooldown_count": len(self.pair_cooldown),
            "safe_mode": settings.ENABLE_SAFE_MODE
        }