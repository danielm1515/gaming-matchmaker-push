from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.games.models import Game
from app.games.schemas import GameResponse

router = APIRouter()


@router.get("", response_model=list[GameResponse])
async def list_games(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Game).where(Game.is_active == True).order_by(Game.name))
    return result.scalars().all()
