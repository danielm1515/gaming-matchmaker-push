"""Discord HTTP API helpers for managing temporary party channels."""
import httpx
from app.config import settings

DISCORD_API = "https://discord.com/api/v10"


def _headers() -> dict:
    return {"Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}", "Content-Type": "application/json"}


async def create_party_channels(party_name: str, game_name: str) -> dict:
    """
    Create a text + voice channel pair for a party session.
    Returns {"text_channel_id", "voice_channel_id", "invite_url"} or raises on failure.
    """
    guild_id = settings.DISCORD_GUILD_ID
    category_id = settings.DISCORD_CATEGORY_ID or None
    channel_name = _safe_name(f"{game_name}-{party_name}" if party_name else game_name)

    async with httpx.AsyncClient() as client:
        # Create text channel
        text_payload: dict = {
            "name": channel_name,
            "type": 0,  # GUILD_TEXT
        }
        if category_id:
            text_payload["parent_id"] = category_id

        r = await client.post(
            f"{DISCORD_API}/guilds/{guild_id}/channels",
            json=text_payload,
            headers=_headers(),
        )
        r.raise_for_status()
        text_channel = r.json()
        text_id = text_channel["id"]

        # Create voice channel
        voice_payload: dict = {
            "name": f"🎮 {channel_name}",
            "type": 2,  # GUILD_VOICE
        }
        if category_id:
            voice_payload["parent_id"] = category_id

        r = await client.post(
            f"{DISCORD_API}/guilds/{guild_id}/channels",
            json=voice_payload,
            headers=_headers(),
        )
        r.raise_for_status()
        voice_channel = r.json()
        voice_id = voice_channel["id"]

        # Create an invite for the text channel (24-hour, unlimited uses)
        r = await client.post(
            f"{DISCORD_API}/channels/{text_id}/invites",
            json={"max_age": 86400, "max_uses": 0, "unique": True},
            headers=_headers(),
        )
        r.raise_for_status()
        invite = r.json()
        invite_url = f"https://discord.gg/{invite['code']}"

    return {
        "text_channel_id": text_id,
        "voice_channel_id": voice_id,
        "invite_url": invite_url,
    }


async def delete_channel(channel_id: str) -> None:
    """Delete a Discord channel. Silently ignores 404 (already deleted)."""
    async with httpx.AsyncClient() as client:
        r = await client.delete(
            f"{DISCORD_API}/channels/{channel_id}",
            headers=_headers(),
        )
        if r.status_code not in (200, 204, 404):
            r.raise_for_status()


def _safe_name(name: str) -> str:
    """Convert to Discord-safe channel name (lowercase, hyphens, max 100 chars)."""
    import re
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\-_]", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name[:100] or "party-channel"
