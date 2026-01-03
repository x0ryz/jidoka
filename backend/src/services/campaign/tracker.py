from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from src.models import get_utc_now


@dataclass
class CampaignProgressTracker:
    """
    Трекер прогресу однієї кампанії.

    Responsibilities:
    - Зберігати статистику кампанії
    - Розраховувати швидкість відправки
    - Прогнозувати час завершення
    """

    campaign_id: UUID
    start_time: datetime = field(default_factory=get_utc_now)

    batches_processed: int = 0

    total_sent: int = 0
    total_failed: int = 0

    def increment_sent(self):
        """Інкрементувати лічильник відправлених"""
        self.total_sent += 1

    def increment_failed(self):
        """Інкрементувати лічильник невдалих"""
        self.total_failed += 1

    def increment_batch(self):
        """Інкрементувати лічильник батчів"""
        self.batches_processed += 1

    def calculate_rate(self) -> float:
        """
        Розрахувати швидкість відправки (повідомлень на хвилину).

        Returns:
            float: Кількість повідомлень на хвилину
        """
        elapsed_seconds = (get_utc_now() - self.start_time).total_seconds()

        if elapsed_seconds <= 0:
            return 0.0

        if self.total_sent <= 0:
            return 0.0

        # messages per minute = (messages / seconds) * 60
        return (self.total_sent / elapsed_seconds) * 60

    def estimate_completion(self, remaining_contacts: int) -> str | None:
        """
        Прогнозувати час завершення кампанії.

        Args:
            remaining_contacts: Скільки контактів залишилося обробити

        Returns:
            str | None: ISO timestamp коли завершиться, або None якщо неможливо розрахувати
        """
        rate_per_minute = self.calculate_rate()

        if rate_per_minute <= 0:
            return None

        # Скільки хвилин потрібно для remaining_contacts
        eta_minutes = remaining_contacts / rate_per_minute
        eta_seconds = eta_minutes * 60

        completion_time = get_utc_now() + timedelta(seconds=eta_seconds)
        return completion_time.isoformat()

    def get_elapsed_time(self) -> float:
        """Отримати скільки часу минуло з початку (в секундах)"""
        return (get_utc_now() - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        """
        Конвертувати в словник для логування/API.

        Returns:
            dict: Всі метрики трекера
        """
        return {
            "campaign_id": str(self.campaign_id),
            "batches_processed": self.batches_processed,
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "rate_per_minute": round(self.calculate_rate(), 2),
            "elapsed_seconds": round(self.get_elapsed_time(), 2),
            "started_at": self.start_time.isoformat(),
        }

    def __repr__(self) -> str:
        """Readable representation для дебагу"""
        return (
            f"CampaignProgressTracker("
            f"id={self.campaign_id}, "
            f"sent={self.total_sent}, "
            f"failed={self.total_failed}, "
            f"rate={self.calculate_rate():.2f}/min"
            f")"
        )
