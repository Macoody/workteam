import { defineStore } from 'pinia'
import api from '@/api'

export const useProjectStore = defineStore('project', {
  state: () => ({
    projects: [],
    currentProject: null
  }),
  actions: {
    async fetchProjects() {
      this.projects = await api.get('/projects')
      return this.projects
    },
    async createProject(data) {
      const p = await api.post('/projects', data)
      this.projects.push(p)
      return p
    },
    async updateProject(id, data) {
      const p = await api.put(`/projects/${id}`, data)
      const idx = this.projects.findIndex(x => x.id === id)
      if (idx >= 0) this.projects[idx] = p
      return p
    },
    async deleteProject(id) {
      await api.delete(`/projects/${id}`)
      this.projects = this.projects.filter(x => x.id !== id)
    },
    async getProject(id) {
      this.currentProject = await api.get(`/projects/${id}`)
      return this.currentProject
    }
  }
})