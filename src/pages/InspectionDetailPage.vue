<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Camera } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import { api } from '@/api'
import { useFormat } from '@/composables/useFormat'
import { useUserStore } from '@/stores/user'
import type { InspectionDetail, BladePhoto, BladeSide } from '@/types'
import { SIDE_LABELS, SIDE_ORDER, INSPECTION_STATUS_LABELS } from '@/types'

const route = useRoute()
const userStore = useUserStore()
const { formatDate, formatSize } = useFormat()

const id = route.params.id as string
const loading = ref(false)
const detail = ref<InspectionDetail | null>(null)
const submitting = ref(false)

const bladeCount = computed(() => detail.value?.turbine?.blade_count || 3)
const bladeNos = computed(() =>
  Array.from({ length: bladeCount.value }, (_, i) => i + 1),
)
const isDraft = computed(() => detail.value?.status === 'draft')
const isSubmitted = computed(() => detail.value?.status === 'submitted')

function photoOf(bladeNo: number, side: BladeSide): BladePhoto | undefined {
  return detail.value?.photos.find(
    (p) => p.blade_no === bladeNo && p.side === side,
  )
}

// 缺失面描述列表
const missingSides = computed(() => {
  const d = detail.value
  if (!d) return [] as string[]
  const miss: string[] = []
  for (const no of bladeNos.value) {
    for (const side of SIDE_ORDER) {
      if (!d.coverage?.[no]?.[side]) {
        miss.push(`#${no} ${SIDE_LABELS[side]}`)
      }
    }
  }
  return miss
})

const completedBlades = computed(() => {
  const d = detail.value
  if (!d) return 0
  return bladeNos.value.filter((no) =>
    SIDE_ORDER.every((s) => d.coverage?.[no]?.[s]),
  ).length
})

const coverageSummary = computed(() => {
  const total = bladeCount.value
  const done = completedBlades.value
  if (done === total) return `${done}/${total} 叶片已完成三面采集`
  return `${done}/${total} 叶片完成`
})

async function refresh() {
  if (!id) return
  loading.value = true
  try {
    detail.value = await api.getInspection(id)
  } finally {
    loading.value = false
  }
}

async function handleUpload(bladeNo: number, side: BladeSide, file: File) {
  try {
    await api.uploadPhoto(id, bladeNo, side, file)
    ElMessage.success(`${SIDE_LABELS[side]} 照片已上传`)
    await refresh()
  } catch {
    // 错误已由请求拦截器提示
  }
}

function onFileChange(bladeNo: number, side: BladeSide, file: UploadFile) {
  if (!file?.raw) return
  handleUpload(bladeNo, side, file.raw)
}

async function handleDelete(photo: BladePhoto) {
  try {
    await api.deletePhoto(photo.id)
    ElMessage.success('照片已删除')
    await refresh()
  } catch {
    // ignore
  }
}

