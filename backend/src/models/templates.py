from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base
from src.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.campaigns import Campaign
    from src.models.waba import WabaAccount


class Template(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "templates"

    waba_id: Mapped[UUID] = mapped_column(ForeignKey("waba_accounts.id"))
    waba: Mapped["WabaAccount | None"] = relationship(back_populates="templates")

    meta_template_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    name: Mapped[str] = mapped_column(String, index=True)
    language: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)

    components: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="template")
