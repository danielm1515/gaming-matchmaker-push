import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.auth.dependencies import get_current_player
from app.parties.models import Party, PartyMember
from app.parties.schemas import PartyResponse, PartyCreate, PartyUpdate
from app.players.models import Player, PlayerGame
from app.games.models import Game
from app.regions.models import Region
from app.chat.models import Message
from app.chat.schemas import MessageResponse
from app.chat.manager import manager, global_manager
from app.common.exceptions import NotFoundError, ForbiddenError, ConflictError, BadRequestError
from app.common.enums import PartyStatus, SkillLevel, SKILL_ORDER, MessageType

router = APIRouter()


def party_query():
    return select(Party).options(
        selectinload(Party.game),
        selectinload(Party.region),
        selectinload(Party.leader).selectinload(Player.region),
        selectinload(Party.leader).selectinload(Player.player_games).selectinload(PlayerGame.game),
        selectinload(Party.members).selectinload(PartyMember.player).selectinload(Player.region),
        selectinload(Party.members).selectinload(PartyMember.player).selectinload(Player.player_games).selectinload(PlayerGame.game),
    )


@router.get("", response_model=list[PartyResponse])
async def list_parties(
    game_id: uuid.UUID | None = Query(None),
    region_code: str | None = Query(None),
    skill_level: SkillLevel | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = party_query().where(Party.status == PartyStatus.OPEN, Party.is_public == True)

    if game_id:
        q = q.where(Party.game_id == game_id)
    if region_code:
        region_result = await db.execute(select(Region).where(Region.code == region_code.upper()))
        region = region_result.scalar_one_or_none()
        if region:
            q = q.where(Party.region_id == region.id)
    if skill_level:
        skill_rank = SKILL_ORDER[skill_level]
        q = q.where(
            SKILL_ORDER[Party.min_skill] <= skill_rank,
            SKILL_ORDER[Party.max_skill] >= skill_rank,
        )

    q = q.order_by(Party.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=PartyResponse, status_code=201)
async def create_party(
    data: PartyCreate,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    game = await db.get(Game, data.game_id)
    if not game:
        raise NotFoundError("Game")

    region = await db.get(Region, data.region_id)
    if not region:
        raise NotFoundError("Region")

    party = Party(
        game_id=data.game_id,
        region_id=data.region_id,
        leader_id=current_player.id,
        name=data.name,
        max_size=min(data.max_size, game.max_party_size),
        min_skill=data.min_skill,
        max_skill=data.max_skill,
        is_public=data.is_public,
    )
    db.add(party)
    await db.flush()

    member = PartyMember(party_id=party.id, player_id=current_player.id)
    db.add(member)
    await db.flush()

    result = await db.execute(party_query().where(Party.id == party.id))
    return result.scalar_one()


@router.get("/{party_id}", response_model=PartyResponse)
async def get_party(party_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(party_query().where(Party.id == party_id))
    party = result.scalar_one_or_none()
    if not party:
        raise NotFoundError("Party")
    return party


@router.put("/{party_id}", response_model=PartyResponse)
async def update_party(
    party_id: uuid.UUID,
    data: PartyUpdate,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(party_query().where(Party.id == party_id))
    party = result.scalar_one_or_none()
    if not party:
        raise NotFoundError("Party")
    if party.leader_id != current_player.id:
        raise ForbiddenError("Only the party leader can update it")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(party, field, value)
    party.updated_at = datetime.utcnow()
    await db.flush()

    result2 = await db.execute(party_query().where(Party.id == party_id))
    return result2.scalar_one()


@router.post("/{party_id}/join", response_model=PartyResponse)
async def join_party(
    party_id: uuid.UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(party_query().where(Party.id == party_id))
    party = result.scalar_one_or_none()
    if not party:
        raise NotFoundError("Party")
    if party.status != PartyStatus.OPEN:
        raise BadRequestError("Party is not open for joining")

    member_ids = [m.player_id for m in party.members]
    if current_player.id in member_ids:
        raise ConflictError("You are already in this party")
    if len(party.members) >= party.max_size:
        raise BadRequestError("Party is full")

    player_skill_rank = SKILL_ORDER[current_player.skill_level]
    if not (SKILL_ORDER[party.min_skill] <= player_skill_rank <= SKILL_ORDER[party.max_skill]):
        raise BadRequestError("Your skill level does not meet this party's requirements")

    member = PartyMember(party_id=party_id, player_id=current_player.id)
    db.add(member)
    await db.flush()

    # Update party status if full
    updated_result = await db.execute(party_query().where(Party.id == party_id))
    updated_party = updated_result.scalar_one()
    if len(updated_party.members) >= updated_party.max_size:
        updated_party.status = PartyStatus.FULL
        await db.flush()

    final_result = await db.execute(party_query().where(Party.id == party_id))
    return final_result.scalar_one()


@router.post("/{party_id}/leave", response_model=PartyResponse)
async def leave_party(
    party_id: uuid.UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(party_query().where(Party.id == party_id))
    party = result.scalar_one_or_none()
    if not party:
        raise NotFoundError("Party")

    member_result = await db.execute(
        select(PartyMember).where(
            (PartyMember.party_id == party_id) & (PartyMember.player_id == current_player.id)
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise BadRequestError("You are not in this party")

    pid_str = str(party_id)

    if party.leader_id == current_player.id:
        remaining = [m for m in party.members if m.player_id != current_player.id]

        if not remaining:
            # Only member — disband
            await db.delete(member)
            party.status = PartyStatus.DISBANDED
            await db.flush()
            await manager.broadcast_to_party(pid_str, {
                "type": MessageType.SYSTEM.value,
                "content": f"{current_player.username} left. Party has been disbanded.",
                "sender": None,
                "sent_at": datetime.utcnow().isoformat(),
            })
        else:
            # Transfer leadership to earliest-joined remaining member
            next_member = min(remaining, key=lambda m: m.joined_at)
            new_leader = await db.get(Player, next_member.player_id)
            await db.delete(member)
            party.leader_id = next_member.player_id
            if party.status == PartyStatus.FULL:
                party.status = PartyStatus.OPEN
            await db.flush()

            await manager.broadcast_to_party(pid_str, {
                "type": MessageType.SYSTEM.value,
                "content": f"{current_player.username} left. {new_leader.username} is now the leader.",
                "sender": None,
                "sent_at": datetime.utcnow().isoformat(),
            })
            await global_manager.send_to_player(str(next_member.player_id), {
                "type": "notification",
                "kind": "leader_transfer",
                "data": {"party_id": pid_str, "message": "You are now the party leader!"},
            })
    else:
        await db.delete(member)
        if party.status == PartyStatus.FULL:
            party.status = PartyStatus.OPEN
        await db.flush()

        await manager.broadcast_to_party(pid_str, {
            "type": MessageType.SYSTEM.value,
            "content": f"{current_player.username} left the party.",
            "sender": None,
            "sent_at": datetime.utcnow().isoformat(),
        })

    final_result = await db.execute(party_query().where(Party.id == party_id))
    return final_result.scalar_one()


@router.post("/{party_id}/kick/{player_id}", response_model=PartyResponse)
async def kick_member(
    party_id: uuid.UUID,
    player_id: uuid.UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(party_query().where(Party.id == party_id))
    party = result.scalar_one_or_none()
    if not party:
        raise NotFoundError("Party")
    if party.leader_id != current_player.id:
        raise ForbiddenError("Only the leader can kick members")
    if player_id == current_player.id:
        raise BadRequestError("You cannot kick yourself")

    member_result = await db.execute(
        select(PartyMember).where(
            (PartyMember.party_id == party_id) & (PartyMember.player_id == player_id)
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise NotFoundError("Player is not in this party")

    kicked_player = await db.get(Player, player_id)
    pid_str = str(party_id)

    await db.delete(member)
    if party.status == PartyStatus.FULL:
        party.status = PartyStatus.OPEN
    await db.flush()

    # Broadcast system message to party chat
    await manager.broadcast_to_party(pid_str, {
        "type": MessageType.SYSTEM.value,
        "content": f"{kicked_player.username} was kicked from the party.",
        "sender": None,
        "sent_at": datetime.utcnow().isoformat(),
    })

    # Notify kicked player via global WebSocket
    await global_manager.send_to_player(str(player_id), {
        "type": "notification",
        "kind": "kicked",
        "data": {"party_id": pid_str, "message": "You were kicked from the party."},
    })

    # Send browser push notification to kicked player
    from app.notifications.service import send_push_to_player
    await send_push_to_player(str(player_id), "Kicked from party", "You were removed from the party.")

    final_result = await db.execute(party_query().where(Party.id == party_id))
    return final_result.scalar_one()


@router.delete("/{party_id}", status_code=204)
async def disband_party(
    party_id: uuid.UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Party).where(Party.id == party_id))
    party = result.scalar_one_or_none()
    if not party:
        raise NotFoundError("Party")
    if party.leader_id != current_player.id:
        raise ForbiddenError("Only the leader can disband the party")

    # Clean up Discord channels if they exist
    from app.discord.models import PartyDiscordChannel
    from app.discord.service import delete_channel
    dc_result = await db.execute(
        select(PartyDiscordChannel).where(PartyDiscordChannel.party_id == party_id)
    )
    dc = dc_result.scalar_one_or_none()
    if dc:
        await delete_channel(dc.text_channel_id)
        if dc.voice_channel_id:
            await delete_channel(dc.voice_channel_id)

    party.status = PartyStatus.DISBANDED
    await db.flush()


@router.post("/{party_id}/ready", response_model=PartyResponse)
async def toggle_ready(
    party_id: uuid.UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    member_result = await db.execute(
        select(PartyMember).where(
            (PartyMember.party_id == party_id) & (PartyMember.player_id == current_player.id)
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise BadRequestError("You are not in this party")

    member.is_ready = not member.is_ready
    await db.flush()

    final_result = await db.execute(party_query().where(Party.id == party_id))
    return final_result.scalar_one()


@router.get("/{party_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    party_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Party).where(Party.id == party_id))
    if not result.scalar_one_or_none():
        raise NotFoundError("Party")

    msg_result = await db.execute(
        select(Message)
        .options(selectinload(Message.sender).selectinload(Player.region))
        .where(Message.party_id == party_id)
        .order_by(Message.sent_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return msg_result.scalars().all()