async function handleSubmit() {
  submitting.value = true
  try {
    await api.submitInspection(id)
    ElMessage.success('巡检已提交')
    await refresh()
  } finally {
    submitting.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <div v-loading="loading" class="space-y-4">
    <!-- 顶部信息卡 -->
    <el-card v-if="detail" class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="space-y-1">
          <div class="flex items-center gap-3">
            <span class="font-display text-lg font-600 text-slate-100">
              {{ detail.turbine?.name || '—' }}
            </span>
            <span class="font-mono text-sm text-wind-300">
              {{ detail.turbine?.code }}
            </span>
            <el-tag :type="isSubmitted ? 'success' : 'info'" effect="dark" size="small">
              {{ INSPECTION_STATUS_LABELS[detail.status] }}
            </el-tag>
          </div>
          <div class="text-sm text-slate-400">
            巡检日期：{{ formatDate(detail.inspection_date) }}
          </div>
        </div>
        <div class="text-right">
          <div class="font-display text-2xl font-700 text-wind-300">
            {{ coverageSummary }}
          </div>
          <div class="text-xs text-slate-500">覆盖进度</div>
        </div>
      </div>
    </el-card>

    <!-- 三面照片采集 -->
    <el-card v-if="detail" class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <template #header>
        <span class="font-display font-600 text-slate-200">三面照片采集</span>
      </template>
      <div class="space-y-3">
        <div
          v-for="no in bladeNos"
          :key="no"
          class="grid grid-cols-3 gap-3"
        >
          <el-card
            v-for="side in SIDE_ORDER"
            :key="side"
            class="!bg-slate-800/40 !border-slate-700"
            shadow="never"
            :body-style="{ padding: '12px' }"
          >
            <div class="mb-2 flex items-center justify-between">
              <span class="text-sm font-600 text-slate-300">
                #{{ no }} · {{ SIDE_LABELS[side] }}
              </span>
              <el-tag
                v-if="detail.coverage?.[no]?.[side]"
                type="success"
                size="small"
                effect="dark"
              >
                已采集
              </el-tag>
              <el-tag v-else type="info" size="small" effect="dark">待采集</el-tag>
            </div>

            <!-- 已有照片 -->
            <div v-if="photoOf(no, side)" class="space-y-1">
              <img
                :src="api.photoUrl(photoOf(no, side)!.id)"
                class="w-full h-32 object-cover rounded"
                :alt="photoOf(no, side)!.original_filename"
              />
              <div class="flex items-center justify-between gap-2">
                <div class="min-w-0">
                  <div class="truncate text-xs text-slate-400">
                    {{ photoOf(no, side)!.original_filename }}
                  </div>
                  <div class="font-mono text-xs text-slate-500">
                    {{ formatSize(photoOf(no, side)!.file_size_bytes) }}
                  </div>
                </div>
                <el-button
                  v-if="isDraft"
                  type="danger"
                  link
                  size="small"
                  @click="handleDelete(photoOf(no, side)!)"
                >
                  删除
                </el-button>
              </div>
            </div>

            <!-- 上传 -->
            <el-upload
              v-else-if="isDraft"
              drag
              :auto-upload="false"
              :show-file-list="false"
              accept="image/*"
              :on-change="(file: UploadFile) => onFileChange(no, side, file)"
            >
              <div class="flex flex-col items-center gap-1 py-4 text-slate-500">
                <el-icon class="text-2xl text-wind-400"><Camera /></el-icon>
                <span class="text-xs">拖拽或点击上传</span>
              </div>
            </el-upload>

            <!-- 已提交只读占位 -->
            <div
              v-else
              class="flex h-32 items-center justify-center rounded border border-dashed border-slate-700 text-xs text-slate-600"
            >
              暂无照片
            </div>
          </el-card>
        </div>
      </div>
    </el-card>

    <!-- 草稿：提交区 / 覆盖警告 -->
    <el-card v-if="detail && isDraft" class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <el-alert
        v-if="!detail.coverage_complete"
        type="warning"
        :closable="false"
        show-icon
        title="覆盖不完整，无法提交"
      >
        <div class="text-xs text-slate-300">
          以下面尚未采集照片：{{ missingSides.join('、') }}
        </div>
      </el-alert>
      <div class="mt-3 flex justify-end">
        <el-button
          type="primary"
          :disabled="!detail.coverage_complete"
          :loading="submitting"
          @click="handleSubmit"
        >
          提交巡检
        </el-button>
      </div>
    </el-card>

    <!-- 已提交只读提示 -->
    <el-card v-else-if="detail && isSubmitted" class="!bg-slate-900/60 !border-slate-800" shadow="never">
      <div class="flex items-center justify-between">
        <span class="text-sm text-slate-400">该巡检已提交，照片为只读状态。</span>
        <el-button @click="refresh">刷新</el-button>
      </div>
    </el-card>
  </div>
</template>
