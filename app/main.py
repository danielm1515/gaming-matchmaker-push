from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.database import engine, Base

# Import models to register with SQLAlchemy
from app.games.models import Game
from app.regions.models import Region
from app.players.models import Player, PlayerGame
from app.parties.models import Party, PartyMember
from app.chat.models import Message
from app.dm.models import DirectMessage
from app.notifications.models import PushSubscription
from app.discord.models import PartyDiscordChannel

# Routers
from app.auth.router import router as auth_router
from app.players.router import router as players_router
from app.games.router import router as games_router
from app.regions.router import router as regions_router
from app.parties.router import router as parties_router
from app.matching.router import router as matching_router
from app.chat.router import router as chat_router
from app.dm.router import router as dm_router
from app.notifications.router import router as notifications_router
from app.discord.router import router as discord_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrate: add password column to existing discord channel tables
        await conn.execute(
            text("ALTER TABLE party_discord_channels ADD COLUMN IF NOT EXISTS password VARCHAR(32)")
        )
    yield


app = FastAPI(title="Gaming Matchmaker API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,     prefix="/api/auth",     tags=["auth"])
app.include_router(players_router,  prefix="/api/players",  tags=["players"])
app.include_router(games_router,    prefix="/api/games",    tags=["games"])
app.include_router(regions_router,  prefix="/api/regions",  tags=["regions"])
app.include_router(parties_router,  prefix="/api/parties",  tags=["parties"])
app.include_router(matching_router, prefix="/api/match",    tags=["matching"])
app.include_router(chat_router,          prefix="/api",               tags=["chat"])
app.include_router(dm_router,            prefix="/api/dm",            tags=["dm"])
app.include_router(notifications_router, prefix="/api/notifications",  tags=["notifications"])
app.include_router(discord_router,       prefix="/api/parties",        tags=["discord"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
