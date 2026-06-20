<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useFormat } from '@/composables/useFormat'
import { useUserStore } from '@/stores/user'
import type { GridConnection, Turbine, GridStatus } from '@/types'
import { GRID_STATUS_LABELS, GRID_STATUS_COLORS } from '@/types'

const { formatDateTime, shortId } = useFormat()
const userStore = useUserStore()

const loading = ref(false)
const list = ref<GridConnection[]>([])
const turbines = ref<Turbine[]>([])
const filterStatus = ref<GridStatus | ''>('')
const filterTurbine = ref('')
const confirmingId = ref('')

const frozenCount = computed(
  () => list.value.filter((x) => x.status === 'frozen').length,
)

async function loadTurbines() {
  turbines.value = await api.getTurbines()
}

async function loadList() {
  loading.value = true
  try {
    list.value = await api.getGridConnections({
      status: filterStatus.value || undefined,
      turbine_id: filterTurbine.value || undefined,
    })
  } catch {
    ElMessage.error('并网记录加载失败')
  } finally {
    loading.value = false
  }
}

async function handleConfirm(row: GridConnection) {
  confirmingId.value = row.id
  try {
    await api.confirmGrid(row.id)
    ElMessage.success('已确认并网')
    await loadList()
  } catch {
    ElMessage.error('确认失败')
  } finally {
    confirmingId.value = ''
  }
}

onMounted(async () => {
  await loadTurbines()
  await loadList()
})
</script>

<template>
  <div class="space-y-4">
    <el-alert
      v-if="frozenCount > 0"
      type="warning"
      :closable="false"
      show-icon
      class="!bg-amber-500/10 !border-amber-500/40"
    >
      <template #title>
        <span class="text-amber-300">
          当前有 {{ frozenCount }} 条并网记录处于冻结状态：缺陷等级升高已冻结并网，需关闭关联维修单后解除。
        </span>
      </template>
    </el-alert>

    <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <div class="flex flex-wrap items-center gap-3">
        <span class="font-display text-base font-600 text-slate-200">并网确认</span>
        <el-select
          v-model="filterStatus"
          placeholder="状态"
          clearable
          class="w-32"
          @change="loadList"
        >
          <el-option label="全部" value="" />
          <el-option label="待确认" value="pending" />
          <el-option label="已冻结" value="frozen" />
          <el-option label="已确认" value="confirmed" />
        </el-select>
        <el-select
          v-model="filterTurbine"
          placeholder="机组"
          clearable
          filterable
          class="w-44"
          @change="loadList"
        >
          <el-option
            v-for="t in turbines"
            :key="t.id"
            :label="t.code"
            :value="t.id"
          />
        </el-select>
        <div class="flex-1" />
        <el-button @click="loadList">
          <el-icon class="mr-1"><Refresh /></el-icon>刷新
        </el-button>
      </div>
    </el-card>

    <el-card class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <el-table
        v-loading="loading"
        :data="list"
        header-cell-class-name="!bg-slate-800 !text-slate-300"
      >
        <el-table-column label="机组" min-width="120">
          <template #default="{ row }">
            <span class="font-mono text-slate-300">{{ row.turbine?.code || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="110">
          <template #default="{ row }">
            <el-tag :type="GRID_STATUS_COLORS[row.status as GridStatus] as any" effect="dark" size="small">
              {{ GRID_STATUS_LABELS[row.status as GridStatus] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="冻结原因" min-width="180">
          <template #default="{ row }">
            <span class="text-slate-400 line-clamp-1">{{ row.frozen_reason || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="关联缺陷" min-width="120">
          <template #default="{ row }">
            <span class="font-mono text-wind-300">{{ shortId(row.frozen_by_defect_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="确认时间" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.confirmed_at) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending' && userStore.isSupervisor"
              type="success"
              link
              size="small"
              :loading="confirmingId === row.id"
              @click="handleConfirm(row as GridConnection)"
            >确认并网</el-button>
            <el-tooltip
              v-else-if="row.status === 'frozen'"
              :content="row.frozen_reason || '缺陷冻结'"
              placement="top"
            >
              <el-button type="danger" link size="small" disabled>已冻结</el-button>
            </el-tooltip>
            <span v-else class="text-emerald-400 text-sm">已确认</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无并网记录" />
        </template>
      </el-table>
    </el-card>
  </div>
</template>
