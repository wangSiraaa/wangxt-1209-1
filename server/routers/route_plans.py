from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import RoutePlan, User
from ..schemas import RoutePlanCreate, RoutePlanOut, RoutePlanUpdate

router = APIRouter()


@router.get("/route-plans", response_model=list[RoutePlanOut])
async def list_route_plans(
    turbine_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RoutePlan).order_by(RoutePlan.created_at.desc())
    if turbine_id:
        stmt = stmt.where(RoutePlan.turbine_id == turbine_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/route-plans", response_model=RoutePlanOut)
async def create_route_plan(
    data: RoutePlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "inspector")
    route_plan = RoutePlan(**data.model_dump(), created_by=current_user.id)
    db.add(route_plan)
    await db.commit()
    await db.refresh(route_plan)
    return route_plan


@router.put("/route-plans/{plan_id}", response_model=RoutePlanOut)
async def update_route_plan(
    plan_id: UUID,
    data: RoutePlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "inspector")
    result = await db.execute(select(RoutePlan).where(RoutePlan.id == plan_id))
    route_plan = result.scalar_one_or_none()
    if not route_plan:
        raise HTTPException(status_code=404, detail="航线计划不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(route_plan, key, value)
    await db.commit()
    await db.refresh(route_plan)
    return route_plan


@router.delete("/route-plans/{plan_id}")
async def delete_route_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "inspector")
    result = await db.execute(select(RoutePlan).where(RoutePlan.id == plan_id))
    route_plan = result.scalar_one_or_none()
    if not route_plan:
        raise HTTPException(status_code=404, detail="航线计划不存在")
    await db.delete(route_plan)
    await db.commit()
    return {"ok": True}
