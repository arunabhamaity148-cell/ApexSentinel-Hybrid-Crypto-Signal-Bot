from datetime import datetime
from config import settings
from loguru import logger

class SessionFilter:
    """London / New York session logic with overlap bonus."""

    @staticmethod
    def is_good_session() -> bool:
        """Return True during active trading sessions (UTC)."""
        now = datetime.utcnow()
        hour = now.hour
        minute = now.minute

        # London: 07:00 - 16:00
        london = 7 <= hour < 16
        # New York: 13:00 - 22:00
        ny = 13 <= hour < 22
        # Overlap bonus (strongest period)
        overlap = 13 <= hour < 16

        active = london or ny or overlap

        if not active and settings.ENABLE_SAFE_MODE:
            logger.debug("Session filter blocked: {}:{}", hour, minute)

        return active

    @staticmethod
    def get_session_name() -> str:
        hour = datetime.utcnow().hour
        if 13 <= hour < 16:
            return "LONDON-NY OVERLAP"
        elif 7 <= hour < 13:
            return "LONDON"
        elif 13 <= hour < 22:
            return "NEW YORK"
        return "DEAD ZONE"