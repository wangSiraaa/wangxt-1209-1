<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useFormat } from '@/composables/useFormat'
import { useUserStore } from '@/stores/user'
import type { Defect, Turbine, Inspection, BladePhoto, DefectType, DefectSeverity, DefectStatus } from '@/types'
import { DEFECT_TYPE_LABELS, SEVERITY_LABELS, SEVERITY_COLORS, SIDE_LABELS } from '@/types'

const { formatDateTime } = useFormat()
const userStore = useUserStore()

const DEFECT_STATUS_LABELS: Record<DefectStatus, string> = { open: '待处理', resolved: '已解决' }
const DEFECT_STATUS_COLORS: Record<DefectStatus, string> = { open: 'warning', resolved: 'success' }
const SEV_RANK: Record<DefectSeverity, number> = { L1: 1, L2: 2, L3: 3, L4: 4 }

const loading = ref(false)
const list = ref<Defect[]>([])
const turbines = ref<Turbine[]>([])
const filterStatus = ref<DefectStatus | ''>('')
const filterTurbine = ref('')
const filterType = ref<DefectType | ''>('')

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editing = ref<Defect | null>(null)
const saving = ref(false)
const inspections = ref<Inspection[]>([])
const photos = ref<BladePhoto[]>([])
const loadingPhotos = ref(false)
const form = reactive({
  inspection_id: '', photo_id: '', blade_no: 0,
  side: '' as BladePhoto['side'] | '',
  defect_type: 'crack' as DefectType,
  severity: 'L1' as DefectSeverity,
  description: '',
  review_notes: '',
})

const showEscalationNote = computed(
  () => dialogMode.value === 'edit' && !!editing.value && SEV_RANK[form.severity] > SEV_RANK[editing.value.severity],
)

function resetForm() {
  form.inspection_id = ''; form.photo_id = ''; form.blade_no = 0; form.side = ''
  form.defect_type = 'crack'; form.severity = 'L1'; form.description = ''; form.review_notes = ''
  inspections.value = []; photos.value = []
}

async function loadTurbines() {
  turbines.value = await api.getTurbines()
}

