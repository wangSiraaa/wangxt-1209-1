from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..deps import get_current_user, require_role, save_upload_file, write_audit
from ..models import (
    ALL_SIDES, AuditAction, AuditEntity, BladePhoto, BladeSide,
    Defect, Inspection, InspectionStatus, Turbine, User,
)
from ..schemas import BladePhotoOut, InspectionDetail, InspectionOut

router = APIRouter()


async def _build_inspection_out(insp: Inspection, db: AsyncSession) -> Inspection:
    photo_count_result = await db.execute(
        select(func.count(BladePhoto.id)).where(BladePhoto.inspection_id == insp.id)
    )
    insp.photo_count = photo_count_result.scalar() or 0

    defect_count_result = await db.execute(
        select(func.count(Defect.id)).where(Defect.inspection_id == insp.id)
    )
    insp.defect_count = defect_count_result.scalar() or 0
    return insp


@router.get("/inspections", response_model=list[InspectionOut])
async def list_inspections(
    turbine_id: UUID | None = None,
    status: InspectionStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Inspection)
        .options(selectinload(Inspection.turbine), selectinload(Inspection.inspector), selectinload(Inspection.route_plan))
        .order_by(Inspection.created_at.desc())
    )
    if turbine_id:
        stmt = stmt.where(Inspection.turbine_id == turbine_id)
    if status:
        stmt = stmt.where(Inspection.status == status)
    result = await db.execute(stmt)
    inspections = result.scalars().unique().all()
    for insp in inspections:
        await _build_inspection_out(insp, db)
    return inspections


@router.get("/inspections/{inspection_id}", response_model=InspectionDetail)
async def get_inspection(inspection_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Inspection)
        .options(
            selectinload(Inspection.turbine),
            selectinload(Inspection.inspector),
            selectinload(Inspection.route_plan),
            selectinload(Inspection.photos),
            selectinload(Inspection.defects),
        )
        .where(Inspection.id == inspection_id)
    )
    insp = result.scalar_one_or_none()
    if not insp:
        raise HTTPException(status_code=404, detail="巡检不存在")

    await _build_inspection_out(insp, db)

    photos = insp.photos
    coverage: dict[int, dict[str, bool]] = {}
    for blade_no in range(1, insp.turbine.blade_count + 1 if insp.turbine else 4):
        coverage[blade_no] = {}
        for side in ALL_SIDES:
            has = any(p.blade_no == blade_no and p.side == side for p in photos)
            coverage[blade_no][side.value] = has

    blade_count = insp.turbine.blade_count if insp.turbine else 3
    total_needed = blade_count * len(ALL_SIDES)
    total_have = sum(1 for blade_sides in coverage.values() for has in blade_sides.values() if has)
    insp.photos = photos
    return InspectionDetail(
        **{
            field: getattr(insp, field)
            for field in InspectionOut.model_fields
            if hasattr(insp, field)
        },
        photos=[BladePhotoOut.model_validate(p) for p in photos],
        coverage=coverage,
        coverage_complete=total_have >= total_needed,
    )


@router.post("/inspections", response_model=InspectionOut)
async def create_inspection(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "inspector")
    turbine_id = UUID(data["turbine_id"])
    route_plan_id = UUID(data["route_plan_id"]) if data.get("route_plan_id") else None

    turbine_result = await db.execute(select(Turbine).where(Turbine.id == turbine_id))
    turbine = turbine_result.scalar_one_or_none()
    if not turbine:
        raise HTTPException(status_code=404, detail="机组不存在")

    from datetime import date as date_cls
    insp_date = data.get("inspection_date")
    insp = Inspection(
        turbine_id=turbine_id,
        route_plan_id=route_plan_id,
        inspector_id=current_user.id,
        status=InspectionStatus.draft,
        inspection_date=date_cls.fromisoformat(insp_date) if insp_date else date_cls.today(),
    )
    db.add(insp)
    await db.flush()

    turbine.status = "inspection"
    await write_audit(
        db, AuditEntity.inspection, insp.id, AuditAction.created, current_user,
        detail={"turbine_id": str(turbine_id), "inspection_date": str(insp.inspection_date)},
    )
    await db.commit()
    await db.refresh(insp, attribute_names=["turbine", "inspector", "route_plan"])
    await _build_inspection_out(insp, db)
    return insp


