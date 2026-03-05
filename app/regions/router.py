from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.regions.models import Region
from app.regions.schemas import RegionResponse

router = APIRouter()


@router.get("", response_model=list[RegionResponse])
async def list_regions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Region).order_by(Region.name))
    return result.scalars().all()
