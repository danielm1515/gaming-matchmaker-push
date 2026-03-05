import uuid
import secrets
import string
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.dependencies import get_current_player
from app.players.models import Player
from app.parties.models import Party
from app.discord.models import PartyDiscordChannel
from app.discord.schemas import DiscordChannelResponse
from app.discord.service import create_party_channels, delete_channel
from app.common.exceptions import NotFoundError, ForbiddenError, ConflictError, BadRequestError
from app.config import settings

router = APIRouter()


@router.post("/{party_id}/discord", response_model=DiscordChannelResponse, status_code=201)
async def create_discord_channel(
    party_id: uuid.UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a temporary Discord text + voice channel for this party session.
    Only the party leader can do this. Only one channel per party.
    Requires DISCORD_BOT_TOKEN and DISCORD_GUILD_ID to be set in .env.
    """
    if not settings.DISCORD_BOT_TOKEN or not settings.DISCORD_GUILD_ID:
        raise BadRequestError("Discord integration is not configured on this server.")

    party = await db.get(Party, party_id)
    if not party:
        raise NotFoundError("Party")
    if party.leader_id != current_player.id:
        raise ForbiddenError("Only the party leader can create a Discord channel.")

    # Check if already exists
    existing = await db.execute(
        select(PartyDiscordChannel).where(PartyDiscordChannel.party_id == party_id)
    )
    if existing.scalar_one_or_none():
        raise ConflictError("A Discord channel already exists for this party.")

    # Load game name for the channel name
    await db.refresh(party, ["game"])
    game_name = party.game.name if party.game else "party"
    party_name = party.name or ""

    try:
        result = await create_party_channels(party_name, game_name)
    except Exception as e:
        raise BadRequestError(f"Failed to create Discord channel: {e}")

    alphabet = string.ascii_letters + string.digits
    channel_password = ''.join(secrets.choice(alphabet) for _ in range(12))

    record = PartyDiscordChannel(
        party_id=party_id,
        text_channel_id=result["text_channel_id"],
        voice_channel_id=result["voice_channel_id"],
        invite_url=result["invite_url"],
        password=channel_password,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/{party_id}/discord", response_model=DiscordChannelResponse)
async def get_discord_channel(
    party_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the Discord channel info for a party (if one exists)."""
    result = await db.execute(
        select(PartyDiscordChannel).where(PartyDiscordChannel.party_id == party_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise NotFoundError("Discord channel")
    return record


@router.delete("/{party_id}/discord", status_code=204)
async def delete_discord_channel(
    party_id: uuid.UUID,
    current_player: Player = Depends(get_current_player),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete the Discord channels for this party (leader only).
    Called automatically when a party is disbanded.
    """
    party = await db.get(Party, party_id)
    if not party:
        raise NotFoundError("Party")
    if party.leader_id != current_player.id:
        raise ForbiddenError("Only the party leader can delete the Discord channel.")

    result = await db.execute(
        select(PartyDiscordChannel).where(PartyDiscordChannel.party_id == party_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise NotFoundError("Discord channel")

    # Delete both channels from Discord
    await delete_channel(record.text_channel_id)
    if record.voice_channel_id:
        await delete_channel(record.voice_channel_id)

    await db.delete(record)
