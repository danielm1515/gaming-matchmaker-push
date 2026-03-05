import json
import asyncio
from functools import partial
from app.config import settings


async def send_push_to_player(player_id: str, title: str, body: str, data: dict | None = None):
    """Send a Web Push notification to all browser subscriptions for a player."""
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return  # Push not configured

    try:
        from pywebpush import webpush, WebPushException
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.notifications.models import PushSubscription

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(PushSubscription).where(PushSubscription.player_id == player_id)
            )
            subscriptions = result.scalars().all()

        if not subscriptions:
            return

        payload = json.dumps({"title": title, "body": body, "data": data or {}})
        loop = asyncio.get_event_loop()

        for sub in subscriptions:
            sub_info = {
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            }
            try:
                fn = partial(
                    webpush,
                    subscription_info=sub_info,
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": settings.VAPID_SUBJECT},
                )
                await loop.run_in_executor(None, fn)
            except WebPushException as e:
                # Subscription expired or invalid — remove it
                if e.response and e.response.status_code in (404, 410):
                    async with AsyncSessionLocal() as db:
                        s = await db.get(PushSubscription, sub.id)
                        if s:
                            await db.delete(s)
                            await db.commit()
    except Exception:
        pass  # Never let push failures break the main request flow
