<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { Plus, Edit } from '@element-plus/icons-vue'
import { api } from '@/api'
import { useFormat } from '@/composables/useFormat'
import { useUserStore } from '@/stores/user'
import type { Turbine, TurbineStatus } from '@/types'
import { TURBINE_STATUS_LABELS, TURBINE_STATUS_COLORS } from '@/types'

const { formatDate } = useFormat()
const userStore = useUserStore()

const loading = ref(false)
const turbines = ref<Turbine[]>([])

const statusOptions = (Object.keys(TURBINE_STATUS_LABELS) as TurbineStatus[]).map(
  (status) => ({ value: status, label: TURBINE_STATUS_LABELS[status] }),
)

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const submitting = ref(false)
const formRef = ref<FormInstance>()

function defaultForm(): Turbine {
  return {
    id: '',
    code: '',
    name: '',
    farm_name: '',
    model: '',
    rated_power_kw: 0,
    blade_count: 3,
    status: 'operating',
    latitude: undefined,
    longitude: undefined,
    created_at: '',
    updated_at: '',
  }
}

const form = reactive<Turbine>(defaultForm())

const rules = {
  code: [{ required: true, message: '请输入编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  farm_name: [{ required: true, message: '请输入风电场', trigger: 'blur' }],
}

async function loadTurbines() {
  loading.value = true
  try {
    turbines.value = await api.getTurbines()
  } catch {
    ElMessage.error('机组列表加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialogMode.value = 'create'
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

function openEdit(row: Turbine) {
  dialogMode.value = 'edit'
  Object.assign(form, defaultForm(), row)
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const payload: Partial<Turbine> = {
        code: form.code,
        name: form.name,
        farm_name: form.farm_name,
        model: form.model,
        rated_power_kw: Number(form.rated_power_kw),
        blade_count: Number(form.blade_count),
        status: form.status,
        latitude: form.latitude,
        longitude: form.longitude,
      }
      if (dialogMode.value === 'create') {
        await api.createTurbine(payload)
        ElMessage.success('机组创建成功')
      } else {
        await api.updateTurbine(form.id, payload)
        ElMessage.success('机组更新成功')
      }
      dialogVisible.value = false
      await loadTurbines()
    } catch {
      ElMessage.error(dialogMode.value === 'create' ? '机组创建失败' : '机组更新失败')
    } finally {
      submitting.value = false
    }
  })
}

onMounted(loadTurbines)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="font-display text-lg font-600 text-slate-200">机组管理</h2>
      <el-button v-if="userStore.isInspector" type="primary" :icon="Plus" @click="openCreate">
        新建机组
      </el-button>
    </div>

    <el-card class="!bg-slate-900/60 !border-slate-800" body-class="!p-0" shadow="never">
      <el-table
        v-loading="loading"
        :data="turbines"
        header-cell-class-name="!bg-slate-800 !text-slate-300"
        style="width: 100%"
      >
        <el-table-column prop="code" label="编号" min-width="120">
          <template #default="{ row }">
            <span class="font-mono text-wind-300">{{ row.code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column prop="farm_name" label="风电场" min-width="120" />
        <el-table-column prop="model" label="机型" min-width="120" />
        <el-table-column label="额定功率" min-width="110">
          <template #default="{ row }">
            <span class="font-mono text-slate-300">{{ row.rated_power_kw }}kW</span>
          </template>
        </el-table-column>
        <el-table-column prop="blade_count" label="叶片数" width="80" align="center" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag
              :type="TURBINE_STATUS_COLORS[row.status as TurbineStatus] as any"
              effect="dark"
              size="small"
            >
              {{ TURBINE_STATUS_LABELS[row.status as TurbineStatus] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="110">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="userStore.isInspector"
              link
              type="primary"
              :icon="Edit"
              @click="openEdit(row as Turbine)"
            >
              编辑
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无机组数据" :image-size="80" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建机组' : '编辑机组'"
      width="560px"
      append-to-body
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="90px"
        label-position="right"
      >
        <el-form-item label="编号" prop="code">
          <el-input v-model="form.code" placeholder="如 TBN-001" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="机组名称" />
        </el-form-item>
        <el-form-item label="风电场" prop="farm_name">
          <el-input v-model="form.farm_name" placeholder="所属风电场" />
        </el-form-item>
        <el-form-item label="机型" prop="model">
          <el-input v-model="form.model" placeholder="机组型号" />
        </el-form-item>
        <div class="flex gap-4">
          <el-form-item label="额定功率" prop="rated_power_kw" class="flex-1">
            <el-input-number
              v-model="form.rated_power_kw"
              :min="0"
              :step="100"
              controls-position="right"
              class="!w-full"
            />
          </el-form-item>
          <el-form-item label="叶片数" prop="blade_count" class="flex-1">
            <el-input-number
              v-model="form.blade_count"
              :min="1"
              :max="12"
              controls-position="right"
              class="!w-full"
            />
          </el-form-item>
        </div>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" class="!w-full">
            <el-option
              v-for="opt in statusOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <div class="flex gap-4">
          <el-form-item label="纬度" prop="latitude" class="flex-1">
            <el-input-number
              v-model="form.latitude"
              :precision="6"
              :step="0.0001"
              :controls="false"
              placeholder="39.123456"
              class="!w-full"
            />
          </el-form-item>
          <el-form-item label="经度" prop="longitude" class="flex-1">
            <el-input-number
              v-model="form.longitude"
              :precision="6"
              :step="0.0001"
              :controls="false"
              placeholder="116.123456"
              class="!w-full"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
