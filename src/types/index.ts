export type UserRole = 'inspector' | 'annotator' | 'supervisor'

export type TurbineStatus = 'operating' | 'inspection' | 'repair' | 'offline'

export type InspectionStatus = 'draft' | 'submitted'

export type BladeSide = 'pressure' | 'suction' | 'leading'

export type DefectType = 'crack' | 'lightning' | 'icing'

export type DefectSeverity = 'L1' | 'L2' | 'L3' | 'L4'

export type DefectStatus = 'open' | 'resolved'

export type RepairDecision = 'repair' | 'observe'

export type RepairStatus = 'open' | 'in_progress' | 'closed'

export type GridStatus = 'pending' | 'frozen' | 'confirmed'

export interface User {
  id: string
  username: string
  display_name: string
  role: UserRole
  created_at: string
}

export interface Turbine {
  id: string
  code: string
  name: string
  farm_name: string
  model: string
  rated_power_kw: number
  blade_count: number
  status: TurbineStatus
  latitude?: number
  longitude?: number
  created_by?: string
  created_at: string
  updated_at: string
}

export interface RoutePlan {
  id: string
  turbine_id: string
  name: string
  description?: string
  waypoint_count: number
  altitude_m: number
  created_by?: string
  created_at: string
  updated_at: string
}

export interface Inspection {
  id: string
  turbine_id: string
  route_plan_id?: string
  inspector_id: string
  status: InspectionStatus
  inspection_date: string
  submitted_at?: string
  created_at: string
  updated_at: string
  turbine?: Turbine
  inspector?: User
  route_plan?: RoutePlan
  photo_count?: number
  defect_count?: number
}

export interface BladePhoto {
  id: string
  inspection_id: string
  blade_no: number
  side: BladeSide
  file_path: string
  sha256: string
  original_filename: string
  file_size_bytes: number
  mime_type: string
  uploaded_by?: string
  uploaded_at: string
}

export interface SideCoverage {
  blade_no: number
  sides: BladeSide[]
}

export interface InspectionDetail extends Inspection {
  photos: BladePhoto[]
  coverage: Record<number, Partial<Record<BladeSide, boolean>>>
  coverage_complete: boolean
}

export interface Defect {
  id: string
  inspection_id: string
  photo_id: string
  blade_no: number
  side: BladeSide
  defect_type: DefectType
  severity: DefectSeverity
  previous_severity?: DefectSeverity
  description?: string
  annotated_by: string
  status: DefectStatus
  created_at: string
  updated_at: string
  photo?: BladePhoto
  annotator?: User
  turbine?: Turbine
  inspection?: Inspection
}

export interface RepairOrder {
  id: string
  defect_id: string
  turbine_id: string
  inspection_id: string
  decision: RepairDecision
  status: RepairStatus
  supervisor_id: string
  decided_at: string
  closed_at?: string
  closure_notes?: string
  created_at: string
  updated_at: string
  defect?: Defect
  turbine?: Turbine
  supervisor?: User
}

export interface GridConnection {
  id: string
  turbine_id: string
  status: GridStatus
  frozen_reason?: string
  frozen_by_defect_id?: string
  confirmed_at?: string
  confirmed_by?: string
  created_at: string
  updated_at: string
  turbine?: Turbine
  defect?: Defect
}

export interface AuditTrace {
  id: string
  entity_type: string
  entity_id: string
  action: string
  operator_id?: string
  operator_role?: UserRole
  detail: Record<string, unknown>
  created_at: string
  operator?: User
}

export interface TraceResult {
  repair_order: RepairOrder
  defect: Defect
  photos: BladePhoto[]
  defects: Defect[]
  timeline: AuditTrace[]
}

export interface DashboardStats {
  turbine_count: number
  draft_inspection_count: number
  open_defect_count: number
  frozen_grid_count: number
  submitted_inspection_count: number
  open_repair_count: number
  defect_by_type: { type: DefectType; count: number }[]
  defect_by_severity: { severity: DefectSeverity; count: number }[]
}

export interface ApiResult<T> {
  items?: T[]
  total?: number
  data?: T
}

export const SIDE_LABELS: Record<BladeSide, string> = {
  pressure: '迎风面',
  suction: '背风面',
  leading: '前缘',
}

export const SIDE_ORDER: BladeSide[] = ['pressure', 'suction', 'leading']

export const DEFECT_TYPE_LABELS: Record<DefectType, string> = {
  crack: '裂纹',
  lightning: '雷击点',
  icing: '结冰',
}

export const SEVERITY_LABELS: Record<DefectSeverity, string> = {
  L1: 'L1 轻微',
  L2: 'L2 中度',
  L3: 'L3 严重',
  L4: 'L4 危急',
}

export const SEVERITY_COLORS: Record<DefectSeverity, string> = {
  L1: '',
  L2: 'warning',
  L3: 'danger',
  L4: 'danger',
}

export const TURBINE_STATUS_LABELS: Record<TurbineStatus, string> = {
  operating: '运行中',
  inspection: '巡检中',
  repair: '维修中',
  offline: '离线',
}

export const TURBINE_STATUS_COLORS: Record<TurbineStatus, string> = {
  operating: 'success',
  inspection: 'primary',
  repair: 'warning',
  offline: 'info',
}

export const INSPECTION_STATUS_LABELS: Record<InspectionStatus, string> = {
  draft: '草稿',
  submitted: '已提交',
}

export const REPAIR_STATUS_LABELS: Record<RepairStatus, string> = {
  open: '待处理',
  in_progress: '处理中',
  closed: '已关闭',
}

export const GRID_STATUS_LABELS: Record<GridStatus, string> = {
  pending: '待确认',
  frozen: '已冻结',
  confirmed: '已确认',
}

export const GRID_STATUS_COLORS: Record<GridStatus, string> = {
  pending: 'info',
  frozen: 'danger',
  confirmed: 'success',
}
