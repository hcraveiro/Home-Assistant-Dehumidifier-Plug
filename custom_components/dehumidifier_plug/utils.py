import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from homeassistant.util import dt as dt_util
import logging

_LOGGER = logging.getLogger(__name__)

def slugify(value: str) -> str:
    """Simplified slugify function for entity_id creation.

    This function normalizes and converts a string to a lowercase,
    underscore-separated slug suitable for use in entity IDs.
    """
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[\s\-]+", "_", value)  # Replace spaces and dashes with a single underscore
    return value

def _safe_parse_dt(value: Any, *, assume_tz: timezone = timezone.utc) -> Optional[datetime]:
    """Parse a datetime persisted in storage robustly.
    Accepts None, str (ISO8601), or datetime. Returns tz-aware datetime or None.
    """
    # Already a datetime
    if isinstance(value, datetime):
        # Normalize: ensure tz-aware
        if value.tzinfo is None:
            return value.replace(tzinfo=assume_tz)
        return value

    # Only try to parse non-empty strings
    if isinstance(value, str) and value.strip():
        try:
            dt = dt_util.parse_datetime(value)  # returns aware or None
            if dt is None:
                # Fallback to stdlib for weird-but-valid ISO formats
                dt = datetime.fromisoformat(value)
            # Ensure tz-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=assume_tz)
            return dt
        except Exception as err:
            _LOGGER.debug("Failed to parse datetime from '%s': %s", value, err)

    # Anything else (None, empty string, wrong type) -> None
    return None