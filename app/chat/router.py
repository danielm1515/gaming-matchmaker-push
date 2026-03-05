import uuid
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.auth.service import decode_token
from app.players.models import Player
from app.parties.models import Party, PartyMember
from app.chat.models import Message
from app.chat.manager import manager, global_manager
from app.common.enums import MessageType, AvailabilityStatus

router = APIRouter()


async def _get_player_by_id(player_id: str, db: AsyncSession) -> Player | None:
    result = await db.execute(select(Player).where(Player.id == uuid.UUID(player_id)))
    return result.scalar_one_or_none()


@router.websocket("/ws/party/{party_id}")
async def party_websocket(
    websocket: WebSocket,
    party_id: uuid.UUID,
    token: str = Query(...),
):
    # Authenticate
    payload = decode_token(token)
    player_id_str: str | None = payload.get("sub")
    if not player_id_str:
        await websocket.close(code=4001)
        return

    async with AsyncSessionLocal() as db:
        player = await _get_player_by_id(player_id_str, db)
        if not player:
            await websocket.close(code=4001)
            return

        # Verify party membership
        result = await db.execute(
            select(PartyMember).where(
                (PartyMember.party_id == party_id) & (PartyMember.player_id == player.id)
            )
        )
        if not result.scalar_one_or_none():
            await websocket.close(code=4003)
            return

        await manager.connect(websocket, str(party_id), str(player.id))

        # Broadcast JOIN system message
        join_msg = {
            "type": MessageType.JOIN.value,
            "content": f"{player.username} joined the party",
            "sender": {"id": str(player.id), "username": player.username, "avatar_url": player.avatar_url},
            "sent_at": datetime.utcnow().isoformat(),
        }
        await manager.broadcast_to_party(str(party_id), join_msg)

        try:
            while True:
                data = await websocket.receive_json()
                content = str(data.get("content", "")).strip()
                if not content:
                    continue

                # Persist message
                message = Message(
                    party_id=party_id,
                    sender_id=player.id,
                    content=content,
                    type=MessageType.TEXT,
                )
                db.add(message)
                await db.commit()
                await db.refresh(message)

                # Broadcast to all party members
                out = {
                    "id": str(message.id),
                    "type": MessageType.TEXT.value,
                    "content": content,
                    "sender": {
                        "id": str(player.id),
                        "username": player.username,
                        "avatar_url": player.avatar_url,
                    },
                    "party_id": str(party_id),
                    "sent_at": message.sent_at.isoformat(),
                }
                await manager.broadcast_to_party(str(party_id), out)

        except WebSocketDisconnect:
            manager.disconnect(str(party_id), str(player.id))
            leave_msg = {
                "type": MessageType.LEAVE.value,
                "content": f"{player.username} left the party",
                "sender": {"id": str(player.id), "username": player.username, "avatar_url": player.avatar_url},
                "sent_at": datetime.utcnow().isoformat(),
            }
            await manager.broadcast_to_party(str(party_id), leave_msg)
        except Exception:
            manager.disconnect(str(party_id), str(player.id))


@router.websocket("/ws/player")
async def player_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Global per-player WebSocket for:
    - Realtime presence updates (broadcast to all connected clients)
    - Direct messages (delivered to target player if online)
    - Notifications

    Client sends JSON:
      {"type": "status", "availability": "LOOKING_FOR_PARTY"}
      {"type": "dm", "to_player_id": "<uuid>", "content": "..."}

    Server sends JSON:
      {"type": "presence", "player_id": "...", "username": "...", "avatar_url": "...", "availability": "..."}
      {"type": "dm", "id": "...", "from": {...}, "content": "...", "sent_at": "..."}
      {"type": "dm_sent", ...}   -- echo back to sender on success
      {"type": "notification", "kind": "...", "data": {...}}
    """
    payload = decode_token(token)
    player_id_str: str | None = payload.get("sub")
    if not player_id_str:
        await websocket.close(code=4001)
        return

    async with AsyncSessionLocal() as db:
        player = await _get_player_by_id(player_id_str, db)
        if not player:
            await websocket.close(code=4001)
            return

        await global_manager.connect(websocket, str(player.id))

        # Set ONLINE if was OFFLINE
        if player.availability == AvailabilityStatus.OFFLINE:
            player.availability = AvailabilityStatus.ONLINE
        player.last_seen_at = datetime.utcnow()
        await db.commit()

        # Broadcast this player's presence to everyone
        await global_manager.broadcast({
            "type": "presence",
            "player_id": str(player.id),
            "username": player.username,
            "avatar_url": player.avatar_url,
            "availability": player.availability.value,
        })

        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "status":
                    new_status = data.get("availability", "")
                    try:
                        player.availability = AvailabilityStatus(new_status)
                        await db.commit()
                        await global_manager.broadcast({
                            "type": "presence",
                            "player_id": str(player.id),
                            "username": player.username,
                            "avatar_url": player.avatar_url,
                            "availability": player.availability.value,
                        })
                    except ValueError:
                        pass

                elif msg_type == "dm":
                    # Lazy import to avoid circular imports
                    from app.dm.models import DirectMessage

                    to_id_raw = data.get("to_player_id", "")
                    content = str(data.get("content", "")).strip()
                    if not to_id_raw or not content:
                        continue
                    try:
                        to_uuid = uuid.UUID(to_id_raw)
                    except ValueError:
                        continue

                    receiver = await db.get(Player, to_uuid)
                    if not receiver:
                        continue

                    dm = DirectMessage(
                        sender_id=player.id,
                        receiver_id=to_uuid,
                        content=content,
                    )
                    db.add(dm)
                    await db.commit()
                    await db.refresh(dm)

                    dm_payload = {
                        "type": "dm",
                        "id": str(dm.id),
                        "from": {
                            "id": str(player.id),
                            "username": player.username,
                            "avatar_url": player.avatar_url,
                        },
                        "to_player_id": str(to_uuid),
                        "content": content,
                        "sent_at": dm.sent_at.isoformat(),
                    }
                    # Deliver to receiver if online
                    await global_manager.send_to_player(str(to_uuid), dm_payload)
                    # Echo back to sender as confirmation
                    await global_manager.send_to_player(str(player.id), {**dm_payload, "type": "dm_sent"})

        except WebSocketDisconnect:
            global_manager.disconnect(str(player.id))
            player.availability = AvailabilityStatus.OFFLINE
            player.last_seen_at = datetime.utcnow()
            await db.commit()
            await global_manager.broadcast({
                "type": "presence",
                "player_id": str(player.id),
                "username": player.username,
                "avatar_url": player.avatar_url,
                "availability": AvailabilityStatus.OFFLINE.value,
            })
        except Exception:
            global_manager.disconnect(str(player.id))
