from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.exc import IntegrityError
<<<<<<< HEAD
from src.core.dependencies import get_uow
from src.core.exceptions import BadRequestError, NotFoundError
from src.core.uow import UnitOfWork
=======
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_session
from src.core.exceptions import BadRequestError, NotFoundError
from src.repositories.reply import QuickReplyRepository
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
from src.schemas.replies import (
    QuickReplyCreate,
    QuickReplyListResponse,
    QuickReplyResponse,
    QuickReplyTextResponse,
    QuickReplyUpdate,
)

router = APIRouter(prefix="/quick-replies", tags=["Quick Replies"])


<<<<<<< HEAD
@router.get("", response_model=list[QuickReplyListResponse])
async def list_quick_replies(
    search: str | None = Query(None, description="Search by title"),
    language: str | None = Query(None, description="Filter by available language"),
    uow: UnitOfWork = Depends(get_uow),
=======
@router.get("", response_model=list[QuickReplyResponse])
async def list_quick_replies(
    search: str | None = Query(None, description="Search by title"),
    language: str | None = Query(
        None, description="Filter by available language"),
    session: AsyncSession = Depends(get_session),
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
):
    """
    Get all quick replies with optional search and language filtering.

    - **search**: Search quick replies by title (case-insensitive)
    - **language**: Filter quick replies that have content in specified language
    """
<<<<<<< HEAD
    async with uow:
        if search:
            return await uow.quick_replies.search_by_title(search)
        elif language:
            return await uow.quick_replies.get_by_language(language)
        else:
            return await uow.quick_replies.get_all()
=======
    repo = QuickReplyRepository(session)
    if search:
        return await repo.search_by_title(search)
    elif language:
        return await repo.get_by_language(language)
    else:
        return await repo.get_all()
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)


@router.post("", response_model=QuickReplyResponse, status_code=status.HTTP_201_CREATED)
async def create_quick_reply(
<<<<<<< HEAD
    data: QuickReplyCreate, uow: UnitOfWork = Depends(get_uow)
=======
    data: QuickReplyCreate, session: AsyncSession = Depends(get_session)
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
):
    """
    Create a new quick reply.

<<<<<<< HEAD
    - **shortcut**: Unique identifier for quick access (max 50 characters)
    - **title**: Display name for the quick reply (max 100 characters)
    - **content**: Multi-language content as key-value pairs
    - **default_language**: Language code to use as fallback (default: "uk")
    """
    async with uow:
        try:
            quick_reply = await uow.quick_replies.create(data.model_dump())
            await uow.commit()
            await uow.session.refresh(quick_reply)
            return quick_reply
        except IntegrityError:
            raise BadRequestError(
                detail="Quick reply with this shortcut already exists"
            )


@router.get("/{reply_id}", response_model=QuickReplyResponse)
async def get_quick_reply(reply_id: UUID, uow: UnitOfWork = Depends(get_uow)):
    """
    Get specific quick reply by ID.
    """
    async with uow:
        quick_reply = await uow.quick_replies.get_by_id(reply_id)
        if not quick_reply:
            raise NotFoundError(detail="Quick reply not found")
        return quick_reply
=======
    """
    repo = QuickReplyRepository(session)
    quick_reply = await repo.create(data.model_dump())
    await session.commit()
    await session.refresh(quick_reply)
    return quick_reply


@router.get("/{reply_id}", response_model=QuickReplyResponse)
async def get_quick_reply(reply_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    Get specific quick reply by ID.
    """
    repo = QuickReplyRepository(session)
    quick_reply = await repo.get_by_id(reply_id)
    if not quick_reply:
        raise NotFoundError(detail="Quick reply not found")
    return quick_reply
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)


@router.patch("/{reply_id}", response_model=QuickReplyResponse)
async def update_quick_reply(
<<<<<<< HEAD
    reply_id: UUID, data: QuickReplyUpdate, uow: UnitOfWork = Depends(get_uow)
=======
    reply_id: UUID, data: QuickReplyUpdate, session: AsyncSession = Depends(get_session)
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
):
    """
    Update a quick reply.

    Only provided fields will be updated. All fields are optional.
    """
