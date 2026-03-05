"""Seed the database with initial games and regions data."""
import asyncio
from app.database import AsyncSessionLocal, engine, Base
from app.games.models import Game
from app.regions.models import Region
from app.players.models import Player, PlayerGame  # noqa: F401 - needed for SQLAlchemy mapper resolution
from app.parties.models import Party, PartyMember  # noqa: F401
from app.chat.models import Message  # noqa: F401
from sqlalchemy import select


GAMES = [
    {"name": "Warzone", "slug": "warzone", "max_party_size": 4, "logo_url": "/logos/warzone.svg"},
    {"name": "Fortnite", "slug": "fortnite", "max_party_size": 4, "logo_url": "/logos/fortnite.svg"},
    {"name": "Apex Legends", "slug": "apex-legends", "max_party_size": 3, "logo_url": "/logos/apex.svg"},
    {"name": "Valorant", "slug": "valorant", "max_party_size": 5, "logo_url": "/logos/valorant.svg"},
    {"name": "League of Legends", "slug": "lol", "max_party_size": 5, "logo_url": "/logos/lol.svg"},
    {"name": "Overwatch 2", "slug": "overwatch-2", "max_party_size": 5, "logo_url": "/logos/ow2.svg"},
    {"name": "CS2", "slug": "cs2", "max_party_size": 5, "logo_url": "/logos/cs2.svg"},
    {"name": "Rocket League", "slug": "rocket-league", "max_party_size": 3, "logo_url": "/logos/rl.svg"},
]

REGIONS = [
    {"name": "North America", "code": "NA", "countries": ["US", "CA", "MX"]},
    {"name": "Europe West", "code": "EU", "countries": ["GB", "DE", "FR", "ES", "IT", "NL", "BE", "PT", "SE", "NO", "DK", "FI"]},
    {"name": "Europe East", "code": "EUNE", "countries": ["PL", "CZ", "SK", "HU", "RO", "BG", "HR", "RS", "UA", "GR"]},
    {"name": "Middle East", "code": "ME", "countries": ["IL", "SA", "AE", "TR", "EG", "JO", "KW", "QA", "BH", "OM"]},
    {"name": "Latin America", "code": "LATAM", "countries": ["BR", "AR", "CL", "CO", "PE", "VE", "UY", "PY", "BO", "EC"]},
    {"name": "Asia Pacific", "code": "APAC", "countries": ["JP", "KR", "CN", "TW", "HK", "SG", "TH", "MY", "ID", "PH"]},
    {"name": "South East Asia", "code": "SEA", "countries": ["VN", "MM", "KH", "LA", "BD", "LK"]},
    {"name": "Oceania", "code": "OCE", "countries": ["AU", "NZ"]},
    {"name": "Africa", "code": "AF", "countries": ["ZA", "NG", "KE", "GH", "ET", "EG"]},
    {"name": "Russia/CIS", "code": "RU", "countries": ["RU", "KZ", "BY", "AZ", "GE", "AM"]},
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Seed games
        for g in GAMES:
            existing = await db.execute(select(Game).where(Game.slug == g["slug"]))
            if not existing.scalar_one_or_none():
                db.add(Game(**g))
                print(f"Added game: {g['name']}")

        # Seed regions
        for r in REGIONS:
            existing = await db.execute(select(Region).where(Region.code == r["code"]))
            if not existing.scalar_one_or_none():
                db.add(Region(**r))
                print(f"Added region: {r['name']}")

        await db.commit()
        print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
