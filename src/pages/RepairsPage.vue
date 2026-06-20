<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useFormat } from '@/composables/useFormat'
import { useUserStore } from '@/stores/user'
import type { RepairOrder, Turbine, Defect, RepairStatus, RepairDecision, DefectType, DefectSeverity } from '@/types'
import { DEFECT_TYPE_LABELS, SEVERITY_LABELS, SEVERITY_COLORS, SIDE_LABELS, REPAIR_STATUS_LABELS } from '@/types'

const router = useRouter()
const { formatDateTime } = useFormat()
const userStore = useUserStore()

const REPAIR_STATUS_COLORS: Record<RepairStatus, string> = { open: 'warning', in_progress: 'primary', closed: 'success' }
const DECISION_LABELS: Record<RepairDecision, string> = { repair: '停机维修', observe: '观察' }
const DECISION_COLORS: Record<RepairDecision, string> = { repair: 'danger', observe: 'info' }

const loading = ref(false)
const list = ref<RepairOrder[]>([])
const turbines = ref<Turbine[]>([])
const filterStatus = ref<RepairStatus | ''>('')
const filterTurbine = ref('')

const closeVisible = ref(false)
const closing = ref(false)
const closeTarget = ref<RepairOrder | null>(null)
const closureNotes = ref('')

const createVisible = ref(false)
const creating = ref(false)
const openDefects = ref<Defect[]>([])
const createForm = reactive({ defect_id: '', decision: 'repair' as RepairDecision })

async function loadTurbines() {
  turbines.value = await api.getTurbines()
}

async function loadList() {
  loading.value = true
  try {
    list.value = await api.getRepairOrders({
      status: filterStatus.value || undefined,
      turbine_id: filterTurbine.value || undefined,
    })
  } catch {
    ElMessage.error('维修单加载失败')
  } finally {
    loading.value = false
  }
}

function openClose(row: RepairOrder) {
  closeTarget.value = row
  closureNotes.value = ''
  closeVisible.value = true
}

async function handleClose() {
  if (!closeTarget.value) return
  if (!closureNotes.value.trim()) {
    ElMessage.warning('请填写关闭说明')
    return
  }
  closing.value = true
  try {
    await api.closeRepairOrder(closeTarget.value.id, closureNotes.value)
    ElMessage.success('维修单已关闭')
    closeVisible.value = false
    await loadList()
  } catch {
    ElMessage.error('关闭失败')
  } finally {
    closing.value = false
  }
}

async function openCreate() {
  createForm.defect_id = ''
  createForm.decision = 'repair'
  try {
    openDefects.value = await api.getDefects({ status: 'open' })
  } catch {
    ElMessage.error('缺陷加载失败')
  }
  createVisible.value = true
}

function defectOptionLabel(d: Defect): string {
  return `${d.turbine?.code || ''} ${d.blade_no}# ${SIDE_LABELS[d.side]} · ${DEFECT_TYPE_LABELS[d.defect_type]} ${SEVERITY_LABELS[d.severity]}`
}

async function handleCreate() {
  if (!createForm.defect_id) {
    ElMessage.warning('请选择关联缺陷')
    return
  }
  creating.value = true
  try {
    await api.createRepairOrder({ defect_id: createForm.defect_id, decision: createForm.decision })
    ElMessage.success('维修单已创建')
    createVisible.value = false
    await loadList()
  } catch {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

function goTrace(row: RepairOrder) {
  router.push(`/trace?repair=${row.id}`)
}

onMounted(async () => {
  await loadTurbines()
  await loadList()
})
</script>

<template>
  <div class="space-y-4">
    <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <div class="flex flex-wrap items-center gap-3">
        <span class="font-display text-base font-600 text-slate-200">维修单管理</span>
        <el-select v-model="filterStatus" placeholder="状态" clearable class="w-32" @change="loadList">
          <el-option label="全部" value="" />
          <el-option label="待处理" value="open" />
          <el-option label="处理中" value="in_progress" />
          <el-option label="已关闭" value="closed" />
        </el-select>
        <el-select v-model="filterTurbine" placeholder="机组" clearable filterable class="w-44" @change="loadList">
          <el-option v-for="t in turbines" :key="t.id" :label="t.code" :value="t.id" />
        </el-select>
        <div class="flex-1" />
        <el-button v-if="userStore.isSupervisor" type="primary" @click="openCreate">
          <el-icon class="mr-1"><Plus /></el-icon>新增维修单
        </el-button>
        <el-button @click="loadList"><el-icon class="mr-1"><Refresh /></el-icon>刷新</el-button>
      </div>
    </el-card>

    <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <el-table v-loading="loading" :data="list" header-cell-class-name="!bg-slate-800 !text-slate-300">
        <el-table-column label="机组" min-width="110">
          <template #default="{ row }"><span class="font-mono text-slate-300">{{ row.turbine?.code || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="关联缺陷" min-width="170">
          <template #default="{ row }">
            <template v-if="row.defect">
              <el-tag effect="dark" size="small">{{ DEFECT_TYPE_LABELS[row.defect.defect_type as DefectType] }}</el-tag>
              <el-tag :type="(SEVERITY_COLORS[row.defect.severity as DefectSeverity] || '') as any" effect="dark" size="small" class="ml-1">
                {{ SEVERITY_LABELS[row.defect.severity as DefectSeverity] }}
              </el-tag>
            </template>
            <span v-else class="text-slate-500">—</span>
          </template>
        </el-table-column>
        <el-table-column label="决策" min-width="110">
          <template #default="{ row }">
            <el-tag :type="DECISION_COLORS[row.decision as RepairDecision] as any" effect="dark" size="small">
              {{ DECISION_LABELS[row.decision as RepairDecision] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="100">
          <template #default="{ row }">
            <el-tag :type="REPAIR_STATUS_COLORS[row.status as RepairStatus] as any" effect="dark" size="small">
              {{ REPAIR_STATUS_LABELS[row.status as RepairStatus] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="决策时间" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.decided_at) }}</template>
        </el-table-column>
        <el-table-column label="关闭时间" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.closed_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button v-if="userStore.isSupervisor && row.status !== 'closed'" type="warning" link size="small" @click="openClose(row as RepairOrder)">关闭</el-button>
            <el-button type="primary" link size="small" @click="goTrace(row as RepairOrder)">追溯</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无维修单数据" /></template>
      </el-table>
    </el-card>

    <el-dialog v-model="closeVisible" title="关闭维修单" width="520px">
      <el-form label-width="90px">
        <el-form-item label="关闭说明">
          <el-input v-model="closureNotes" type="textarea" :rows="4" placeholder="请填写关闭说明（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeVisible = false">取消</el-button>
        <el-button type="primary" :loading="closing" @click="handleClose">确认关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createVisible" title="新增维修单" width="560px">
      <el-form label-width="90px">
        <el-form-item label="关联缺陷">
          <el-select v-model="createForm.defect_id" placeholder="选择待处理缺陷" filterable class="w-full">
            <el-option v-for="d in openDefects" :key="d.id" :label="defectOptionLabel(d)" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="决策">
          <el-radio-group v-model="createForm.decision">
            <el-radio-button value="repair">停机维修</el-radio-button>
            <el-radio-button value="observe">观察</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
