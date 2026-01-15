from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base
from src.models.base import UUIDMixin, get_utc_now


class WebhookLog(Base, UUIDMixin):
    __tablename__ = "webhook_logs"

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now
    )
