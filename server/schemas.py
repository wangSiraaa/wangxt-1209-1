from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .models import (
    AuditAction, AuditEntity, BladeSide, DefectSeverity, DefectStatus,
    DefectType, GridStatus, InspectionStatus, RepairDecision, RepairStatus,
    TurbineStatus, UserRole,
)


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- 用户 ----
class UserOut(ORMBase):
    id: UUID
    username: str
    display_name: str
    role: UserRole
    created_at: datetime


# ---- 机组 ----
class TurbineCreate(BaseModel):
    code: str
    name: str
    farm_name: str
    model: str | None = None
    rated_power_kw: int = 2000
    blade_count: int = 3
    status: TurbineStatus = TurbineStatus.operating
    latitude: float | None = None
    longitude: float | None = None


class TurbineUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    farm_name: str | None = None
    model: str | None = None
    rated_power_kw: int | None = None
    blade_count: int | None = None
    status: TurbineStatus | None = None
    latitude: float | None = None
    longitude: float | None = None


class TurbineOut(ORMBase):
    id: UUID
    code: str
    name: str
    farm_name: str
    model: str | None
    rated_power_kw: int
    blade_count: int
    status: TurbineStatus
    latitude: float | None
    longitude: float | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


# ---- 航线计划 ----
class RoutePlanCreate(BaseModel):
    turbine_id: UUID
    name: str
    description: str | None = None
    waypoint_count: int = 8
    altitude_m: float = 30.0


class RoutePlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    waypoint_count: int | None = None
    altitude_m: float | None = None


class RoutePlanOut(ORMBase):
    id: UUID
    turbine_id: UUID
    name: str
    description: str | None
    waypoint_count: int
    altitude_m: float
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


# ---- 巡检 ----
class InspectionCreate(BaseModel):
    turbine_id: UUID
    route_plan_id: UUID | None = None
    inspection_date: date | None = None


class BladePhotoOut(ORMBase):
    id: UUID
    inspection_id: UUID
    blade_no: int
    side: BladeSide
    file_path: str
    sha256: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    uploaded_by: UUID | None
    uploaded_at: datetime


class SideCoverage(BaseModel):
    blade_no: int
    sides: list[BladeSide]


class InspectionOut(ORMBase):
    id: UUID
    turbine_id: UUID
    route_plan_id: UUID | None
    inspector_id: UUID
    status: InspectionStatus
    inspection_date: date
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    turbine: TurbineOut | None = None
    inspector: UserOut | None = None
    route_plan: RoutePlanOut | None = None
    photo_count: int = 0
    defect_count: int = 0


class InspectionDetail(InspectionOut):
    photos: list[BladePhotoOut] = []
    coverage: dict[int, dict[str, bool]] = {}
    coverage_complete: bool = False


# ---- 缺陷 ----
class DefectCreate(BaseModel):
    inspection_id: UUID
    photo_id: UUID
    blade_no: int
    side: BladeSide
    defect_type: DefectType
    severity: DefectSeverity
    description: str | None = None
    review_notes: str | None = None


class DefectUpdate(BaseModel):
    severity: DefectSeverity | None = None
    description: str | None = None
    review_notes: str | None = None
    status: DefectStatus | None = None


class DefectOut(ORMBase):
    id: UUID
    inspection_id: UUID
    photo_id: UUID
    blade_no: int
    side: BladeSide
    defect_type: DefectType
    severity: DefectSeverity
    previous_severity: DefectSeverity | None
    description: str | None
    review_notes: str | None
    annotated_by: UUID
    status: DefectStatus
    created_at: datetime
    updated_at: datetime
    photo: BladePhotoOut | None = None
    annotator: UserOut | None = None
    turbine: TurbineOut | None = None
    inspection: InspectionOut | None = None


# ---- 维修单 ----
class RepairOrderCreate(BaseModel):
    defect_id: UUID
    decision: RepairDecision


class RepairOrderClose(BaseModel):
    closure_notes: str


class RepairOrderOut(ORMBase):
    id: UUID
    defect_id: UUID
    turbine_id: UUID
    inspection_id: UUID
    decision: RepairDecision
    status: RepairStatus
    supervisor_id: UUID
    decided_at: datetime
    closed_at: datetime | None
    closure_notes: str | None
    created_at: datetime
    updated_at: datetime
    defect: DefectOut | None = None
    turbine: TurbineOut | None = None
    supervisor: UserOut | None = None


# ---- 并网确认 ----
class GridConnectionOut(ORMBase):
    id: UUID
    turbine_id: UUID
    status: GridStatus
    frozen_reason: str | None
    frozen_by_defect_id: UUID | None
    confirmed_at: datetime | None
    confirmed_by: UUID | None
    created_at: datetime
    updated_at: datetime
    turbine: TurbineOut | None = None
    defect: DefectOut | None = None


# ---- 追溯审计 ----
class AuditTraceOut(ORMBase):
    id: UUID
    entity_type: AuditEntity
    entity_id: UUID
    action: AuditAction
    operator_id: UUID | None
    operator_role: UserRole | None
    detail: dict | None
    created_at: datetime
    operator: UserOut | None = None


class TraceResult(BaseModel):
    repair_order: RepairOrderOut
    defect: DefectOut
    photos: list[BladePhotoOut]
    defects: list[DefectOut]
    timeline: list[AuditTraceOut]


# ---- 工作台 ----
class DefectTypeCount(BaseModel):
    type: DefectType
    count: int


class DefectSeverityCount(BaseModel):
    severity: DefectSeverity
    count: int


class DashboardStats(BaseModel):
    turbine_count: int
    draft_inspection_count: int
    submitted_inspection_count: int
    open_defect_count: int
    open_repair_count: int
    frozen_grid_count: int
    defect_by_type: list[DefectTypeCount]
    defect_by_severity: list[DefectSeverityCount]
