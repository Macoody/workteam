import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { requiresAuth: true } },
  { path: '/projects', name: 'Projects', component: () => import('@/views/Projects.vue'), meta: { requiresAuth: true } },
  { path: '/members', name: 'Members', component: () => import('@/views/Members.vue'), meta: { requiresAuth: true } },
  { path: '/kanban/:projectId?', name: 'Kanban', component: () => import('@/views/Kanban.vue'), meta: { requiresAuth: true } },
  { path: '/tasks', name: 'Tasks', component: () => import('@/views/Tasks.vue'), meta: { requiresAuth: true } },
  { path: '/documents', name: 'Documents', component: () => import('@/views/Documents.vue'), meta: { requiresAuth: true } },
  { path: '/documents/:id', name: 'DocEditor', component: () => import('@/views/DocEditor.vue'), meta: { requiresAuth: true } },
  { path: '/logs', name: 'WorkLogs', component: () => import('@/views/WorkLogs.vue'), meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.token) {
    next('/login')
  } else if (to.path === '/login' && auth.token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
