import request from './request'
import type {
  User,
  Turbine,
  RoutePlan,
  Inspection,
  InspectionDetail,
  BladePhoto,
  Defect,
  RepairOrder,
  GridConnection,
  TraceResult,
  DashboardStats,
  DefectType,
  DefectSeverity,
  DefectStatus,
  TurbineStatus,
  InspectionStatus,
  GridStatus,
  RepairStatus,
} from '@/types'

export const api = {
  // ---- 用户 ----
  getUsers: () => request.get<unknown, User[]>('/users'),
  getCurrentUser: () => request.get<unknown, User>('/users/me'),
  switchUser: (userId: string) =>
    request.post<unknown, User>(`/users/${userId}/switch`),

  // ---- 工作台 ----
  getDashboardStats: () =>
    request.get<unknown, DashboardStats>('/dashboard/stats'),

  // ---- 机组 ----
  getTurbines: (params?: { status?: TurbineStatus; farm?: string }) =>
    request.get<unknown, Turbine[]>('/turbines', { params }),
  getTurbine: (id: string) => request.get<unknown, Turbine>(`/turbines/${id}`),
  createTurbine: (data: Partial<Turbine>) =>
    request.post<unknown, Turbine>('/turbines', data),
  updateTurbine: (id: string, data: Partial<Turbine>) =>
    request.put<unknown, Turbine>(`/turbines/${id}`, data),

  // ---- 航线计划 ----
  getRoutePlans: (params?: { turbine_id?: string }) =>
    request.get<unknown, RoutePlan[]>('/route-plans', { params }),
  createRoutePlan: (data: Partial<RoutePlan>) =>
    request.post<unknown, RoutePlan>('/route-plans', data),
  updateRoutePlan: (id: string, data: Partial<RoutePlan>) =>
    request.put<unknown, RoutePlan>(`/route-plans/${id}`, data),
  deleteRoutePlan: (id: string) =>
    request.delete<unknown, void>(`/route-plans/${id}`),

  // ---- 巡检 ----
  getInspections: (params?: {
    turbine_id?: string
    status?: InspectionStatus
  }) => request.get<unknown, Inspection[]>('/inspections', { params }),
  getInspection: (id: string) =>
    request.get<unknown, InspectionDetail>(`/inspections/${id}`),
  createInspection: (data: {
    turbine_id: string
    route_plan_id?: string
    inspection_date?: string
  }) => request.post<unknown, Inspection>('/inspections', data),
  uploadPhoto: (
    inspectionId: string,
    blade_no: number,
    side: string,
    file: File,
  ) => {
    const form = new FormData()
    form.append('blade_no', String(blade_no))
    form.append('side', side)
    form.append('file', file)
    return request.post<unknown, BladePhoto>(
      `/inspections/${inspectionId}/photos`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
  },
  deletePhoto: (photoId: string) =>
    request.delete<unknown, void>(`/photos/${photoId}`),
  submitInspection: (id: string) =>
    request.post<unknown, Inspection>(`/inspections/${id}/submit`),

  // ---- 缺陷 ----
  getDefects: (params?: {
    inspection_id?: string
    turbine_id?: string
    status?: DefectStatus
    defect_type?: DefectType
    severity?: DefectSeverity
  }) => request.get<unknown, Defect[]>('/defects', { params }),
  createDefect: (data: {
    inspection_id: string
    photo_id: string
    blade_no: number
    side: string
    defect_type: DefectType
    severity: DefectSeverity
    description?: string
    review_notes?: string
  }) => request.post<unknown, Defect>('/defects', data),
  updateDefect: (
    id: string,
    data: Partial<{
      severity: DefectSeverity
      description: string
      review_notes: string
      status: DefectStatus
    }>,
  ) => request.put<unknown, Defect>(`/defects/${id}`, data),
  getPhotoDefects: (photoId: string) =>
    request.get<unknown, Defect[]>(`/photos/${photoId}/defects`),
  photoUrl: (photoId: string) => `/api/photos/${photoId}/image`,

  // ---- 维修单 ----
  getRepairOrders: (params?: {
    turbine_id?: string
    status?: RepairStatus
  }) => request.get<unknown, RepairOrder[]>('/repair-orders', { params }),
  createRepairOrder: (data: {
    defect_id: string
    decision: 'repair' | 'observe'
  }) => request.post<unknown, RepairOrder>('/repair-orders', data),
  closeRepairOrder: (id: string, closure_notes: string) =>
    request.put<unknown, RepairOrder>(`/repair-orders/${id}/close`, {
      closure_notes,
    }),
  getTrace: (id: string) =>
    request.get<unknown, TraceResult>(`/repair-orders/${id}/trace`),

  // ---- 并网确认 ----
  getGridConnections: (params?: {
    turbine_id?: string
    status?: GridStatus
  }) => request.get<unknown, GridConnection[]>('/grid-connections', { params }),
  confirmGrid: (id: string) =>
    request.post<unknown, GridConnection>(`/grid-connections/${id}/confirm`),
}
