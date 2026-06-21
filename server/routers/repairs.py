from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..deps import get_current_user, require_role, write_audit
from ..models import (
    AuditAction, AuditEntity, AuditTrace, BladePhoto, Defect,
    GridConnection, GridStatus, Inspection, RepairOrder, RepairStatus,
    Turbine, User,
)
from .defects import DEFECT_LOAD_OPTIONS
from ..schemas import (
    BladePhotoOut, DefectOut, RepairOrderClose, RepairOrderCreate,
    RepairOrderOut, TraceResult,
)

router = APIRouter()

REPAIR_LOAD_OPTIONS = (
    selectinload(RepairOrder.defect).selectinload(Defect.photo),
    selectinload(RepairOrder.defect).selectinload(Defect.annotator),
    selectinload(RepairOrder.defect).selectinload(Defect.inspection).selectinload(Inspection.turbine),
    selectinload(RepairOrder.defect).selectinload(Defect.inspection).selectinload(Inspection.inspector),
    selectinload(RepairOrder.defect).selectinload(Defect.inspection).selectinload(Inspection.route_plan),
    selectinload(RepairOrder.turbine),
    selectinload(RepairOrder.supervisor),
)


async def _reload_repair(db: AsyncSession, repair_id: UUID) -> RepairOrder:
    result = await db.execute(
        select(RepairOrder).options(*REPAIR_LOAD_OPTIONS).where(RepairOrder.id == repair_id)
    )
    r = result.scalar_one()
    if r.defect and r.defect.inspection:
        r.defect.turbine = r.defect.inspection.turbine
    return r


@router.get("/repair-orders", response_model=list[RepairOrderOut])
async def list_repair_orders(
    turbine_id: UUID | None = Query(None),
    status: RepairStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(RepairOrder)
        .options(*REPAIR_LOAD_OPTIONS)
        .order_by(RepairOrder.created_at.desc())
    )
    if turbine_id:
        stmt = stmt.where(RepairOrder.turbine_id == turbine_id)
    if status:
        stmt = stmt.where(RepairOrder.status == status)

    result = await db.execute(stmt)
    repairs = result.scalars().unique().all()
    for r in repairs:
        if r.defect and r.defect.inspection:
            r.defect.turbine = r.defect.inspection.turbine
    return repairs


@router.post("/repair-orders", response_model=RepairOrderOut)
async def create_repair_order(
    data: RepairOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "supervisor")

    defect_result = await db.execute(
        select(Defect).where(Defect.id == data.defect_id)
    )
    defect = defect_result.scalar_one_or_none()
    if not defect:
        raise HTTPException(status_code=404, detail="缺陷不存在")

    insp_result = await db.execute(select(Inspection).where(Inspection.id == defect.inspection_id))
    insp = insp_result.scalar_one_or_none()
    if not insp:
        raise HTTPException(status_code=404, detail="巡检不存在")

    existing = await db.execute(
        select(RepairOrder).where(
            RepairOrder.defect_id == data.defect_id,
            RepairOrder.status != RepairStatus.closed,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该缺陷已有未关闭的维修单")

    repair = RepairOrder(
        defect_id=data.defect_id,
        turbine_id=insp.turbine_id,
        inspection_id=insp.id,
        decision=data.decision,
        status=RepairStatus.in_progress if data.decision == "repair" else RepairStatus.open,
        supervisor_id=current_user.id,
    )
    db.add(repair)
    await db.flush()

    await write_audit(
        db, AuditEntity.repair_order, repair.id, AuditAction.created, current_user,
        detail={"defect_id": str(data.defect_id), "decision": data.decision.value},
    )
    await db.commit()
    return await _reload_repair(db, repair.id)


@router.put("/repair-orders/{repair_id}/close", response_model=RepairOrderOut)
async def close_repair_order(
    repair_id: UUID,
    data: RepairOrderClose,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "supervisor")

    result = await db.execute(select(RepairOrder).where(RepairOrder.id == repair_id))
    repair = result.scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=404, detail="维修单不存在")
    if repair.status == RepairStatus.closed:
        raise HTTPException(status_code=400, detail="维修单已关闭")

    repair.status = RepairStatus.closed
    repair.closed_at = datetime.utcnow()
    repair.closure_notes = data.closure_notes

    from sqlalchemy import desc

    grid_result = await db.execute(
        select(GridConnection)
        .where(
            GridConnection.turbine_id == repair.turbine_id,
            GridConnection.status != GridStatus.confirmed,
        )
        .order_by(desc(GridConnection.created_at))
    )
    grid = grid_result.scalar_one_or_none()
    if grid and grid.status == GridStatus.frozen and grid.frozen_by_defect_id == repair.defect_id:
        grid.status = GridStatus.pending
        grid.frozen_reason = None
        grid.frozen_by_defect_id = None
        await write_audit(
            db, AuditEntity.grid, grid.id, AuditAction.unfrozen, current_user,
            detail={"repair_order_id": str(repair_id), "defect_id": str(repair.defect_id)},
        )

    defect_result = await db.execute(select(Defect).where(Defect.id == repair.defect_id))
    defect = defect_result.scalar_one_or_none()
    if defect:
        defect.status = "resolved"
        defect.updated_at = datetime.utcnow()

    await write_audit(
        db, AuditEntity.repair_order, repair.id, AuditAction.closed, current_user,
        detail={"closure_notes": data.closure_notes},
    )
    await db.commit()
    return await _reload_repair(db, repair.id)


@router.get("/repair-orders/{repair_id}/trace", response_model=TraceResult)
async def get_trace(repair_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RepairOrder)
        .options(*REPAIR_LOAD_OPTIONS)
        .where(RepairOrder.id == repair_id)
    )
    repair = result.scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=404, detail="维修单不存在")
    if repair.defect and repair.defect.inspection:
        repair.defect.turbine = repair.defect.inspection.turbine

    photos_result = await db.execute(
        select(BladePhoto).where(BladePhoto.inspection_id == repair.inspection_id)
    )
    photos = photos_result.scalars().all()

    defects_result = await db.execute(
        select(Defect)
        .options(*DEFECT_LOAD_OPTIONS)
        .where(Defect.inspection_id == repair.inspection_id)
    )
    defects = defects_result.scalars().unique().all()
    for d in defects:
        d.turbine = d.inspection.turbine if d.inspection else None

    timeline_result = await db.execute(
        select(AuditTrace)
        .options(selectinload(AuditTrace.operator))
        .where(
            (AuditTrace.entity_id == repair_id)
            | (AuditTrace.entity_id == repair.defect_id)
            | (AuditTrace.entity_id == repair.inspection_id)
        )
        .order_by(AuditTrace.created_at)
    )
    timeline = list(timeline_result.scalars().unique().all())

    for p in photos:
        photo_traces = await db.execute(
            select(AuditTrace).where(AuditTrace.entity_id == p.id, AuditTrace.entity_type == AuditEntity.photo)
        )
        timeline.extend(photo_traces.scalars().all())

    timeline.sort(key=lambda t: t.created_at)

    return TraceResult(
        repair_order=RepairOrderOut.model_validate(repair),
        defect=DefectOut.model_validate(repair.defect) if repair.defect else None,
        photos=[BladePhotoOut.model_validate(p) for p in photos],
        defects=[DefectOut.model_validate(d) for d in defects],
        timeline=timeline,
    )
