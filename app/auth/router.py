from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.auth.service import hash_password, verify_password, create_access_token
from app.players.models import Player
from app.common.exceptions import ConflictError, UnauthorizedError

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check uniqueness
    existing = await db.execute(
        select(Player).where(
            (Player.email == data.email) | (Player.username == data.username)
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Email or username already taken")

    player = Player(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        country_code=data.country_code,
    )
    db.add(player)
    await db.flush()
    await db.refresh(player)

    token = create_access_token({"sub": str(player.id)})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Player).where(Player.email == data.email))
    player = result.scalar_one_or_none()

    if not player or not verify_password(data.password, player.password_hash):
        raise UnauthorizedError("Invalid email or password")

    token = create_access_token({"sub": str(player.id)})
    return TokenResponse(access_token=token)
