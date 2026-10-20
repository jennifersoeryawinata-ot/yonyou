from datetime import datetime, timezone

from sqlalchemy.orm import declared_attr
from sqlalchemy import MetaData
from sqlmodel import Field
from sqlmodel import SQLModel as _SQLModel
from stringcase import snakecase
from ulid import ULID
from utils.tz_datetime import TZDateTime
from configs.config import settings

_SQLModel.metadata = MetaData(schema=settings.POSTGRES_SCHEMA)

class SQLModel(_SQLModel):
    @declared_attr  # type: ignore
    def __tablename__(cls) -> str:
        return snakecase(cls.__name__)


def generate_default_utc_time() -> datetime:
    return datetime.now(tz=timezone.utc)


class BaseULIDModel(SQLModel):
    id: str = Field(default_factory=lambda: str(ULID()), primary_key=True, index=True, max_length=26)
    created_date: datetime | None = Field(default_factory=generate_default_utc_time, sa_type=TZDateTime, nullable=False)
    updated_date: datetime | None = Field(default_factory=generate_default_utc_time, sa_type=TZDateTime, nullable=False, sa_column_kwargs={"onupdate": generate_default_utc_time})
    created_by: str | None = Field(default=None, max_length=26)
    updated_by: str | None = Field(default=None, max_length=26)
