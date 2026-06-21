import enum
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger, CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer,
    Numeric, SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class UserRole(str, enum.Enum):
    inspector = "inspector"
    annotator = "annotator"
    supervisor = "supervisor"


class TurbineStatus(str, enum.Enum):
    operating = "operating"
    inspection = "inspection"
    repair = "repair"
    offline = "offline"


class InspectionStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"


class BladeSide(str, enum.Enum):
    pressure = "pressure"
    suction = "suction"
    leading = "leading"


class DefectType(str, enum.Enum):
    crack = "crack"
    lightning = "lightning"
    icing = "icing"


class DefectSeverity(str, enum.Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class DefectStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"


class RepairDecision(str, enum.Enum):
    repair = "repair"
    observe = "observe"


class RepairStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"


class GridStatus(str, enum.Enum):
    pending = "pending"
    frozen = "frozen"
    confirmed = "confirmed"


class AuditEntity(str, enum.Enum):
    inspection = "inspection"
    defect = "defect"
    repair_order = "repair_order"
    photo = "photo"
    grid = "grid"


class AuditAction(str, enum.Enum):
    created = "created"
    updated = "updated"
    submitted = "submitted"
    annotated = "annotated"
    escalated = "escalated"
    closed = "closed"
    confirmed = "confirmed"
    frozen = "frozen"
    unfrozen = "unfrozen"


SEVERITY_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
ALL_SIDES = [BladeSide.pressure, BladeSide.suction, BladeSide.leading]


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Turbine(Base):
    __tablename__ = "turbines"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    farm_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str | None] = mapped_column(String(64))
    rated_power_kw: Mapped[int] = mapped_column(Integer, default=2000)
    blade_count: Mapped[int] = mapped_column(SmallInteger, default=3)
    status: Mapped[TurbineStatus] = mapped_column(Enum(TurbineStatus, name="turbine_status"), default=TurbineStatus.operating)
    latitude: Mapped[float | None] = mapped_column()
    longitude: Mapped[float | None] = mapped_column()
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    route_plans: Mapped[list["RoutePlan"]] = relationship(back_populates="turbine", cascade="all, delete-orphan")
    grid_connections: Mapped[list["GridConnection"]] = relationship(back_populates="turbine")


class RoutePlan(Base):
    __tablename__ = "route_plans"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    turbine_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("turbines.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    waypoint_count: Mapped[int] = mapped_column(Integer, default=8)
    altitude_m: Mapped[float] = mapped_column(Numeric(6, 1), default=30.0)
    created_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    turbine: Mapped["Turbine"] = relationship(back_populates="route_plans")


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    turbine_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("turbines.id"), nullable=False)
    route_plan_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("route_plans.id"))
    inspector_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[InspectionStatus] = mapped_column(Enum(InspectionStatus, name="inspection_status"), default=InspectionStatus.draft)
    inspection_date: Mapped[date] = mapped_column(Date, default=date.today)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    turbine: Mapped["Turbine"] = relationship()
    inspector: Mapped["User"] = relationship()
    route_plan: Mapped["RoutePlan | None"] = relationship()
    photos: Mapped[list["BladePhoto"]] = relationship(back_populates="inspection", cascade="all, delete-orphan")
    defects: Mapped[list["Defect"]] = relationship(back_populates="inspection")


class BladePhoto(Base):
    __tablename__ = "blade_photos"
    __table_args__ = (
        UniqueConstraint("inspection_id", "blade_no", "side", name="uq_photo_blade_side"),
        CheckConstraint("blade_no BETWEEN 1 AND 3", name="ck_photo_blade_no"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    inspection_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    blade_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    side: Mapped[BladeSide] = mapped_column(Enum(BladeSide, name="blade_side"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), default="image/jpeg")
    uploaded_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    inspection: Mapped["Inspection"] = relationship(back_populates="photos")
    defects: Mapped[list["Defect"]] = relationship(back_populates="photo")


class Defect(Base):
    __tablename__ = "defects"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    inspection_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("inspections.id"), nullable=False)
    photo_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("blade_photos.id"), nullable=False)
    blade_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    side: Mapped[BladeSide] = mapped_column(Enum(BladeSide, name="blade_side"), nullable=False)
    defect_type: Mapped[DefectType] = mapped_column(Enum(DefectType, name="defect_type"), nullable=False)
    severity: Mapped[DefectSeverity] = mapped_column(Enum(DefectSeverity, name="defect_severity"), nullable=False)
    previous_severity: Mapped[DefectSeverity | None] = mapped_column(Enum(DefectSeverity, name="defect_severity"))
    description: Mapped[str | None] = mapped_column(Text)
    review_notes: Mapped[str | None] = mapped_column(Text)
    annotated_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[DefectStatus] = mapped_column(Enum(DefectStatus, name="defect_status"), default=DefectStatus.open)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    inspection: Mapped["Inspection"] = relationship(back_populates="defects")
    photo: Mapped["BladePhoto"] = relationship(back_populates="defects")
    annotator: Mapped["User"] = relationship(foreign_keys=[annotated_by])
    repair_orders: Mapped[list["RepairOrder"]] = relationship(back_populates="defect")


class RepairOrder(Base):
    __tablename__ = "repair_orders"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    defect_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("defects.id"), nullable=False)
    turbine_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("turbines.id"), nullable=False)
    inspection_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("inspections.id"), nullable=False)
    decision: Mapped[RepairDecision] = mapped_column(Enum(RepairDecision, name="repair_decision"), nullable=False)
    status: Mapped[RepairStatus] = mapped_column(Enum(RepairStatus, name="repair_status"), default=RepairStatus.open)
    supervisor_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closure_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    defect: Mapped["Defect"] = relationship(back_populates="repair_orders")
    turbine: Mapped["Turbine"] = relationship()
    supervisor: Mapped["User"] = relationship(foreign_keys=[supervisor_id])


class GridConnection(Base):
    __tablename__ = "grid_connections"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    turbine_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("turbines.id"), nullable=False)
    status: Mapped[GridStatus] = mapped_column(Enum(GridStatus, name="grid_status"), default=GridStatus.pending)
    frozen_reason: Mapped[str | None] = mapped_column(Text)
    frozen_by_defect_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("defects.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    turbine: Mapped["Turbine"] = relationship(back_populates="grid_connections")
    defect: Mapped["Defect | None"] = relationship(foreign_keys=[frozen_by_defect_id])


class AuditTrace(Base):
    __tablename__ = "audit_traces"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[AuditEntity] = mapped_column(Enum(AuditEntity, name="audit_entity"), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction, name="audit_action"), nullable=False)
    operator_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    operator_role: Mapped[UserRole | None] = mapped_column(Enum(UserRole, name="user_role"))
    detail: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    operator: Mapped["User | None"] = relationship()
