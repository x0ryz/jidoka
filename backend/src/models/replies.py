from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class QuickReply(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quick_replies"

<<<<<<< HEAD
    shortcut: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )

    title: Mapped[str] = mapped_column(String(100), nullable=False)

    content: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)

    default_language: Mapped[str] = mapped_column(String(5), default="uk")

    def get_text(self, lang: str) -> str:
        """Повертає текст потрібною мовою або дефолтною"""
        return self.content.get(lang, self.content.get(self.default_language, ""))
=======
    title: Mapped[str] = mapped_column(String(100), nullable=False)

    content: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)

    def get_text(self, lang: str) -> str:
        """Повертає текст потрібною мовою або першою доступною"""
        if lang in self.content:
            return self.content[lang]
        # Fallback на першу доступну мову
        return next(iter(self.content.values()), "")
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
