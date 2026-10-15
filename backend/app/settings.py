import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")


def local_today():
    return datetime.now(timezone.utc).astimezone(ZoneInfo(APP_TIMEZONE)).date()


def timestamp_date(value):
    return datetime.fromisoformat(value).astimezone(ZoneInfo(APP_TIMEZONE)).date().isoformat()
