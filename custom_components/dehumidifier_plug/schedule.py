"""Pure weekday and interval evaluation."""
from datetime import datetime, time

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def is_in_schedule(
    now: datetime, weekdays: list[str], windows: list[tuple[time, time]]
) -> bool:
    """Evaluate intervals, attributing overnight intervals to the start day."""
    today = WEEKDAYS[now.weekday()]
    yesterday = WEEKDAYS[(now.weekday() - 1) % 7]
    current = now.time().replace(tzinfo=None)
    for start, end in windows:
        if start == end and today in weekdays:
            return True
        if start < end and today in weekdays and start <= current < end:
            return True
        if start > end and (
            (today in weekdays and current >= start)
            or (yesterday in weekdays and current < end)
        ):
            return True
    return False
