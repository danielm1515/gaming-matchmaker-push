import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.auth.dependencies import get_current_player
from app.players.models import Player, PlayerGame
from app.players.schemas import PlayerResponse, PlayerUpdate, AddGameRequest
from app.games.models import Game
from app.regions.models import Region
from app.common.exceptions import NotFoundError, ConflictError, BadRequestError
from app.common.enums import SkillLevel, AvailabilityStatus

router = APIRouter()


def player_query():
    return select(Player).options(
        selectinload(Player.region),
        selectinload(Player.player_games).selectinload(PlayerGame.game),
    )


@router.get("/me", response_model=PlayerResponse)
async def get_me(current_player: Player = Depends(get_current_player), db: AsyncSession = Depends(get_db)):
    result = await db.execute(player_query().where(Player.id == current_player.id))
    player = result.scalar_one_or_none()
    if not player:
        raise NotFoundError("Player")
    # Update last_seen
    player.last_seen_at = datetime.utcnow()
    return player


@router.put("/me", response_model=PlayerResponse)
async def update_me(
    data: PlayerUpdate,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(player_query().where(Player.id == current_player.id))
    player = result.scalar_one_or_none()
    if not player:
        raise NotFoundError("Player")

    update_data = data.model_dump(exclude_none=True)

    if "region_id" in update_data:
        region = await db.get(Region, update_data["region_id"])
        if not region:
            raise NotFoundError("Region")

    for field, value in update_data.items():
        setattr(player, field, value)

    player.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(player)

    result2 = await db.execute(player_query().where(Player.id == player.id))
    return result2.scalar_one()


@router.get("", response_model=list[PlayerResponse])
async def list_players(
    game_id: uuid.UUID | None = Query(None),
    region_code: str | None = Query(None),
    country_code: str | None = Query(None),
    skill_level: SkillLevel | None = Query(None),
    availability: AvailabilityStatus | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = player_query().where(Player.is_active == True)

    if skill_level:
        q = q.where(Player.skill_level == skill_level)
    if availability:
        q = q.where(Player.availability == availability)
    if country_code:
        q = q.where(Player.country_code == country_code.upper())
    if region_code:
        region_result = await db.execute(select(Region).where(Region.code == region_code.upper()))
        region = region_result.scalar_one_or_none()
        if region:
            q = q.where(Player.region_id == region.id)
    if game_id:
        q = q.where(Player.player_games.any(PlayerGame.game_id == game_id))

    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{player_id}", response_model=PlayerResponse)
async def get_player(player_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(player_query().where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        raise NotFoundError("Player")
    return player


@router.post("/me/games", response_model=PlayerResponse)
async def add_game(
    data: AddGameRequest,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    game = await db.get(Game, data.game_id)
    if not game:
        raise NotFoundError("Game")

    existing = await db.execute(
        select(PlayerGame).where(
            (PlayerGame.player_id == current_player.id) & (PlayerGame.game_id == data.game_id)
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Game already added to your profile")

    pg = PlayerGame(
        player_id=current_player.id,
        game_id=data.game_id,
        skill_level=data.skill_level,
        hours_played=data.hours_played,
    )
    db.add(pg)
    await db.flush()

    result = await db.execute(player_query().where(Player.id == current_player.id))
    return result.scalar_one()


@router.delete("/me/games/{game_id}", response_model=PlayerResponse)
async def remove_game(
    game_id: uuid.UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlayerGame).where(
            (PlayerGame.player_id == current_player.id) & (PlayerGame.game_id == game_id)
        )
    )
    pg = result.scalar_one_or_none()
    if not pg:
        raise NotFoundError("Game on your profile")

    await db.delete(pg)
    await db.flush()

    result2 = await db.execute(player_query().where(Player.id == current_player.id))
    return result2.scalar_one()
