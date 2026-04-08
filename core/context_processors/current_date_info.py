from datetime import datetime


def current_date_info(request):
    """Информации о текущей дате."""
    now = datetime.now()
    return {
        "current_year": now.year,
        "current_month": now.month,
        "current_day": now.day,
        "current_date": now.date(),
        "current_datetime": now,
    }
