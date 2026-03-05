import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.auth.dependencies import get_current_player
from app.players.models import Player
from app.dm.models import DirectMessage
from app.dm.schemas import DMResponse, ConversationSummary
from app.common.exceptions import NotFoundError

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationSummary])
async def get_conversations(
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """List all DM conversations for the current player, sorted by most recent."""
    result = await db.execute(
        select(DirectMessage)
        .options(selectinload(DirectMessage.sender), selectinload(DirectMessage.receiver))
        .where(
            or_(
                DirectMessage.sender_id == current_player.id,
                DirectMessage.receiver_id == current_player.id,
            )
        )
        .order_by(DirectMessage.sent_at.desc())
    )
    messages = result.scalars().all()

    # Group by conversation partner (keep only the latest message per partner)
    seen: dict[str, ConversationSummary] = {}
    for msg in messages:
        is_sender = msg.sender_id == current_player.id
        partner = msg.receiver if is_sender else msg.sender
        partner_id = str(partner.id)
        if partner_id not in seen:
            unread = sum(
                1 for m in messages
                if str(m.sender_id) == partner_id
                and m.receiver_id == current_player.id
                and not m.is_read
            )
            seen[partner_id] = ConversationSummary(
                partner=partner,
                last_message=msg.content,
                last_sent_at=msg.sent_at,
                unread_count=unread,
            )
    return list(seen.values())


@router.get("/{player_id}", response_model=list[DMResponse])
async def get_dm_history(
    player_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Get DM history between current player and another player."""
    other = await db.get(Player, player_id)
    if not other:
        raise NotFoundError("Player")

    result = await db.execute(
        select(DirectMessage)
        .options(selectinload(DirectMessage.sender), selectinload(DirectMessage.receiver))
        .where(
            or_(
                and_(
                    DirectMessage.sender_id == current_player.id,
                    DirectMessage.receiver_id == player_id,
                ),
                and_(
                    DirectMessage.sender_id == player_id,
                    DirectMessage.receiver_id == current_player.id,
                ),
            )
        )
        .order_by(DirectMessage.sent_at.asc())
        .limit(limit)
        .offset(offset)
    )
    messages = result.scalars().all()

    # Mark incoming messages as read
    for msg in messages:
        if msg.receiver_id == current_player.id and not msg.is_read:
            msg.is_read = True
    await db.commit()

    return messages
