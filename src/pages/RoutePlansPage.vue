<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import { api } from '@/api'
import { useFormat } from '@/composables/useFormat'
import { useUserStore } from '@/stores/user'
import type { RoutePlan, Turbine } from '@/types'

const { formatDate } = useFormat()
const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const routes = ref<RoutePlan[]>([])
const turbines = ref<Turbine[]>([])
const filterTurbineId = ref('')

const turbineMap = computed(
  () => new Map(turbines.value.map((t) => [t.id, t])),
)

function turbineCode(id: string): string {
  return turbineMap.value.get(id)?.code ?? '—'
}

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()

function defaultForm(): RoutePlan {
  return {
    id: '',
    turbine_id: '',
    name: '',
    description: '',
    waypoint_count: 0,
    altitude_m: 30,
    created_at: '',
    updated_at: '',
  }
}

const form = reactive<RoutePlan>(defaultForm())

const rules = {
  name: [{ required: true, message: '请输入航线名称', trigger: 'blur' }],
  turbine_id: [{ required: true, message: '请选择关联机组', trigger: 'change' }],
}

async function loadTurbines() {
  try {
    turbines.value = await api.getTurbines()
  } catch {
    ElMessage.error('机组数据加载失败')
  }
}

async function loadRoutes() {
  loading.value = true
  try {
    routes.value = await api.getRoutePlans({
      turbine_id: filterTurbineId.value || undefined,
    })
  } catch {
    ElMessage.error('航线列表加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialogMode.value = 'create'
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

function openEdit(row: RoutePlan) {
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
      const payload: Partial<RoutePlan> = {
        name: form.name,
        turbine_id: form.turbine_id,
        description: form.description,
        waypoint_count: Number(form.waypoint_count),
        altitude_m: Number(form.altitude_m),
      }
      if (dialogMode.value === 'create') {
        await api.createRoutePlan(payload)
        ElMessage.success('航线创建成功')
      } else {
        await api.updateRoutePlan(form.id, payload)
        ElMessage.success('航线更新成功')
      }
      dialogVisible.value = false
      await loadRoutes()
    } catch {
      ElMessage.error(dialogMode.value === 'create' ? '航线创建失败' : '航线更新失败')
    } finally {
      submitting.value = false
    }
  })
}

async function handleDelete(row: RoutePlan) {
  try {
    await api.deleteRoutePlan(row.id)
    ElMessage.success('航线已删除')
    await loadRoutes()
  } catch {
    ElMessage.error('航线删除失败')
  }
}

onMounted(async () => {
  await loadTurbines()
  await loadRoutes()
})
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="font-display text-lg font-600 text-slate-200">航线计划</h2>
      <div class="flex items-center gap-3">
        <el-select
          v-model="filterTurbineId"
          placeholder="全部机组"
          class="w-48"
          @change="loadRoutes"
        >
          <el-option label="全部机组" value="" />
          <el-option
            v-for="t in turbines"
            :key="t.id"
            :label="t.code"
            :value="t.id"
          />
        </el-select>
        <el-button
          v-if="userStore.isInspector"
          type="primary"
          :icon="Plus"
          @click="openCreate"
        >
          新建航线
        </el-button>
      </div>
    </div>

    <el-card class="!bg-slate-900/60 !border-slate-800" body-class="!p-0" shadow="never">
      <el-table
        v-loading="loading"
        :data="routes"
        header-cell-class-name="!bg-slate-800 !text-slate-300"
        style="width: 100%"
      >
        <el-table-column prop="name" label="航线名称" min-width="160">
          <template #default="{ row }">
            <span class="text-slate-200">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="关联机组" min-width="130">
          <template #default="{ row }">
            <span class="font-mono text-wind-300">{{ turbineCode(row.turbine_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="waypoint_count" label="航点数" width="90" align="center" />
        <el-table-column label="巡检高度" min-width="110">
          <template #default="{ row }">
            <span class="font-mono text-slate-300">{{ row.altitude_m }}m</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="120">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <template v-if="userStore.isInspector">
              <el-button
                link
                type="primary"
                :icon="Edit"
                @click="openEdit(row as RoutePlan)"
              >
                编辑
              </el-button>
              <el-popconfirm
                title="确定删除该航线吗？"
                confirm-button-text="删除"
                cancel-button-text="取消"
                @confirm="handleDelete(row as RoutePlan)"
              >
                <template #reference>
                  <el-button link type="danger" :icon="Delete">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
            <span v-else class="text-xs text-slate-600">—</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无航线数据" :image-size="80" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新建航线' : '编辑航线'"
      width="520px"
      append-to-body
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="90px"
        label-position="right"
      >
        <el-form-item label="航线名称" prop="name">
          <el-input v-model="form.name" placeholder="如 迎风面标准巡检航线" />
        </el-form-item>
        <el-form-item label="关联机组" prop="turbine_id">
          <el-select v-model="form.turbine_id" placeholder="选择机组" class="!w-full">
            <el-option
              v-for="t in turbines"
              :key="t.id"
              :label="`${t.code} · ${t.name}`"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="航线说明（选填）"
          />
        </el-form-item>
        <div class="flex gap-4">
          <el-form-item label="航点数" prop="waypoint_count" class="flex-1">
            <el-input-number
              v-model="form.waypoint_count"
              :min="0"
              :step="1"
              controls-position="right"
              class="!w-full"
            />
          </el-form-item>
          <el-form-item label="巡检高度" prop="altitude_m" class="flex-1">
            <el-input-number
              v-model="form.altitude_m"
              :min="0"
              :step="5"
              controls-position="right"
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
