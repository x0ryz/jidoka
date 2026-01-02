from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from src.core.database import get_session
from src.core.exceptions import NotFoundError
from src.core.uow import UnitOfWork
from src.schemas import TemplateListResponse, TemplateResponse

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("", response_model=list[TemplateListResponse])
async def list_templates(session: AsyncSession = Depends(get_session)):
    """
    Get all message templates.

    Returns templates synced from Meta WhatsApp Business API.
    """
    uow = UnitOfWork(lambda: session)
    async with uow:
        return await uow.templates.get_all_sorted()


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    Get specific template by ID.
    """
    uow = UnitOfWork(lambda: session)
    async with uow:
        template = await uow.templates.get_by_id(template_id)

        if not template:
            raise NotFoundError(detail="Template not found")

        return template


@router.get("/by-status/{status_filter}", response_model=list[TemplateListResponse])
async def get_templates_by_status(
    status_filter: str, session: AsyncSession = Depends(get_session)
):
    """Get templates filtered by status."""
    uow = UnitOfWork(lambda: session)
    async with uow:
        return await uow.templates.get_by_status(status_filter)
