import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import type { User, UserRole } from '@/types'

const STORAGE_KEY = 'wind-inspect-user-id'

export const useUserStore = defineStore('user', () => {
  const currentUser = ref<User | null>(null)
  const users = ref<User[]>([])

  const role = computed<UserRole | null>(() => currentUser.value?.role ?? null)

  const isInspector = computed(() => role.value === 'inspector')
  const isAnnotator = computed(() => role.value === 'annotator')
  const isSupervisor = computed(() => role.value === 'supervisor')

  async function loadUsers() {
    users.value = await api.getUsers()
  }

  async function loadCurrentUser() {
    currentUser.value = await api.getCurrentUser()
  }

  async function switchUser(userId: string) {
    currentUser.value = await api.switchUser(userId)
    localStorage.setItem(STORAGE_KEY, userId)
  }

  async function init() {
    await loadUsers()
    const savedId = localStorage.getItem(STORAGE_KEY)
    if (savedId) {
      try {
        await switchUser(savedId)
        return
      } catch {
        // fallthrough
      }
    }
    await loadCurrentUser()
  }

  return {
    currentUser,
    users,
    role,
    isInspector,
    isAnnotator,
    isSupervisor,
    loadUsers,
    loadCurrentUser,
    switchUser,
    init,
  }
})
