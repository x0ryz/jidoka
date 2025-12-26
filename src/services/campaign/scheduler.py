import asyncio
import json
from typing import Callable

from loguru import logger
from redis import asyncio as aioredis

from src.core.config import settings
from src.core.database import async_session_maker
from src.core.uow import UnitOfWork
from src.models import get_utc_now


class CampaignScheduler:
    """
    Background service that checks for scheduled campaigns and starts them.
    Runs every minute to check if any campaigns should be started.
    """

    def __init__(self, redis_publisher: Callable[[str, str], None] = None):
        self.redis_publisher = redis_publisher
        self.running = False

    async def start(self):
        """Start the scheduler loop"""
        self.running = True
        logger.info("Campaign Scheduler started")

        while self.running:
            try:
                await self._check_scheduled_campaigns()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                logger.info("Campaign Scheduler cancelled")
                break
            except Exception as e:
                logger.exception(f"Error in Campaign Scheduler: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Campaign Scheduler stopped")

    async def _check_scheduled_campaigns(self):
        """Check for campaigns that should be started"""
        now = get_utc_now()

        uow = UnitOfWork(async_session_maker)

        async with uow:
            # Get campaigns scheduled to start now or earlier
            campaigns = await uow.campaigns.get_scheduled_campaigns(now)

            if not campaigns:
                return

            logger.info(f"Found {len(campaigns)} campaigns to start")

            for campaign in campaigns:
                try:
                    logger.info(
                        f"Starting scheduled campaign: {campaign.id} - {campaign.name}"
                    )

                    # Publish to Redis for worker to process
                    await self._publish_campaign_start(str(campaign.id))

                except Exception as e:
                    logger.exception(f"Failed to start campaign {campaign.id}: {e}")

    async def _publish_campaign_start(self, campaign_id: str):
        """Publish campaign start event to Redis"""
        try:
            redis = aioredis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )

            payload = {"campaign_id": campaign_id}

            await redis.publish("campaign_start", json.dumps(payload))
            await redis.close()

            logger.info(f"Published campaign start event: {campaign_id}")

        except Exception as e:
            logger.error(f"Failed to publish campaign start: {e}")
