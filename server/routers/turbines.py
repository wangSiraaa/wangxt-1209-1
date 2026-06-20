from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Turbine, TurbineStatus, User
from ..schemas import TurbineCreate, TurbineOut, TurbineUpdate

router = APIRouter()


@router.get("/turbines", response_model=list[TurbineOut])
async def list_turbines(
    status: TurbineStatus | None = Query(None),
    farm: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Turbine).order_by(Turbine.created_at.desc())
    if status:
        stmt = stmt.where(Turbine.status == status)
    if farm:
        stmt = stmt.where(Turbine.farm_name.ilike(f"%{farm}%"))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/turbines/{turbine_id}", response_model=TurbineOut)
async def get_turbine(turbine_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Turbine).where(Turbine.id == turbine_id))
    turbine = result.scalar_one_or_none()
    if not turbine:
        raise HTTPException(status_code=404, detail="机组不存在")
    return turbine


@router.post("/turbines", response_model=TurbineOut)
async def create_turbine(
    data: TurbineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "inspector", "supervisor")
    turbine = Turbine(**data.model_dump(), created_by=current_user.id)
    db.add(turbine)
    await db.commit()
    await db.refresh(turbine)
    return turbine


@router.put("/turbines/{turbine_id}", response_model=TurbineOut)
async def update_turbine(
    turbine_id: UUID,
    data: TurbineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "inspector", "supervisor")
    result = await db.execute(select(Turbine).where(Turbine.id == turbine_id))
    turbine = result.scalar_one_or_none()
    if not turbine:
        raise HTTPException(status_code=404, detail="机组不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(turbine, key, value)
    await db.commit()
    await db.refresh(turbine)
    return turbine