@router.post("/inspections/{inspection_id}/photos", response_model=BladePhotoOut)
async def upload_photo(
    inspection_id: UUID,
    blade_no: int = Form(...),
    side: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "inspector")

    result = await db.execute(
        select(Inspection).options(selectinload(Inspection.turbine)).where(Inspection.id == inspection_id)
    )
    insp = result.scalar_one_or_none()
    if not insp:
        raise HTTPException(status_code=404, detail="巡检不存在")
    if insp.status != InspectionStatus.draft:
        raise HTTPException(status_code=400, detail="已提交的巡检不能上传照片")

    blade_count = insp.turbine.blade_count if insp.turbine else 3
    if blade_no < 1 or blade_no > blade_count:
        raise HTTPException(status_code=400, detail=f"叶片编号必须在 1~{blade_count} 之间")

    try:
        side_enum = BladeSide(side)
    except ValueError:
        raise HTTPException(status_code=400, detail="叶片面必须是 pressure / suction / leading")

    existing = await db.execute(
        select(BladePhoto).where(
            BladePhoto.inspection_id == inspection_id,
            BladePhoto.blade_no == blade_no,
            BladePhoto.side == side_enum,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该叶片该面已有照片，请先删除再上传")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="上传文件为空")

    file_path, sha256 = await save_upload_file(file_bytes, file.filename or "photo.jpg", inspection_id)

    photo = BladePhoto(
        inspection_id=inspection_id,
        blade_no=blade_no,
        side=side_enum,
        file_path=file_path,
        sha256=sha256,
        original_filename=file.filename or "photo.jpg",
        file_size_bytes=len(file_bytes),
        mime_type=file.content_type or "image/jpeg",
        uploaded_by=current_user.id,
    )
    db.add(photo)
    await db.flush()
    await write_audit(
        db, AuditEntity.photo, photo.id, AuditAction.created, current_user,
        detail={"inspection_id": str(inspection_id), "blade_no": blade_no, "side": side},
    )
    await db.commit()
    await db.refresh(photo)
    return photo


@router.post("/inspections/{inspection_id}/submit", response_model=InspectionOut)
async def submit_inspection(
    inspection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "inspector")

    result = await db.execute(
        select(Inspection)
        .options(selectinload(Inspection.turbine), selectinload(Inspection.photos))
        .where(Inspection.id == inspection_id)
    )
    insp = result.scalar_one_or_none()
    if not insp:
        raise HTTPException(status_code=404, detail="巡检不存在")
    if insp.status == InspectionStatus.submitted:
        raise HTTPException(status_code=400, detail="巡检已提交，不能重复提交")

    blade_count = insp.turbine.blade_count if insp.turbine else 3
    photos = insp.photos
    coverage = set()
    for p in photos:
        coverage.add((p.blade_no, p.side))

    missing = []
    for blade_no in range(1, blade_count + 1):
        for side in ALL_SIDES:
            if (blade_no, side) not in coverage:
                missing.append(f"叶片{blade_no}的{side.value}面")

    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"三面叶片照片采集未完成，缺少：{', '.join(missing)}",
        )

    insp.status = InspectionStatus.submitted
    insp.submitted_at = datetime.utcnow()

    if insp.turbine:
        insp.turbine.status = "operating"

    await write_audit(
        db, AuditEntity.inspection, insp.id, AuditAction.submitted, current_user,
        detail={"photo_count": len(photos), "blade_count": blade_count},
    )
    await db.commit()
    await db.refresh(insp, attribute_names=["turbine", "inspector", "route_plan"])
    await _build_inspection_out(insp, db)
    return insp
