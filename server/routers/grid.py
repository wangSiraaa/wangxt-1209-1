from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..deps import get_current_user, require_role, write_audit
from ..models import (
    AuditAction, AuditEntity, Defect, GridConnection, GridStatus, Inspection,
    Turbine, User,
)
from ..schemas import GridConnectionOut

router = APIRouter()

GRID_LOAD_OPTIONS = (
    selectinload(GridConnection.turbine),
    selectinload(GridConnection.defect).selectinload(Defect.photo),
    selectinload(GridConnection.defect).selectinload(Defect.annotator),
    selectinload(GridConnection.defect).selectinload(Defect.inspection).selectinload(Inspection.turbine),
    selectinload(GridConnection.defect).selectinload(Defect.inspection).selectinload(Inspection.inspector),
    selectinload(GridConnection.defect).selectinload(Defect.inspection).selectinload(Inspection.route_plan),
)


@router.get("/grid-connections", response_model=list[GridConnectionOut])
async def list_grid_connections(
    turbine_id: UUID | None = Query(None),
    status: GridStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(GridConnection)
        .options(*GRID_LOAD_OPTIONS)
        .order_by(GridConnection.created_at)
    )
    if turbine_id:
        stmt = stmt.where(GridConnection.turbine_id == turbine_id)
    if status:
        stmt = stmt.where(GridConnection.status == status)
    result = await db.execute(stmt)
    return result.scalars().unique().all()


@router.post("/grid-connections/{grid_id}/confirm", response_model=GridConnectionOut)
async def confirm_grid(
    grid_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "supervisor")

    result = await db.execute(
        select(GridConnection)
        .options(*GRID_LOAD_OPTIONS)
        .where(GridConnection.id == grid_id)
    )
    grid = result.scalar_one_or_none()
    if not grid:
        raise HTTPException(status_code=404, detail="并网记录不存在")

    if grid.status == GridStatus.frozen:
        raise HTTPException(
            status_code=423,
            detail=f"并网已冻结，不能确认。冻结原因：{grid.frozen_reason or '未知'}",
        )
    if grid.status == GridStatus.confirmed:
        raise HTTPException(status_code=400, detail="并网已确认，无需重复操作")

    grid.status = GridStatus.confirmed
    grid.confirmed_at = datetime.utcnow()
    grid.confirmed_by = current_user.id

    if grid.turbine:
        grid.turbine.status = "operating"

    await write_audit(
        db, AuditEntity.grid, grid.id, AuditAction.confirmed, current_user,
        detail={"turbine_id": str(grid.turbine_id)},
    )
    await db.commit()
    result = await db.execute(
        select(GridConnection)
        .options(*GRID_LOAD_OPTIONS)
        .where(GridConnection.id == grid_id)
    )
    return result.scalar_one()
