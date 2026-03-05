import uuid
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.service import decode_token
from app.players.models import Player
from app.common.exceptions import UnauthorizedError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_player(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Player:
    payload = decode_token(token)
    player_id: str | None = payload.get("sub")
    if not player_id:
        raise UnauthorizedError("Invalid token")

    result = await db.execute(select(Player).where(Player.id == uuid.UUID(player_id)))
    player = result.scalar_one_or_none()
    if not player or not player.is_active:
        raise UnauthorizedError("Player not found or inactive")

    return player
