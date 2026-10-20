# pylint: skip-file
from datetime import datetime, timezone
from typing import Any

import pytz
from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy.engine import Dialect

__all__ = ["TZDateTime"]


class TZDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> Any:
        if value is not None:
            if value.tzinfo and value.tzinfo != pytz.utc:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> Any:
        if value is not None:
            value = value.replace(tzinfo=timezone.utc)
        return value
