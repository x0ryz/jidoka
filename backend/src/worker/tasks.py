import asyncio

from src.core.database import async_session_maker
from src.models import CampaignStatus, get_utc_now
from src.repositories.campaign import CampaignRepository
from src.services.campaign.lifecycle import CampaignLifecycleManager
from src.services.notifications.service import NotificationService
from src.worker.dependencies import logger


async def scheduled_campaigns_checker(broker):
    """Background task that checks for scheduled campaigns every minute"""
    logger.info("Scheduled campaigns checker started")
    while True:
        try:
            await asyncio.sleep(60)
            logger.debug("Checking for scheduled campaigns...")
            now = get_utc_now()
            async with async_session_maker() as session:
                campaigns_repo = CampaignRepository(session)

                # Check for scheduled campaigns to start
                campaigns = await campaigns_repo.get_scheduled_campaigns(now)
                for campaign in campaigns:
                    logger.info(
                        f"Triggering scheduled campaign: {campaign.id}")
                    await broker.publish(
                        str(campaign.id),
                        subject="campaigns.start",
                        stream="campaigns",
                    )

                # Check for running/paused campaigns that might need completion
                running_campaigns = await campaigns_repo.list_with_status(CampaignStatus.RUNNING)
                paused_campaigns = await campaigns_repo.list_with_status(CampaignStatus.PAUSED)

                all_active = running_campaigns + paused_campaigns
                if all_active:
                    logger.debug(
                        f"Checking completion for {len(all_active)} active campaigns")

                for campaign in all_active:
                    try:
                        # Use a fresh session for each campaign check
                        async with async_session_maker() as check_session:
                            check_campaigns_repo = CampaignRepository(
                                check_session)
                            notifier = NotificationService()
                            lifecycle = CampaignLifecycleManager(
                                check_session, check_campaigns_repo, notifier, {}
                            )
                            await lifecycle.check_and_complete_if_done(campaign.id)
                            await check_session.commit()
                    except Exception as e:
                        logger.error(
                            f"Error checking completion for campaign {campaign.id}: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("Scheduled campaigns checker stopped")
            break
        except Exception as e:
            logger.error(f"Error in scheduled campaigns checker: {e}")
