<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu, Files, Warning, Lightning } from '@element-plus/icons-vue'
import { api } from '@/api'
import type { DashboardStats, DefectType, DefectSeverity } from '@/types'
import { DEFECT_TYPE_LABELS, SEVERITY_LABELS } from '@/types'

const loading = ref(false)
const stats = ref<DashboardStats | null>(null)

const defectTypeTotal = computed(() =>
  (stats.value?.defect_by_type ?? []).reduce((sum, item) => sum + item.count, 0),
)

const defectTypeColors: Record<DefectType, string> = {
  crack: 'bg-amber-500',
  lightning: 'bg-wind-400',
  icing: 'bg-sky-500',
}

const severityDots: Record<DefectSeverity, string> = {
  L1: 'bg-emerald-500',
  L2: 'bg-amber-500',
  L3: 'bg-orange-500',
  L4: 'bg-red-500',
}

const allSeverities: DefectSeverity[] = ['L1', 'L2', 'L3', 'L4']

const severityRows = computed(() => {
  const counts = new Map<DefectSeverity, number>()
  for (const item of stats.value?.defect_by_severity ?? []) {
    counts.set(item.severity, item.count)
  }
  return allSeverities.map((severity) => ({
    severity,
    label: SEVERITY_LABELS[severity],
    count: counts.get(severity) ?? 0,
  }))
})

const statCards = computed(() => {
  const s = stats.value
  const openDefect = s?.open_defect_count ?? 0
  const frozenGrid = s?.frozen_grid_count ?? 0
  return [
    {
      key: 'turbine',
      label: '机组数',
      value: s?.turbine_count ?? 0,
      icon: Cpu,
      numClass: 'text-wind-400',
      iconClass: 'bg-wind-500/15 text-wind-400',
    },
    {
      key: 'draft',
      label: '待提交巡检',
      value: s?.draft_inspection_count ?? 0,
      icon: Files,
      numClass: 'text-wind-400',
      iconClass: 'bg-amber-500/15 text-amber-400',
    },
    {
      key: 'defect',
      label: '未闭环缺陷',
      value: openDefect,
      icon: Warning,
      numClass: openDefect > 0 ? 'text-red-500' : 'text-wind-400',
      iconClass: 'bg-red-500/15 text-red-400',
    },
    {
      key: 'frozen',
      label: '冻结并网',
      value: frozenGrid,
      icon: Lightning,
      numClass: frozenGrid > 0 ? 'text-red-500' : 'text-wind-400',
      iconClass: 'bg-red-500/15 text-red-400',
    },
  ]
})

async function loadStats() {
  loading.value = true
  try {
    stats.value = await api.getDashboardStats()
  } catch {
    ElMessage.error('工作台数据加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
</script>

<template>
  <div v-loading="loading" class="space-y-4">
    <div class="grid grid-cols-4 gap-4">
      <el-card
        v-for="card in statCards"
        :key="card.key"
        class="!bg-slate-900/60 !border-slate-800"
        body-class="!p-4"
        shadow="never"
      >
        <div class="flex items-center gap-3">
          <div
            class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg"
            :class="card.iconClass"
          >
            <el-icon :size="22"><component :is="card.icon" /></el-icon>
          </div>
          <div class="min-w-0">
            <div class="text-xs text-slate-400">{{ card.label }}</div>
            <div class="text-3xl font-700 font-mono leading-tight" :class="card.numClass">
              {{ card.value }}
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <el-card
        class="!bg-slate-900/60 !border-slate-800 col-span-2"
        body-class="!p-5"
        shadow="never"
      >
        <template #header>
          <span class="font-display text-sm font-600 text-slate-200">缺陷类型分布</span>
        </template>
        <el-empty v-if="defectTypeTotal === 0" description="暂无缺陷数据" :image-size="72" />
        <div v-else class="space-y-4">
          <div v-for="item in stats?.defect_by_type ?? []" :key="item.type">
            <div class="mb-1.5 flex items-center justify-between text-xs">
              <span class="text-slate-300">{{ DEFECT_TYPE_LABELS[item.type] }}</span>
              <span class="font-mono text-slate-400">{{ item.count }}</span>
            </div>
            <div class="h-2 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="defectTypeColors[item.type]"
                :style="{
                  width: defectTypeTotal
                    ? (item.count / defectTypeTotal) * 100 + '%'
                    : '0%',
                }"
              />
            </div>
          </div>
        </div>
      </el-card>

      <el-card class="!bg-slate-900/60 !border-slate-800" body-class="!p-5" shadow="never">
        <template #header>
          <span class="font-display text-sm font-600 text-slate-200">缺陷等级分布</span>
        </template>
        <div class="space-y-3">
          <div
            v-for="row in severityRows"
            :key="row.severity"
            class="flex items-center justify-between rounded-lg bg-slate-800/40 px-3 py-2.5"
          >
            <div class="flex items-center gap-2">
              <span class="h-2.5 w-2.5 rounded-full" :class="severityDots[row.severity]" />
              <span class="text-sm text-slate-300">{{ row.label }}</span>
            </div>
            <span class="font-mono text-lg font-700 text-wind-400">{{ row.count }}</span>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>
