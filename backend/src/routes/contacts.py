from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import desc, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession
from src.core.database import get_session
from src.core.exceptions import BadRequestError, NotFoundError
from src.core.uow import UnitOfWork
from src.models import Contact, get_utc_now
from src.schemas import MessageResponse
from src.schemas.contacts import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)
from src.services.chat import ChatService

router = APIRouter(tags=["Contacts"])


@router.get("/contacts", response_model=list[ContactListResponse])
async def get_contacts(session: AsyncSession = Depends(get_session)):
    """Get all contacts sorted by unread count and last activity"""
    statement = select(Contact).order_by(
        desc(Contact.unread_count), desc(Contact.updated_at)
    )
    result = await session.exec(statement)
    contacts = result.all()
    return contacts


@router.get("/contacts/search")
async def search_contacts(
    q: str, limit: int = 50, session: AsyncSession = Depends(get_session)
):
    """
    Search contacts by phone number or name.

    - **q**: Search query (phone or name)
    - **limit**: Maximum results to return
    """
    stmt = (
        select(Contact)
        .where(or_(Contact.phone_number.contains(q), Contact.name.ilike(f"%{q}%")))
        .limit(limit)
    )
    result = await session.exec(stmt)
    contacts = result.all()
    return contacts


@router.post(
    "/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED
)
async def create_contact(
    data: ContactCreate, session: AsyncSession = Depends(get_session)
):
    """
    Create a new contact manually.
    """
    uow = UnitOfWork(lambda: session)

    async with uow:
        # Check if contact already exists
        existing = await uow.contacts.get_by_phone(data.phone_number)
        if existing:
            raise BadRequestError(
                detail="Contact with this phone number already exists",
            )

        contact = Contact(
            phone_number=data.phone_number,
            name=data.name,
            tags=data.tags,
            source="manual",
            created_at=get_utc_now(),
            updated_at=get_utc_now(),
        )
        uow.session.add(contact)
        await uow.session.flush()
        await uow.session.refresh(contact)

        return contact


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: UUID, session: AsyncSession = Depends(get_session)):
    """Get single contact by ID"""
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise NotFoundError(detail="Contact not found")
    return contact


@router.patch("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID, data: ContactUpdate, session: AsyncSession = Depends(get_session)
):
    """Update contact details."""
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise NotFoundError(detail="Contact not found")

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(contact, key, value)

    contact.updated_at = get_utc_now()
    session.add(contact)
    await session.commit()
    await session.refresh(contact)

    return contact


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID, session: AsyncSession = Depends(get_session)
):
    """
    Delete a contact.

    This will also delete all associated messages.
    """
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise NotFoundError(detail="Contact not found")

    await session.delete(contact)
    await session.commit()


@router.post("/contacts/{contact_id}/mark-read", response_model=Contact)
async def mark_contact_as_read(
    contact_id: UUID, session: AsyncSession = Depends(get_session)
):
    """
    Mark all messages from this contact as read.
    """
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise NotFoundError(detail="Contact not found")

    contact.unread_count = 0
    contact.updated_at = get_utc_now()
    session.add(contact)
    await session.commit()
    await session.refresh(contact)

    return contact


@router.get("/contacts/{contact_id}/messages", response_model=list[MessageResponse])
async def get_chat_history(
    contact_id: UUID,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """
    Get chat history with a contact.
    """
    uow = UnitOfWork(lambda: session)

    chat_service = ChatService(uow)

    messages = await chat_service.get_chat_history(contact_id, limit, offset)

    if messages is None:
        raise NotFoundError(detail="Contact not found")

    return messages
