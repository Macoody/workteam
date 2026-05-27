import { defineStore } from 'pinia'
import api from '@/api'
import router from '@/router'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null
  }),
  actions: {
    async login(username, password) {
      // 后端 OAuth2PasswordRequestForm 需要 form-data 格式
      const params = new URLSearchParams()
      params.append('username', username)
      params.append('password', password)
      const data = await axios.post('/api/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      this.token = data.access_token || data.token
      localStorage.setItem('token', this.token)
      return data
    },
    async register(data) {
      return api.post('/auth/register', data)
    },
    async getMe() {
      this.user = await api.get('/auth/me')
      return this.user
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      router.push('/login')
    }
  }
})