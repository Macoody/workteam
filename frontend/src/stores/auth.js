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
      const data = await api.post('/auth/login', { username, password })
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