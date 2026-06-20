import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import UPLOAD_DIR
from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import BladePhoto, Defect, User
from ..schemas import DefectOut

router = APIRouter()


@router.get("/photos/{photo_id}/image")
async def get_photo_image(photo_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BladePhoto).where(BladePhoto.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    file_path = UPLOAD_DIR.parent / photo.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="图片文件不存在于磁盘")

    return FileResponse(path=str(file_path), media_type=photo.mime_type or "image/jpeg")


@router.get("/photos/{photo_id}/defects", response_model=list[DefectOut])
async def get_photo_defects(photo_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Defect)
        .options(selectinload(Defect.photo), selectinload(Defect.annotator))
        .where(Defect.photo_id == photo_id)
        .order_by(Defect.created_at.desc())
    )
    defects = result.scalars().unique().all()
    return defects


@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_role(current_user, "inspector")

    result = await db.execute(select(BladePhoto).where(BladePhoto.id == photo_id))
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    defect_result = await db.execute(select(Defect).where(Defect.photo_id == photo_id))
    if defect_result.scalars().first():
        raise HTTPException(status_code=409, detail="该照片已有关联缺陷，不能删除")

    file_path = UPLOAD_DIR.parent / photo.file_path
    if file_path.exists():
        os.remove(file_path)

    await db.delete(photo)
    await db.commit()
    return {"ok": True}
