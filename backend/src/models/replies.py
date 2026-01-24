from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class QuickReply(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quick_replies"

    title: Mapped[str] = mapped_column(String(100), nullable=False)

    content: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)

    def get_text(self, lang: str) -> str:
        """Повертає текст потрібною мовою або першою доступною"""
        if lang in self.content:
            return self.content[lang]
        # Fallback на першу доступну мову
        return next(iter(self.content.values()), "")
