<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useFormat } from '@/composables/useFormat'
import { useUserStore } from '@/stores/user'
import type { Turbine, RoutePlan, Inspection, InspectionStatus } from '@/types'
import { INSPECTION_STATUS_LABELS } from '@/types'

const router = useRouter()
const userStore = useUserStore()
const { formatDate, formatDateTime } = useFormat()

const loading = ref(false)
const inspections = ref<Inspection[]>([])
const turbines = ref<Turbine[]>([])
const routePlans = ref<RoutePlan[]>([])

const filterTurbine = ref<string | undefined>(undefined)
const filterStatus = ref<InspectionStatus | undefined>(undefined)

const statusOptions: { value: InspectionStatus; label: string }[] = [
  { value: 'draft', label: INSPECTION_STATUS_LABELS.draft },
  { value: 'submitted', label: INSPECTION_STATUS_LABELS.submitted },
]

function statusTagType(status: InspectionStatus) {
  return status === 'draft' ? 'info' : 'success'
}

async function loadInspections() {
  loading.value = true
  try {
    inspections.value = await api.getInspections({
      turbine_id: filterTurbine.value,
      status: filterStatus.value,
    })
  } finally {
    loading.value = false
  }
}

async function loadTurbines() {
  turbines.value = await api.getTurbines()
}

// ---- 发起巡检对话框 ----
const dialogVisible = ref(false)
const submitting = ref(false)
const form = ref({
  turbine_id: '' as string,
  route_plan_id: undefined as string | undefined,
  inspection_date: '' as string,
})

function openCreate() {
  form.value = { turbine_id: '', route_plan_id: undefined, inspection_date: '' }
  routePlans.value = []
  dialogVisible.value = true
}

async function onTurbineChange() {
  form.value.route_plan_id = undefined
  if (form.value.turbine_id) {
    routePlans.value = await api.getRoutePlans({ turbine_id: form.value.turbine_id })
  }
}

async function handleCreate() {
  if (!form.value.turbine_id) {
    ElMessage.warning('请选择机组')
    return
  }
  submitting.value = true
  try {
    const created = await api.createInspection({
      turbine_id: form.value.turbine_id,
      route_plan_id: form.value.route_plan_id || undefined,
      inspection_date: form.value.inspection_date || undefined,
    })
    ElMessage.success('巡检已创建')
    dialogVisible.value = false
    router.push(`/inspections/${created.id}`)
  } finally {
    submitting.value = false
  }
}

function viewRow(row: Inspection) {
  router.push(`/inspections/${row.id}`)
}

onMounted(async () => {
  await Promise.all([loadTurbines(), loadInspections()])
})
</script>

<template>
  <div class="space-y-4">
    <!-- 头部 -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="font-display text-xl font-600 text-slate-100">巡检管理</h1>
      <div class="flex flex-wrap items-center gap-3">
        <el-select
          v-model="filterTurbine"
          placeholder="全部机组"
          clearable
          class="w-48"
          @change="loadInspections"
        >
          <el-option
            v-for="t in turbines"
            :key="t.id"
            :label="`${t.code} · ${t.name}`"
            :value="t.id"
          />
        </el-select>
        <el-select
          v-model="filterStatus"
          placeholder="全部状态"
          clearable
          class="w-36"
          @change="loadInspections"
        >
          <el-option
            v-for="s in statusOptions"
            :key="s.value"
            :label="s.label"
            :value="s.value"
          />
        </el-select>
        <el-button
          v-if="userStore.isInspector"
          type="primary"
          @click="openCreate"
        >
          发起巡检
        </el-button>
      </div>
    </div>

    <!-- 列表 -->
    <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <el-table
        v-loading="loading"
        :data="inspections"
        stripe
        class="w-full"
        header-cell-class-name="!bg-slate-800 !text-slate-300"
      >
        <el-table-column label="机组" min-width="130">
          <template #default="{ row }">
            <span class="font-mono text-wind-300">{{ row.turbine?.code || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="巡检日期" min-width="110">
          <template #default="{ row }">
            {{ formatDate(row.inspection_date) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="dark" size="small">
              {{ INSPECTION_STATUS_LABELS[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="照片数" min-width="80" align="center">
          <template #default="{ row }">{{ row.photo_count ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="缺陷数" min-width="80" align="center">
          <template #default="{ row }">
            <span :class="row.defect_count ? 'text-amber-400 font-600' : 'text-slate-500'">
              {{ row.defect_count ?? 0 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewRow(row as Inspection)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 发起巡检对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="发起巡检"
      width="480px"
      class="!bg-slate-900"
    >
      <el-form :model="form" label-width="90px" label-position="right">
        <el-form-item label="机组" required>
          <el-select
            v-model="form.turbine_id"
            placeholder="请选择机组"
            class="w-full"
            @change="onTurbineChange"
          >
            <el-option
              v-for="t in turbines"
              :key="t.id"
              :label="`${t.code} · ${t.name}`"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="航线计划">
          <el-select
            v-model="form.route_plan_id"
            placeholder="可选"
            clearable
            class="w-full"
            :disabled="!form.turbine_id"
          >
            <el-option
              v-for="r in routePlans"
              :key="r.id"
              :label="r.name"
              :value="r.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="巡检日期">
          <el-date-picker
            v-model="form.inspection_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            class="!w-full"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>
