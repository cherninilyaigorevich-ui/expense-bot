from datetime import date

from app.services.archive import get_month_bounds
from app.services.retention import subtract_months
from app.tasks.monthly_maintenance import previous_month


def test_previous_month_regular():
    assert previous_month(
        date(2026, 8, 24)
    ) == (2026, 7)


def test_previous_month_january():
    assert previous_month(
        date(2027, 1, 1)
    ) == (2026, 12)


def test_subtract_months():
    assert subtract_months(
        year=2026,
        month=8,
        months=3,
    ) == (2026, 5)


def test_subtract_months_cross_year():
    assert subtract_months(
        year=2027,
        month=2,
        months=3,
    ) == (2026, 11)


def test_get_month_bounds_august():
    date_from, date_to = get_month_bounds(
        year=2026,
        month=8,
    )

    assert date_from == date(2026, 8, 1)
    assert date_to == date(2026, 8, 31)


def test_get_month_bounds_february():
    date_from, date_to = get_month_bounds(
        year=2028,
        month=2,
    )

    assert date_from == date(2028, 2, 1)
    assert date_to == date(2028, 2, 29)