async function loadDefects() {
  loading.value = true
  try {
    list.value = await api.getDefects({
      status: filterStatus.value || undefined,
      turbine_id: filterTurbine.value || undefined,
      defect_type: filterType.value || undefined,
    })
  } catch {
    ElMessage.error('缺陷列表加载失败')
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  resetForm()
  dialogMode.value = 'create'
  editing.value = null
  try {
    inspections.value = await api.getInspections({ status: 'submitted' })
  } catch {
    ElMessage.error('巡检记录加载失败')
  }
  dialogVisible.value = true
}

async function onInspectionChange(id: string) {
  form.photo_id = ''; form.blade_no = 0; form.side = ''; photos.value = []
  if (!id) return
  loadingPhotos.value = true
  try {
    photos.value = (await api.getInspection(id)).photos || []
  } catch {
    ElMessage.error('照片加载失败')
  } finally {
    loadingPhotos.value = false
  }
}

function onPhotoChange(id: string) {
  const p = photos.value.find((x) => x.id === id)
  if (p) {
    form.blade_no = p.blade_no
    form.side = p.side
  }
}

function openEdit(row: Defect) {
  resetForm()
  dialogMode.value = 'edit'
  editing.value = row
  form.defect_type = row.defect_type
  form.severity = row.severity
  form.description = row.description || ''
  form.review_notes = row.review_notes || ''
  form.photo_id = row.photo_id
  form.blade_no = row.blade_no
  form.side = row.side
  dialogVisible.value = true
}

async function handleSave() {
  if (dialogMode.value === 'create') {
    if (!form.inspection_id || !form.photo_id || !form.side) {
      ElMessage.warning('请选择巡检记录与照片')
      return
    }
    saving.value = true
    try {
      await api.createDefect({
        inspection_id: form.inspection_id,
        photo_id: form.photo_id,
        blade_no: form.blade_no,
        side: form.side as string,
        defect_type: form.defect_type,
        severity: form.severity,
        description: form.description || undefined,
        review_notes: form.review_notes || undefined,
      })
      ElMessage.success('缺陷标注成功')
      dialogVisible.value = false
      await loadDefects()
    } catch {
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  } else {
    if (!editing.value) return
    saving.value = true
    try {
      await api.updateDefect(editing.value.id, {
        severity: form.severity,
        description: form.description,
        review_notes: form.review_notes,
      })
      ElMessage.success('缺陷已更新')
      dialogVisible.value = false
      await loadDefects()
    } catch {
      ElMessage.error('更新失败')
    } finally {
      saving.value = false
    }
  }
}

onMounted(async () => {
  await loadTurbines()
  await loadDefects()
})
</script>

<template>
  <div class="space-y-4">
    <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <div class="flex flex-wrap items-center gap-3">
        <span class="font-display text-base font-600 text-slate-200">缺陷复核</span>
        <el-select v-model="filterStatus" placeholder="状态" clearable class="w-32" @change="loadDefects">
          <el-option label="全部" value="" />
          <el-option label="待处理" value="open" />
          <el-option label="已解决" value="resolved" />
        </el-select>
        <el-select v-model="filterTurbine" placeholder="机组" clearable filterable class="w-44" @change="loadDefects">
          <el-option v-for="t in turbines" :key="t.id" :label="t.code" :value="t.id" />
        </el-select>
        <el-select v-model="filterType" placeholder="缺陷类型" clearable class="w-32" @change="loadDefects">
          <el-option v-for="(lbl, key) in DEFECT_TYPE_LABELS" :key="key" :label="lbl" :value="key" />
        </el-select>
        <div class="flex-1" />
        <el-button v-if="userStore.isAnnotator" type="primary" @click="openCreate">
          <el-icon class="mr-1"><Plus /></el-icon>新增缺陷
        </el-button>
        <el-button @click="loadDefects"><el-icon class="mr-1"><Refresh /></el-icon>刷新</el-button>
      </div>
    </el-card>

    <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <el-table v-loading="loading" :data="list" header-cell-class-name="!bg-slate-800 !text-slate-300">
        <el-table-column label="缺陷类型" min-width="100">
          <template #default="{ row }">
            <el-tag effect="dark" size="small">{{ DEFECT_TYPE_LABELS[row.defect_type as DefectType] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="等级" min-width="110">
          <template #default="{ row }">
            <el-tag :type="(SEVERITY_COLORS[row.severity as DefectSeverity] || '') as any" effect="dark" size="small">
              {{ SEVERITY_LABELS[row.severity as DefectSeverity] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="机组" min-width="110">
          <template #default="{ row }"><span class="font-mono text-slate-300">{{ row.turbine?.code || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="叶片" min-width="80"><template #default="{ row }">{{ row.blade_no }}#</template></el-table-column>
        <el-table-column label="位置" min-width="90">
          <template #default="{ row }">{{ SIDE_LABELS[row.side as BladePhoto['side']] }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="90">
          <template #default="{ row }">
            <el-tag :type="DEFECT_STATUS_COLORS[row.status as DefectStatus] as any" effect="dark" size="small">
              {{ DEFECT_STATUS_LABELS[row.status as DefectStatus] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标注时间" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button v-if="userStore.isAnnotator" type="primary" link size="small" @click="openEdit(row as Defect)">编辑</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无缺陷数据" /></template>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? '新增缺陷标注' : '编辑缺陷'" width="640px">
      <div class="space-y-4">
        <el-form v-if="dialogMode === 'create'" label-width="80px">
          <el-form-item label="巡检记录">
            <el-select v-model="form.inspection_id" placeholder="选择已提交巡检" filterable class="w-full" @change="onInspectionChange">
              <el-option v-for="i in inspections" :key="i.id" :label="`${i.inspection_date} (${i.turbine?.code || ''})`" :value="i.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="照片">
            <el-select v-model="form.photo_id" placeholder="选择照片" filterable :loading="loadingPhotos" class="w-full" @change="onPhotoChange">
              <el-option v-for="p in photos" :key="p.id" :label="`${p.blade_no}# ${SIDE_LABELS[p.side]} · ${p.original_filename}`" :value="p.id" />
            </el-select>
          </el-form-item>
        </el-form>

        <div v-if="form.photo_id" class="overflow-hidden rounded-lg border border-slate-700 bg-slate-950">
          <img :src="api.photoUrl(form.photo_id)" class="max-h-64 w-full object-contain" alt="defect photo" />
        </div>

        <el-form label-width="80px">
          <el-form-item label="缺陷类型">
            <el-select v-model="form.defect_type" :disabled="dialogMode === 'edit'" class="w-full">
              <el-option v-for="(lbl, key) in DEFECT_TYPE_LABELS" :key="key" :label="lbl" :value="key" />
            </el-select>
          </el-form-item>
          <el-form-item label="等级">
            <el-select v-model="form.severity" class="w-full">
              <el-option v-for="(lbl, key) in SEVERITY_LABELS" :key="key" :label="lbl" :value="key" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="showEscalationNote" label=" ">
            <el-alert type="warning" :closable="false" show-icon title="等级升高将自动冻结并网确认" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="form.description" type="textarea" :rows="2" placeholder="缺陷描述（可选）" />
          </el-form-item>
          <el-form-item label="复核备注">
            <el-input v-model="form.review_notes" type="textarea" :rows="3" placeholder="复核说明与建议处理方式（可选）" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
