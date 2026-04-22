import asyncio
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from loguru import logger

from config import settings
from data.models import SignalData
from risk.manager import RiskManager
from tracking.journal import TradeJournal
from tracking.metrics import PerformanceMetrics

class TelegramNotifier:
    """Production Telegram integration with signal alerts and admin commands."""

    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_TOKEN)
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.admin_id = settings.TELEGRAM_ADMIN_ID
        self.application = None
        self.risk_manager: RiskManager = None
        self.journal: TradeJournal = None
        self.metrics: PerformanceMetrics = None

    async def send_startup(self):
        """Send startup notification."""
        msg = f"""
🟢 **ApexSentinel Hybrid Signal Bot Started**

Safe Mode: {'✅ ON' if settings.ENABLE_SAFE_MODE else '⚠️ OFF'}
Scan Interval: {settings.SCAN_INTERVAL_MINUTES} minutes
Core Pairs: {len(settings.CORE_PAIRS)}
Min RR: {settings.MIN_RR}:1
Risk per trade: {settings.MAX_RISK_PER_TRADE*100:.1f}%
        """
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=msg, parse_mode='Markdown')
            logger.info("Startup message sent to Telegram")
        except Exception as e:
            logger.error("Failed to send startup message: {}", e)

    async def send_signal(self, signal: SignalData):
        """Send clean, actionable signal to Telegram."""
        session_name = __import__('filters.session').SessionFilter.get_session_name()

        msg = f"""
🚨 **NEW SIGNAL** 🚨

**{signal.symbol}** — **{signal.direction}**

**Entry:** `{signal.entry:.4f}`
**Stop Loss:** `{signal.sl:.4f}`
**TP1:** `{signal.tp1:.4f}`
**TP2:** `{signal.tp2:.4f if signal.tp2 else '—'}`
**RR:** `{signal.rr:.2f}:1`

**Reason:** {signal.reason}
**Session:** {session_name}
**Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Use /outcome {signal.symbol} WIN/LOSS [RR] to record result.
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg.strip(),
                parse_mode='Markdown'
            )
            logger.info("Signal sent to Telegram: {} {}", signal.symbol, signal.direction)
        except Exception as e:
            logger.error("Telegram send failed: {}", e)

    async def send_summary(self):
        """Send daily performance summary."""
        if not self.risk_manager or not self.journal:
            return

        status = self.risk_manager.get_status()
        metrics = self.journal.get_metrics_summary()

        msg = f"""
📊 **ApexSentinel Daily Summary**

Kill Switch: {'🔴 ACTIVATED' if status['kill_switch'] else '🟢 OFF'}
Daily PnL: {status['daily_pnl_pct']}%
Active Signals: {status['active_signals']}
Total Signals: {metrics.get('total_signals', 0)}
Closed Trades: {metrics.get('total_closed', 0)}
Win Rate: {metrics.get('win_rate_pct', 0)}%

Use /status for full details.
        """
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error("Summary send failed: {}", e)

    # ==================== Admin Commands ====================

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        if not self.risk_manager:
            await update.message.reply_text("Risk manager not initialized.")
            return

        status = self.risk_manager.get_status()
        await update.message.reply_text(
            f"**ApexSentinel Status**\n"
            f"Kill Switch: {'ON' if status['kill_switch'] else 'OFF'}\n"
            f"Daily PnL: {status['daily_pnl_pct']}%\n"
            f"Active Signals: {status['active_signals']}\n"
            f"Safe Mode: {'ON' if status['safe_mode'] else 'OFF'}",
            parse_mode='Markdown'
        )

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        if self.risk_manager:
            self.risk_manager.toggle_kill_switch(True)
            await update.message.reply_text("🛑 Bot paused (Kill switch activated)")
        else:
            await update.message.reply_text("Risk manager not ready.")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        if self.risk_manager:
            self.risk_manager.toggle_kill_switch(False)
            await update.message.reply_text("✅ Bot resumed (Kill switch deactivated)")
        else:
            await update.message.reply_text("Risk manager not ready.")

    async def cmd_outcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: `/outcome SYMBOL OUTCOME [REALIZED_RR]`\nExample: `/outcome BTCUSDT WIN 2.3`")
            return

        symbol = args[0].upper()
        outcome = args[1].upper()
        realized_rr = float(args[2]) if len(args) > 2 else 0.0

        if outcome not in ["WIN", "LOSS", "BREAKEVEN"]:
            await update.message.reply_text("Outcome must be WIN, LOSS or BREAKEVEN")
            return

        # Find latest signal for this symbol (simple implementation)
        df = self.journal.get_recent_signals(limit=20)
        recent = df[df['symbol'] == symbol]
        if recent.empty:
            await update.message.reply_text(f"No recent signal found for {symbol}")
            return

        signal_id = recent.iloc[0]['id']
        self.risk_manager.record_outcome(symbol, outcome, realized_rr)
        self.journal.update_outcome(signal_id, outcome, realized_rr)

        await update.message.reply_text(f"✅ Recorded: {symbol} → {outcome} (RR: {realized_rr})")

    async def cmd_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.admin_id:
            return
        await self.send_summary()