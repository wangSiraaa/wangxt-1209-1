from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import (
    Defect, DefectSeverity, DefectStatus, DefectType, GridConnection,
    GridStatus, Inspection, InspectionStatus, RepairStatus, RepairOrder,
    Turbine,
)
from ..schemas import (
    DashboardStats, DefectSeverityCount, DefectTypeCount,
)

router = APIRouter()


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    turbine_count = (await db.execute(select(func.count(Turbine.id)))).scalar() or 0

    draft_count = (
        await db.execute(
            select(func.count(Inspection.id)).where(Inspection.status == InspectionStatus.draft)
        )
    ).scalar() or 0

    submitted_count = (
        await db.execute(
            select(func.count(Inspection.id)).where(Inspection.status == InspectionStatus.submitted)
        )
    ).scalar() or 0

    open_defect_count = (
        await db.execute(
            select(func.count(Defect.id)).where(Defect.status == DefectStatus.open)
        )
    ).scalar() or 0

    open_repair_count = (
        await db.execute(
            select(func.count(RepairOrder.id)).where(RepairOrder.status != RepairStatus.closed)
        )
    ).scalar() or 0

    frozen_grid_count = (
        await db.execute(
            select(func.count(GridConnection.id)).where(GridConnection.status == GridStatus.frozen)
        )
    ).scalar() or 0

    type_rows = (
        await db.execute(
            select(Defect.defect_type, func.count(Defect.id))
            .where(Defect.status == DefectStatus.open)
            .group_by(Defect.defect_type)
        )
    ).all()
    defect_by_type = [
        DefectTypeCount(type=row[0], count=row[1]) for row in type_rows
    ]

    sev_rows = (
        await db.execute(
            select(Defect.severity, func.count(Defect.id))
            .where(Defect.status == DefectStatus.open)
            .group_by(Defect.severity)
        )
    ).all()
    defect_by_severity = [
        DefectSeverityCount(severity=row[0], count=row[1]) for row in sev_rows
    ]

    return DashboardStats(
        turbine_count=turbine_count,
        draft_inspection_count=draft_count,
        submitted_inspection_count=submitted_count,
        open_defect_count=open_defect_count,
        open_repair_count=open_repair_count,
        frozen_grid_count=frozen_grid_count,
        defect_by_type=defect_by_type,
        defect_by_severity=defect_by_severity,
    )
