<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import {
  Odometer,
  Cpu,
  Guide,
  Camera,
  Search as SearchIcon,
  Tools,
  Lightning,
  Files,
} from '@element-plus/icons-vue'
import type { Component } from 'vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const collapse = ref(false)

const navItems = computed(() => [
  { index: '/', label: '工作台', icon: Odometer as Component },
  { index: '/turbines', label: '机组管理', icon: Cpu as Component },
  { index: '/routes', label: '航线计划', icon: Guide as Component },
  { index: '/inspections', label: '巡检管理', icon: Camera as Component },
  { index: '/defects', label: '缺陷复核', icon: SearchIcon as Component },
  { index: '/repairs', label: '维修单管理', icon: Tools as Component },
  { index: '/grid', label: '并网确认', icon: Lightning as Component },
  { index: '/trace', label: '追溯查询', icon: Files as Component },
])

const activeMenu = computed(() => {
  if (route.path.startsWith('/inspections')) return '/inspections'
  return route.path
})

const roleLabel = computed(() => {
  const r = userStore.role
  if (r === 'inspector') return '巡检工程师'
  if (r === 'annotator') return 'AI 标注员'
  if (r === 'supervisor') return '运维主管'
  return '未登录'
})

const roleTag = computed(() => {
  const r = userStore.role
  if (r === 'inspector') return 'primary'
  if (r === 'annotator') return 'warning'
  if (r === 'supervisor') return 'danger'
  return 'info'
})

function handleSelect(index: string) {
  router.push(index)
}

async function handleSwitchUser(userId: string) {
  await userStore.switchUser(userId)
}

onMounted(async () => {
  await userStore.init()
})
</script>

<template>
  <div class="flex h-full w-full bg-slate-950 grid-bg">
    <!-- 侧栏 -->
    <aside
      class="flex flex-col border-r border-slate-800/80 bg-slate-900/60 backdrop-blur transition-all duration-300"
      :class="collapse ? 'w-16' : 'w-56'"
    >
      <div class="flex items-center gap-2 px-4 py-4 border-b border-slate-800">
        <div class="h-8 w-8 shrink-0 rounded-lg bg-wind-500/20 flex items-center justify-center">
          <Lightning class="h-5 w-5 text-wind-400" />
        </div>
        <div v-show="!collapse" class="overflow-hidden">
          <div class="font-display text-sm font-600 text-wind-300 leading-tight">WIND INSPECT</div>
          <div class="text-[10px] text-slate-500 leading-tight">叶片巡检闭环</div>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="collapse"
        class="flex-1 !border-none !bg-transparent"
        text-color="#94a3b8"
        active-text-color="#22d3ee"
        @select="handleSelect"
      >
        <el-menu-item v-for="item in navItems" :key="item.index" :index="item.index">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.label }}</template>
        </el-menu-item>
      </el-menu>

      <div class="p-3 border-t border-slate-800">
        <el-button
          text
          size="small"
          class="!w-full !text-slate-500"
          @click="collapse = !collapse"
        >
          <el-icon class="mr-1">
            <Fold v-if="!collapse" />
            <Expand v-else />
          </el-icon>
        </el-button>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <!-- 顶栏 -->
      <header class="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-900/40">
        <div class="flex items-center gap-3">
          <span class="font-display text-lg font-600 text-slate-200">
            {{ route.meta?.title || '工作台' }}
          </span>
          <span class="text-slate-600">|</span>
          <span class="text-xs text-slate-500 font-mono">WIND FARM BLADE INSPECTION</span>
        </div>
        <div class="flex items-center gap-3">
          <el-tag :type="roleTag" effect="dark" size="small" round>
            {{ roleLabel }}
          </el-tag>
          <el-select
            :model-value="userStore.currentUser?.id"
            placeholder="切换角色"
            size="small"
            class="w-44"
            @change="handleSwitchUser"
          >
            <el-option
              v-for="u in userStore.users"
              :key="u.id"
              :label="u.display_name"
              :value="u.id"
            />
          </el-select>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="flex-1 overflow-auto p-6">
        <router-view v-slot="{ Component: comp }">
          <transition name="fade" mode="out-in">
            <component :is="comp" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
