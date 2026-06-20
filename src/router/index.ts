import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import DashboardPage from '@/pages/DashboardPage.vue'
import TurbinesPage from '@/pages/TurbinesPage.vue'
import RoutePlansPage from '@/pages/RoutePlansPage.vue'
import InspectionsPage from '@/pages/InspectionsPage.vue'
import InspectionDetailPage from '@/pages/InspectionDetailPage.vue'
import DefectsPage from '@/pages/DefectsPage.vue'
import RepairsPage from '@/pages/RepairsPage.vue'
import GridPage from '@/pages/GridPage.vue'
import TracePage from '@/pages/TracePage.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'dashboard', component: DashboardPage, meta: { title: '工作台' } },
  { path: '/turbines', name: 'turbines', component: TurbinesPage, meta: { title: '机组管理' } },
  { path: '/routes', name: 'routes', component: RoutePlansPage, meta: { title: '航线计划' } },
  { path: '/inspections', name: 'inspections', component: InspectionsPage, meta: { title: '巡检管理' } },
  { path: '/inspections/:id', name: 'inspection-detail', component: InspectionDetailPage, meta: { title: '巡检详情' } },
  { path: '/defects', name: 'defects', component: DefectsPage, meta: { title: '缺陷复核' } },
  { path: '/repairs', name: 'repairs', component: RepairsPage, meta: { title: '维修单管理' } },
  { path: '/grid', name: 'grid', component: GridPage, meta: { title: '并网确认' } },
  { path: '/trace', name: 'trace', component: TracePage, meta: { title: '追溯查询' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  const title = (to.meta?.title as string) || ''
  document.title = title
    ? `${title} · 风电场叶片巡检`
    : '风电场叶片无人机巡检闭环系统'
})

export default router
