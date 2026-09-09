from datetime import date, datetime
from zoneinfo import ZoneInfo


APP_TIMEZONE = ZoneInfo("Europe/Moscow")


def local_today(now: datetime | None = None) -> date:
    """Текущая календарная дата семейного бюджета."""

    if now is None:
        now = datetime.now(APP_TIMEZONE)
    elif now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    else:
        now = now.astimezone(APP_TIMEZONE)

    return now.date()
