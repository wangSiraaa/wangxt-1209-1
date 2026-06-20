import hashlib
from pathlib import Path
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import UPLOAD_DIR
from .database import get_db
from .models import AuditAction, AuditEntity, AuditTrace, User


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> User:
    if not x_user_id:
        user_result = await db.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        if user:
            return user
        raise HTTPException(status_code=401, detail="未提供用户标识，且系统中无用户")
    try:
        uid = UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="用户标识格式错误")
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def require_role(user: User, *roles: str):
    if user.role.value not in roles:
        raise HTTPException(
            status_code=403,
            detail=f"当前角色「{user.role.value}」无权执行此操作，需要角色：{', '.join(roles)}",
        )
    return user


async def save_upload_file(file_bytes: bytes, original_filename: str, inspection_id: UUID) -> tuple[str, str]:
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    sub_dir = UPLOAD_DIR / str(inspection_id)
    sub_dir.mkdir(parents=True, exist_ok=True)
    file_path = sub_dir / f"{sha256[:16]}_{original_filename}"
    file_path.write_bytes(file_bytes)
    return str(file_path.relative_to(UPLOAD_DIR.parent)), sha256


async def write_audit(
    db: AsyncSession,
    entity_type: AuditEntity,
    entity_id: UUID,
    action: AuditAction,
    operator: User,
    detail: dict | None = None,
) -> AuditTrace:
    trace = AuditTrace(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        operator_id=operator.id,
        operator_role=operator.role,
        detail=detail,
    )
    db.add(trace)
    await db.flush()
    await db.refresh(trace, attribute_names=["operator"])
    return trace
