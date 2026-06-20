import axios from 'axios'
import { ElMessage } from 'element-plus'

const STORAGE_KEY = 'wind-inspect-user-id'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const userId = localStorage.getItem(STORAGE_KEY)
  if (userId) {
    config.headers['X-User-Id'] = userId
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(typeof message === 'string' ? message : '请求失败')
    return Promise.reject(error)
  },
)

export default request
