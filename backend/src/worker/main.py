import asyncio

import httpx
from faststream import ContextRepo, FastStream

from src.core.broker import broker, setup_jetstream
from src.worker.dependencies import logger
from src.worker.routers.campaigns import router as campaigns_router
from src.worker.routers.media import router as media_router
from src.worker.routers.messages import router as messages_router
from src.worker.routers.system import router as system_router
from src.worker.tasks import scheduled_campaigns_checker

app = FastStream(broker)

broker.include_router(campaigns_router)
broker.include_router(messages_router)
broker.include_router(media_router)
broker.include_router(system_router)

scheduler_task: asyncio.Task | None = None


@app.on_startup
async def startup_handler(context: ContextRepo):
    global scheduler_task
    logger.info("FastStream Worker: Starting up...")

    http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
    )
    context.set_global("http_client", http_client)

    await setup_jetstream()

    scheduler_task = asyncio.create_task(scheduled_campaigns_checker(broker))
    logger.info("Startup complete.")


@app.on_shutdown
async def shutdown_handler(context: ContextRepo):
    global scheduler_task
    logger.info("FastStream Worker: Shutting down...")

    if scheduler_task:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

    http_client = context.get("http_client")
    if http_client:
        await http_client.aclose()
    logger.info("Shutdown complete.")
