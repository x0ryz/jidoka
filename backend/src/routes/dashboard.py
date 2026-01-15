from fastapi import APIRouter, Depends
from src.core.dependencies import get_dashboard_service
from src.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_stats()


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 20,
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_recent_activity(limit)


@router.get("/charts/messages-timeline")
async def get_messages_timeline(
    days: int = 7,
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_messages_timeline(days)


@router.get("/waba-status")
async def get_waba_status(
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_waba_status()
