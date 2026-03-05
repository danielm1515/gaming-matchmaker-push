from fastapi import WebSocket
import asyncio


class ConnectionManager:
    def __init__(self):
        # party_id (str) -> {player_id (str) -> WebSocket}
        self.active_connections: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, party_id: str, player_id: str):
        await websocket.accept()
        if party_id not in self.active_connections:
            self.active_connections[party_id] = {}
        self.active_connections[party_id][player_id] = websocket

    def disconnect(self, party_id: str, player_id: str):
        if party_id in self.active_connections:
            self.active_connections[party_id].pop(player_id, None)
            if not self.active_connections[party_id]:
                del self.active_connections[party_id]

    async def broadcast_to_party(self, party_id: str, message: dict):
        if party_id not in self.active_connections:
            return
        dead: list[str] = []
        for pid, ws in self.active_connections[party_id].items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(pid)
        for pid in dead:
            self.active_connections[party_id].pop(pid, None)

    def get_online_count(self, party_id: str) -> int:
        return len(self.active_connections.get(party_id, {}))


class GlobalPlayerManager:
    """Manages per-player WebSocket connections for presence, DMs, and notifications."""

    def __init__(self):
        # player_id (str) -> WebSocket
        self.connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, player_id: str):
        await websocket.accept()
        self.connections[player_id] = websocket

    def disconnect(self, player_id: str):
        self.connections.pop(player_id, None)

    async def send_to_player(self, player_id: str, message: dict) -> bool:
        ws = self.connections.get(player_id)
        if ws:
            try:
                await ws.send_json(message)
                return True
            except Exception:
                self.connections.pop(player_id, None)
        return False

    async def broadcast(self, message: dict):
        dead: list[str] = []
        for pid, ws in self.connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(pid)
        for pid in dead:
            self.connections.pop(pid, None)

    def is_online(self, player_id: str) -> bool:
        return player_id in self.connections

    def online_player_ids(self) -> list[str]:
        return list(self.connections.keys())


manager = ConnectionManager()
global_manager = GlobalPlayerManager()
