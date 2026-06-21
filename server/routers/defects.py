from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..deps import get_current_user, require_role, write_audit
from ..models import (
    AuditAction, AuditEntity, BladePhoto, BladeSide, Defect, DefectSeverity,
    DefectStatus, DefectType, GridConnection, GridStatus, Inspection,
    SEVERITY_ORDER, Turbine, User,
)
from ..schemas import DefectCreate, DefectOut, DefectUpdate

router = APIRouter()

DEFECT_LOAD_OPTIONS = (
    selectinload(Defect.photo),
    selectinload(Defect.annotator),
    selectinload(Defect.inspection).selectinload(Inspection.turbine),
    selectinload(Defect.inspection).selectinload(Inspection.inspector),
    selectinload(Defect.inspection).selectinload(Inspection.route_plan),
)


async def _reload_defect(db: AsyncSession, defect_id: UUID) -> Defect:
    result = await db.execute(
        select(Defect).options(*DEFECT_LOAD_OPTIONS).where(Defect.id == defect_id)
    )
    d = result.scalar_one()
    d.turbine = d.inspection.turbine if d.inspection else None
    return d


async def _freeze_grid(
    db: AsyncSession,
    turbine_id: UUID,
    defect_id: UUID,
    severity: DefectSeverity,
    operator: User,
    reason: str,
):
    from sqlalchemy import desc

    result = await db.execute(
        select(GridConnection)
        .where(
            GridConnection.turbine_id == turbine_id,
            GridConnection.status != GridStatus.confirmed,
        )
        .order_by(desc(GridConnection.created_at))
    )
    grid = result.scalar_one_or_none()
    if not grid:
        grid = GridConnection(turbine_id=turbine_id, status=GridStatus.pending)
        db.add(grid)
        await db.flush()

    grid.status = GridStatus.frozen
    grid.frozen_reason = reason
    grid.frozen_by_defect_id = defect_id

    await write_audit(
        db, AuditEntity.grid, grid.id, AuditAction.frozen, operator,
        detail={
            "turbine_id": str(turbine_id),
            "defect_id": str(defect_id),
            "severity": severity.value,
            "reason": reason,
        },
    )


async def _build_defect_out(defect: Defect, db: AsyncSession) -> Defect:
    if not defect.photo:
        photo_result = await db.execute(
            select(BladePhoto).where(BladePhoto.id == defect.photo_id)
        )
        defect.photo = photo_result.scalar_one_or_none()
    if not defect.annotator:
        user_result = await db.execute(
            select(User).where(User.id == defect.annotated_by)
        )
        defect.annotator = user_result.scalar_one_or_none()
    if not defect.turbine:
        insp_result = await db.execute(
            select(Inspection).where(Inspection.id == defect.inspection_id)
        )
        insp = insp_result.scalar_one_or_none()
        if insp:
            turb_result = await db.execute(select(Turbine).where(Turbine.id == insp.turbine_id))
            defect.turbine = turb_result.scalar_one_or_none()
            defect.inspection = insp
    return defect


@router.get("/defects", response_model=list[DefectOut])
async def list_defects(
    inspection_id: UUID | None = Query(None),
    turbine_id: UUID | None = Query(None),
    status: DefectStatus | None = Query(None),
    defect_type: DefectType | None = Query(None),
    severity: DefectSeverity | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Defect)
        .options(*DEFECT_LOAD_OPTIONS)
        .order_by(Defect.created_at.desc())
    )
    if inspection_id:
        stmt = stmt.where(Defect.inspection_id == inspection_id)
    if status:
        stmt = stmt.where(Defect.status == status)
    if defect_type:
        stmt = stmt.where(Defect.defect_type == defect_type)
    if severity:
        stmt = stmt.where(Defect.severity == severity)
    if turbine_id:
        stmt = stmt.join(Inspection, Defect.inspection_id == Inspection.id).where(
            Inspection.turbine_id == turbine_id
        )

    result = await db.execute(stmt)
    defects = result.scalars().unique().all()
    for d in defects:
        d.turbine = d.inspection.turbine if d.inspection else None
    return defects


@router.post("/defects", response_model=DefectOut)
async def create_defect(
    data: DefectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "annotator")

    photo_result = await db.execute(
        select(BladePhoto).where(BladePhoto.id == data.photo_id)
    )
    photo = photo_result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    insp_result = await db.execute(
        select(Inspection).where(Inspection.id == data.inspection_id)
    )
    insp = insp_result.scalar_one_or_none()
    if not insp:
        raise HTTPException(status_code=404, detail="巡检不存在")

    if insp.status != InspectionStatus.submitted:
        raise HTTPException(
            status_code=400,
            detail=f"巡检状态为「{insp.status.value}」，仅已提交的巡检可标注缺陷",
        )

    if photo.inspection_id != data.inspection_id:
        raise HTTPException(
            status_code=400,
            detail="该照片不属于所选巡检，请重新选择",
        )

    if photo.blade_no != data.blade_no or photo.side != data.side:
        raise HTTPException(
            status_code=400,
            detail="叶片号或叶面与照片信息不匹配，请重新选择",
        )

    defect = Defect(
        inspection_id=data.inspection_id,
        photo_id=data.photo_id,
        blade_no=data.blade_no,
        side=data.side,
        defect_type=data.defect_type,
        severity=data.severity,
        description=data.description,
        annotated_by=current_user.id,
        status=DefectStatus.open,
    )
    db.add(defect)
    await db.flush()

    await _freeze_grid(
        db, insp.turbine_id, defect.id, data.severity, current_user,
        f"新增缺陷[{data.defect_type.value}]等级{data.severity.value}，自动冻结并网",
    )

    await write_audit(
        db, AuditEntity.defect, defect.id, AuditAction.annotated, current_user,
        detail={
            "inspection_id": str(data.inspection_id),
            "photo_id": str(data.photo_id),
            "defect_type": data.defect_type.value,
            "severity": data.severity.value,
        },
    )
    await db.commit()
    return await _reload_defect(db, defect.id)


@router.put("/defects/{defect_id}", response_model=DefectOut)
async def update_defect(
    defect_id: UUID,
    data: DefectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "annotator")

    result = await db.execute(
        select(Defect)
        .options(selectinload(Defect.inspection))
        .where(Defect.id == defect_id)
    )
    defect = result.scalar_one_or_none()
    if not defect:
        raise HTTPException(status_code=404, detail="缺陷不存在")

    escalation = False
    if data.severity is not None and data.severity != defect.severity:
        old_sev = defect.severity
        if SEVERITY_ORDER[data.severity.value] > SEVERITY_ORDER[defect.severity.value]:
            escalation = True
            defect.previous_severity = old_sev
        defect.severity = data.severity

    if data.description is not None:
        defect.description = data.description
    if data.status is not None:
        defect.status = data.status
    defect.updated_at = datetime.utcnow()

    if escalation:
        insp = defect.inspection
        if insp:
            await _freeze_grid(
                db, insp.turbine_id, defect.id, defect.severity, current_user,
                f"缺陷等级升高：{defect.previous_severity.value if defect.previous_severity else '?'} → {defect.severity.value}，自动冻结并网",
            )
            await write_audit(
                db, AuditEntity.defect, defect.id, AuditAction.escalated, current_user,
                detail={
                    "previous_severity": defect.previous_severity.value if defect.previous_severity else None,
                    "new_severity": defect.severity.value,
                },
            )

    await write_audit(
        db, AuditEntity.defect, defect.id, AuditAction.updated, current_user,
        detail=data.model_dump(exclude_unset=True),
    )
    await db.commit()
    return await _reload_defect(db, defect.id)
