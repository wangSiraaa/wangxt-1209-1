<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useFormat } from '@/composables/useFormat'
import type { TraceResult, RepairOrder, AuditTrace } from '@/types'
import {
  DEFECT_TYPE_LABELS,
  SEVERITY_LABELS,
  SEVERITY_COLORS,
  SIDE_LABELS,
  REPAIR_STATUS_LABELS,
} from '@/types'

const route = useRoute()
const { formatDateTime, formatSize } = useFormat()

const DECISION_LABELS: Record<'repair' | 'observe', string> = {
  repair: '停机维修',
  observe: '观察',
}

const loading = ref(false)
const trace = ref<TraceResult | null>(null)
const closedOrders = ref<RepairOrder[]>([])
const repairId = ref('')
const previewVisible = ref(false)
const previewUrl = ref('')

function search(id?: string) {
  const target = (id || repairId.value || '').trim()
  if (!target) {
    ElMessage.warning('请输入或选择维修单编号')
    return
  }
  loading.value = true
  api
    .getTrace(target)
    .then((res) => {
      trace.value = res
    })
    .catch(() => {
      ElMessage.error('追溯信息加载失败')
      trace.value = null
    })
    .finally(() => {
      loading.value = false
    })
}

function openPreview(photoId: string) {
  previewUrl.value = api.photoUrl(photoId)
  previewVisible.value = true
}

function shaShort(sha?: string): string {
  return sha ? sha.slice(0, 16) : '—'
}

function hasDetail(node: AuditTrace): boolean {
  return !!node.detail && Object.keys(node.detail).length > 0
}

const repair = computed(() => trace.value?.repair_order)
const hasData = computed(() => !!trace.value)

onMounted(async () => {
  try {
    closedOrders.value = await api.getRepairOrders({ status: 'closed' })
  } catch {
    closedOrders.value = []
  }
  const q = route.query.repair as string | undefined
  if (q) {
    repairId.value = q
    search(q)
  }
})
</script>

<template>
  <div class="space-y-4">
    <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <div class="flex flex-wrap items-center gap-3">
        <span class="font-display text-base font-600 text-slate-200">追溯查询</span>
        <el-select
          v-model="repairId"
          placeholder="输入或选择已关闭维修单编号"
          filterable
          allow-create
          default-first-option
          class="w-80"
        >
          <el-option
            v-for="o in closedOrders"
            :key="o.id"
            :label="`${o.turbine?.code || ''} · ${o.id.slice(0, 8).toUpperCase()}`"
            :value="o.id"
          />
        </el-select>
        <el-button type="primary" :loading="loading" @click="search()">
          <el-icon class="mr-1"><Search /></el-icon>查询
        </el-button>
      </div>
    </el-card>

    <el-empty
      v-if="!hasData && !loading"
      description="请选择或输入维修单编号查询追溯信息"
    />

    <template v-if="hasData">
      <!-- a) 维修单信息 -->
      <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
        <template #header>
          <span class="font-display font-600 text-slate-200">维修单信息</span>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="机组">
            <span class="font-mono text-slate-300">{{ repair?.turbine?.code || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="决策">
            <el-tag effect="dark" size="small">
              {{ repair ? DECISION_LABELS[repair.decision] : '—' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag type="success" effect="dark" size="small">
              {{ repair ? REPAIR_STATUS_LABELS[repair.status] : '—' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="决策时间">
            {{ formatDateTime(repair?.decided_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="关闭时间">
            {{ formatDateTime(repair?.closed_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="关闭说明" :span="2">
            {{ repair?.closure_notes || '—' }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- b) 原始照片 -->
      <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
        <template #header>
          <span class="font-display font-600 text-slate-200">原始照片</span>
        </template>
        <div v-if="trace?.photos?.length" class="grid grid-cols-3 gap-3">
          <div
            v-for="p in trace.photos"
            :key="p.id"
            class="overflow-hidden rounded-lg border border-slate-700 bg-slate-950"
          >
            <img
              :src="api.photoUrl(p.id)"
              class="w-full h-32 object-cover cursor-pointer transition hover:opacity-80"
              alt="blade photo"
              @click="openPreview(p.id)"
            />
            <div class="p-2 text-xs text-slate-400 space-y-0.5">
              <div class="truncate text-slate-300">{{ p.original_filename }}</div>
              <div class="font-mono text-[10px] text-slate-500">{{ shaShort(p.sha256) }}</div>
              <div>{{ formatSize(p.file_size_bytes) }}</div>
            </div>
          </div>
        </div>
        <el-empty v-else description="无照片数据" />
      </el-card>

      <!-- c) 复核意见 -->
      <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
        <template #header>
          <span class="font-display font-600 text-slate-200">复核意见</span>
        </template>
        <div v-if="trace?.defects?.length" class="grid grid-cols-2 gap-3">
          <div
            v-for="d in trace.defects"
            :key="d.id"
            class="rounded-lg border border-slate-700 bg-slate-900/60 p-3"
          >
            <div class="flex items-center gap-2 mb-2">
              <el-tag effect="dark" size="small">{{ DEFECT_TYPE_LABELS[d.defect_type] }}</el-tag>
              <el-tag
                :type="(SEVERITY_COLORS[d.severity] || '') as any"
                effect="dark"
                size="small"
              >{{ SEVERITY_LABELS[d.severity] }}</el-tag>
              <span class="ml-auto text-xs text-slate-500">{{ d.blade_no }}# {{ SIDE_LABELS[d.side] }}</span>
            </div>
            <p class="text-sm text-slate-300 mb-2">{{ d.description || '无描述' }}</p>
            <div v-if="d.review_notes" class="rounded border border-sky-700/50 bg-sky-900/20 p-2 mb-2">
              <div class="text-xs font-medium text-sky-400 mb-1">复核备注</div>
              <p class="text-sm text-slate-200 whitespace-pre-wrap">{{ d.review_notes }}</p>
            </div>
            <div class="text-xs text-slate-500 flex justify-between">
              <span>{{ d.annotator?.display_name || '—' }}</span>
              <span>{{ formatDateTime(d.created_at) }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="无缺陷复核数据" />
      </el-card>

      <!-- d) 操作时间线 -->
      <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
        <template #header>
          <span class="font-display font-600 text-slate-200">操作时间线</span>
        </template>
        <el-timeline v-if="trace?.timeline?.length">
          <el-timeline-item
            v-for="(node, idx) in trace.timeline"
            :key="idx"
            :timestamp="formatDateTime(node.created_at)"
            placement="top"
          >
            <div class="flex items-center gap-2">
              <span class="font-600 text-slate-200">{{ node.action }}</span>
              <el-tag v-if="node.operator_role" size="small" effect="dark">
                {{ node.operator?.display_name || '系统' }}
              </el-tag>
            </div>
            <pre
              v-if="hasDetail(node)"
              class="mt-1 text-xs text-slate-400 bg-slate-950 rounded p-2 overflow-auto whitespace-pre-wrap"
            >{{ JSON.stringify(node.detail, null, 2) }}</pre>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="无操作记录" />
      </el-card>
    </template>

    <el-dialog v-model="previewVisible" title="照片预览" width="800px">
      <img :src="previewUrl" class="w-full max-h-[70vh] object-contain rounded" alt="preview" />
    </el-dialog>
  </div>
</template>
