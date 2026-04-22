import sqlite3
import pandas as pd
from datetime import datetime
from loguru import logger

from config import settings
from data.models import SignalData

class TradeJournal:
    """SQLite-based signal journal for tracking and validation."""

    def __init__(self):
        self.db_path = settings.get_db_path()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry REAL NOT NULL,
                sl REAL NOT NULL,
                tp1 REAL NOT NULL,
                tp2 REAL,
                rr REAL NOT NULL,
                reason TEXT,
                timestamp TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                status TEXT DEFAULT 'PENDING',
                outcome TEXT,
                realized_rr REAL,
                closed_at TEXT
            )
        ''')
        self.conn.commit()
        logger.info("Journal database initialized at {}", self.db_path)

    def log_signal(self, signal: SignalData):
        """Log new signal."""
        self.conn.execute('''
            INSERT INTO signals 
            (symbol, direction, entry, sl, tp1, tp2, rr, reason, timestamp, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal.symbol,
            signal.direction,
            signal.entry,
            signal.sl,
            signal.tp1,
            signal.tp2,
            signal.rr,
            signal.reason,
            datetime.utcnow().isoformat(),
            getattr(signal, 'confidence', 0.0)
        ))
        self.conn.commit()
        logger.info("Signal logged: {} {}", signal.symbol, signal.direction)

    def update_outcome(self, signal_id: int, outcome: str, realized_rr: float = 0.0):
        """Update signal with manual outcome (used by Telegram commands)."""
        self.conn.execute('''
            UPDATE signals 
            SET outcome = ?, realized_rr = ?, closed_at = ?, status = 'CLOSED'
            WHERE id = ?
        ''', (outcome, realized_rr, datetime.utcnow().isoformat(), signal_id))
        self.conn.commit()

    def get_recent_signals(self, limit: int = 50) -> pd.DataFrame:
        """Return recent signals for review."""
        return pd.read_sql_query(
            "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?",
            self.conn, params=(limit,)
        )

    def get_metrics_summary(self) -> dict:
        """Basic performance overview."""
        df = pd.read_sql_query("SELECT * FROM signals WHERE outcome IS NOT NULL", self.conn)
        if df.empty:
            return {"total_closed": 0}

        wins = (df['outcome'] == 'WIN').sum()
        win_rate = wins / len(df) * 100 if len(df) > 0 else 0
        avg_rr = df['realized_rr'].mean() if 'realized_rr' in df.columns else 0

        return {
            "total_signals": len(pd.read_sql_query("SELECT id FROM signals", self.conn)),
            "total_closed": len(df),
            "win_rate_pct": round(win_rate, 1),
            "avg_realized_rr": round(avg_rr, 2)
        }

    def close(self):
        self.conn.close()