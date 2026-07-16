import { defineStore } from 'pinia'
import api from '@/api'
import router from '@/router'

let presenceTimer = null
let presenceListenersReady = false
let activeAuthStore = null

const sectionLabelMap = {
  Dashboard: '总览',
  Projects: '项目',
  Members: '成员管理',
  Kanban: '项目看板',
  Tasks: '任务',
  DigitalEmployees: '数字员工',
  Documents: '文档中心',
  DocEditor: '文档编辑',
  WorkLogs: '工作日志',
  Versions: '版本更新',
  Login: '登录'
}

function currentSectionLabel() {
  const route = router.currentRoute.value
  return route?.meta?.title || sectionLabelMap[route?.name] || route?.name || '未知板块'
}

function authHeader() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function sendOfflineBeacon() {
  const token = localStorage.getItem('token')
  if (!token) return
  fetch('/api/auth/presence/offline', {
    method: 'POST',
    headers: authHeader(),
    keepalive: true
  }).catch(() => {})
}

function handlePageHide() {
  sendOfflineBeacon()
}

function handleVisibilityChange() {
  if (document.visibilityState === 'hidden') {
    sendOfflineBeacon()
  } else if (document.visibilityState === 'visible') {
    activeAuthStore?.heartbeatPresence()
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null
  }),
  actions: {
    async login(username, password) {
      // 后端 OAuth2PasswordRequestForm 需要 form-data 格式
      const params = new URLSearchParams()
      params.append('username', (username || '').trim())
      params.append('password', password)
      const data = await api.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      this.token = data.access_token || data.token
      this.user = data.user || null
      localStorage.setItem('token', this.token)
      this.startPresence()
      return data
    },
    async register(data) {
      return api.post('/auth/register', data)
    },
    async getMe() {
      this.user = await api.get('/auth/me')
      this.startPresence()
      return this.user
    },
    async heartbeatPresence() {
      if (!this.token) return null
      try {
        this.user = await api.post('/auth/presence/heartbeat', {
          current_section: currentSectionLabel()
        })
        return this.user
      } catch (error) {
        console.error(error)
        return null
      }
    },
    startPresence() {
      if (!this.token) return
      activeAuthStore = this
      if (!presenceTimer) {
        this.heartbeatPresence()
        presenceTimer = window.setInterval(() => {
          this.heartbeatPresence()
        }, 30000)
      }
      if (!presenceListenersReady) {
        presenceListenersReady = true
        window.addEventListener('beforeunload', sendOfflineBeacon)
        window.addEventListener('pagehide', handlePageHide)
        document.addEventListener('visibilitychange', handleVisibilityChange)
      }
    },
    async stopPresence() {
      activeAuthStore = null
      if (presenceTimer) {
        window.clearInterval(presenceTimer)
        presenceTimer = null
      }
      if (this.token) {
        try {
          await api.post('/auth/presence/offline')
        } catch (error) {
          console.error(error)
        }
      }
    },
    async logout() {
      await this.stopPresence()
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      router.push('/login')
    }
  }
})