<<<<<<< HEAD
    async with uow:
        update_data = data.model_dump(exclude_unset=True)

        # Check if shortcut is being updated and if it conflicts
        if "shortcut" in update_data:
            existing = await uow.quick_replies.get_by_shortcut(update_data["shortcut"])
            if existing and existing.id != reply_id:
                raise BadRequestError(
                    detail="Quick reply with this shortcut already exists"
                )

        quick_reply = await uow.quick_replies.update(reply_id, update_data)
        if not quick_reply:
            raise NotFoundError(detail="Quick reply not found")

        await uow.commit()
        await uow.session.refresh(quick_reply)
        return quick_reply


@router.delete("/{reply_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quick_reply(reply_id: UUID, uow: UnitOfWork = Depends(get_uow)):
    """
    Delete a quick reply.
    """
    async with uow:
        success = await uow.quick_replies.delete(reply_id)
        if not success:
            raise NotFoundError(detail="Quick reply not found")
        await uow.commit()


@router.get("/shortcut/{shortcut}", response_model=QuickReplyResponse)
async def get_quick_reply_by_shortcut(
    shortcut: str, uow: UnitOfWork = Depends(get_uow)
):
    """
    Get quick reply by its shortcut.

    This is useful for quickly accessing a reply using its memorable shortcut.
    """
    async with uow:
        quick_reply = await uow.quick_replies.get_by_shortcut(shortcut)
        if not quick_reply:
            raise NotFoundError(
                detail=f"Quick reply with shortcut '{shortcut}' not found"
            )
        return quick_reply
=======
    repo = QuickReplyRepository(session)
    update_data = data.model_dump(exclude_unset=True)

    quick_reply = await repo.update(reply_id, update_data)
    if not quick_reply:
        raise NotFoundError(detail="Quick reply not found")

    await session.commit()
    await session.refresh(quick_reply)
    return quick_reply


@router.delete("/{reply_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quick_reply(reply_id: UUID, session: AsyncSession = Depends(get_session)):
    """
    Delete a quick reply.
    """
    repo = QuickReplyRepository(session)
    success = await repo.delete(reply_id)
    if not success:
        raise NotFoundError(detail="Quick reply not found")
    await session.commit()
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)


@router.get("/{reply_id}/text", response_model=QuickReplyTextResponse)
async def get_quick_reply_text(
    reply_id: UUID,
    language: str = Query(default="uk", description="Language code"),
<<<<<<< HEAD
    uow: UnitOfWork = Depends(get_uow),
=======
    session: AsyncSession = Depends(get_session),
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
):
    """
    Get text content for a quick reply in specified language.

    If the requested language is not available, returns content in the default language.
    """
<<<<<<< HEAD
    async with uow:
        quick_reply = await uow.quick_replies.get_by_id(reply_id)
        if not quick_reply:
            raise NotFoundError(detail="Quick reply not found")

        text = quick_reply.get_text(language)
        actual_language = (
            language
            if language in quick_reply.content
            else quick_reply.default_language
        )

        return QuickReplyTextResponse(text=text, language=actual_language)
=======
    repo = QuickReplyRepository(session)
    quick_reply = await repo.get_by_id(reply_id)
    if not quick_reply:
        raise NotFoundError(detail="Quick reply not found")

    text = quick_reply.get_text(language)
    actual_language = (
        language
        if language in quick_reply.content
        else quick_reply.default_language
    )

    return QuickReplyTextResponse(text=text, language=actual_language)
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)


@router.post("/{reply_id}/languages/{language}", response_model=QuickReplyResponse)
async def add_language_content(
    reply_id: UUID,
    language: str,
    content: str = Query(..., description="Text content for the language"),
<<<<<<< HEAD
    uow: UnitOfWork = Depends(get_uow),
=======
    session: AsyncSession = Depends(get_session),
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
):
    """
    Add or update content for a specific language in a quick reply.
    """
