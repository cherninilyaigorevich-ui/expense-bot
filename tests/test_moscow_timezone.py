from datetime import datetime, date, timezone

from app.dates import local_today


def test_moscow_date_before_midnight():
    now = datetime(2026, 10, 26, 20, 30, tzinfo=timezone.utc)
    assert local_today(now) == date(2026, 10, 26)


def test_moscow_date_after_midnight():
    now = datetime(2026, 10, 26, 21, 30, tzinfo=timezone.utc)
    assert local_today(now) == date(2026, 10, 27)
