from faststream.nats import NatsBroker

from src.core.config import settings
from src.core.logger import setup_logging

logger = setup_logging()

broker = NatsBroker(
    servers=[settings.NATS_URL],
    graceful_timeout=30.0,
)


async def setup_jetstream():
    """
    Configure JetStream streams and Key-Value buckets.
    This is called during broker startup.
    """
    if not broker._connection:
        logger.warning("Broker not connected - skipping JetStream setup")
        return

    try:
        js = broker._connection.jetstream()

        try:
            await js.add_stream(
                name="campaigns",
                subjects=["campaigns.>"],
                retention="limits",
                max_msgs=1_000_000,
                max_age=7 * 24 * 3600,
                storage="file",
                discard="old",
            )
            logger.info("JetStream stream 'campaigns' configured successfully")
        except Exception as e:
            logger.info(
                f"JetStream stream 'campaigns' already exists or error: {e}")
            try:
                # Ensure stream subjects support multi-level tokens
                await js.update_stream(
                    name="campaigns",
                    subjects=["campaigns.>"],
                )
                logger.info(
                    "JetStream stream 'campaigns' subjects updated to campaigns.>")
            except Exception as ue:
                logger.info(
                    f"JetStream stream 'campaigns' update skipped or failed: {ue}")

        try:
            await js.create_key_value(
                bucket="processed_messages",
                ttl=24 * 3600,
                storage="file",
            )
            logger.info(
                "JetStream KV bucket 'processed_messages' configured successfully"
            )
        except Exception as e:
            logger.info(
                f"JetStream KV bucket 'processed_messages' already exists or error: {e}"
            )

    except Exception as e:
        logger.error(f"JetStream setup failed: {e}")
