from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:dm1234dm@localhost:5432/gamematcher"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://gaming-matchmaker-push-client.vercel.app",
        "https://gaming-matchmaker-push-client.vercel.app/auth",
        "https://gaming-matchmaker-push.onrender.com",
    ]

    # Web Push (VAPID) — generate once with: python generate_vapid_keys.py
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:admin@gaming-matchmaker.com"

    # Discord Bot — https://discord.com/developers/applications
    DISCORD_BOT_TOKEN: str = ""
    DISCORD_GUILD_ID: str = ""
    DISCORD_CATEGORY_ID: str = ""  # optional: put party channels under a category

    class Config:
        env_file = ".env"


settings = Settings()