<<<<<<< HEAD
    async with uow:
        quick_reply = await uow.quick_replies.get_by_id(reply_id)
        if not quick_reply:
            raise NotFoundError(detail="Quick reply not found")

        # Update content with new language
        new_content = quick_reply.content.copy()
        new_content[language] = content

        updated_reply = await uow.quick_replies.update(
            reply_id, {"content": new_content}
        )
        await uow.commit()
        await uow.session.refresh(updated_reply)
        return updated_reply
=======
    repo = QuickReplyRepository(session)
    quick_reply = await repo.get_by_id(reply_id)
    if not quick_reply:
        raise NotFoundError(detail="Quick reply not found")

    # Update content with new language
    new_content = quick_reply.content.copy()
    new_content[language] = content

    updated_reply = await repo.update(
        reply_id, {"content": new_content}
    )
    await session.commit()
    await session.refresh(updated_reply)
    return updated_reply
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)


@router.delete("/{reply_id}/languages/{language}", response_model=QuickReplyResponse)
async def remove_language_content(
<<<<<<< HEAD
    reply_id: UUID, language: str, uow: UnitOfWork = Depends(get_uow)
=======
    reply_id: UUID, language: str, session: AsyncSession = Depends(get_session)
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
):
    """
    Remove content for a specific language from a quick reply.

    Cannot remove the default language content.
    """
<<<<<<< HEAD
    async with uow:
        quick_reply = await uow.quick_replies.get_by_id(reply_id)
        if not quick_reply:
            raise NotFoundError(detail="Quick reply not found")

        if language == quick_reply.default_language:
            raise BadRequestError(detail="Cannot remove default language content")

        if language not in quick_reply.content:
            raise BadRequestError(
                detail=f"Language '{language}' not found in quick reply content"
            )

        # Update content by removing the language
        new_content = quick_reply.content.copy()
        del new_content[language]

        updated_reply = await uow.quick_replies.update(
            reply_id, {"content": new_content}
        )
        await uow.commit()
        await uow.session.refresh(updated_reply)
        return updated_reply


@router.get("/stats/summary")
async def get_quick_reply_stats(uow: UnitOfWork = Depends(get_uow)):
=======
    repo = QuickReplyRepository(session)
    quick_reply = await repo.get_by_id(reply_id)
    if not quick_reply:
        raise NotFoundError(detail="Quick reply not found")

    if language == quick_reply.default_language:
        raise BadRequestError(detail="Cannot remove default language content")

    if language not in quick_reply.content:
        raise BadRequestError(
            detail=f"Language '{language}' not found in quick reply content"
        )

    # Update content by removing the language
    new_content = quick_reply.content.copy()
    del new_content[language]

    updated_reply = await repo.update(
        reply_id, {"content": new_content}
    )
    await session.commit()
    await session.refresh(updated_reply)
    return updated_reply


@router.get("/stats/summary")
async def get_quick_reply_stats(session: AsyncSession = Depends(get_session)):
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
    """
    Get statistics about quick replies.

    Returns total count, unique languages, and available languages list.
    """
<<<<<<< HEAD
    async with uow:
        total_count = await uow.quick_replies.count_all()
        all_replies = await uow.quick_replies.get_all()

        # Count unique languages
        languages = set()
        for reply in all_replies:
            languages.update(reply.content.keys())

        return {
            "total_quick_replies": total_count,
            "unique_languages": len(languages),
            "available_languages": sorted(list(languages)),
        }
=======
    repo = QuickReplyRepository(session)
    total_count = await repo.count_all()
    all_replies = await repo.get_all()

    # Count unique languages
    languages = set()
    for reply in all_replies:
        languages.update(reply.content.keys())

    return {
        "total_quick_replies": total_count,
        "unique_languages": len(languages),
        "available_languages": sorted(list(languages)),
    }
>>>>>>> ba322de (feat: implement Quick Replies feature with CRUD operations and API endpoints)
