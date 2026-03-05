from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.auth.dependencies import get_current_player
from app.players.models import Player
from app.notifications.models import PushSubscription
from app.config import settings

router = APIRouter()


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Return the VAPID public key for the frontend to use when subscribing."""
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe", status_code=201)
async def subscribe_push(
    data: PushSubscribeRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Register a browser push subscription for the current player."""
    existing = await db.execute(
        select(PushSubscription).where(
            PushSubscription.player_id == current_player.id,
            PushSubscription.endpoint == data.endpoint,
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Already subscribed"}

    sub = PushSubscription(
        player_id=current_player.id,
        endpoint=data.endpoint,
        p256dh=data.p256dh,
        auth=data.auth,
    )
    db.add(sub)
    return {"message": "Subscribed"}


@router.delete("/unsubscribe")
async def unsubscribe_push(
    endpoint: str,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """Remove a browser push subscription."""
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.player_id == current_player.id,
            PushSubscription.endpoint == endpoint,
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        await db.delete(sub)
    return {"message": "Unsubscribed"}
