import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.dependencies import get_current_player
from app.players.models import Player
from app.matching.engine import find_matches
from app.matching.schemas import MatchResultResponse

router = APIRouter()


@router.get("/find", response_model=list[MatchResultResponse])
async def find_party_matches(
    game_id: uuid.UUID = Query(..., description="Game to find a party for"),
    max_skill_distance: int = Query(2, ge=0, le=5),
    limit: int = Query(10, ge=1, le=20),
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    results = await find_matches(
        player=current_player,
        game_id=game_id,
        db=db,
        max_skill_distance=max_skill_distance,
        limit=limit,
    )
    return [
        MatchResultResponse(
            party=r.party,
            match_score=r.match_score,
            region_score=r.region_score,
            skill_score=r.skill_score,
            fill_score=r.fill_score,
            availability_score=r.availability_score,
        )
        for r in results
    ]
