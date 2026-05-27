import { defineStore } from 'pinia'
import api from '@/api'

export const useTaskStore = defineStore('task', {
  state: () => ({
    tasks: []
  }),
  actions: {
    async fetchTasks(projectId) {
      const params = projectId ? `?project_id=${projectId}` : ''
      this.tasks = await api.get(`/tasks${params}`)
      return this.tasks
    },
    async createTask(data) {
      const t = await api.post('/tasks', data)
      this.tasks.push(t)
      return t
    },
    async updateTask(id, data) {
      const t = await api.put(`/tasks/${id}`, data)
      const idx = this.tasks.findIndex(x => x.id === id)
      if (idx >= 0) this.tasks[idx] = t
      return t
    },
    async deleteTask(id) {
      await api.delete(`/tasks/${id}`)
      this.tasks = this.tasks.filter(x => x.id !== id)
    }
  }
})