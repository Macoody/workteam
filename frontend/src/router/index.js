import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue') },
      { path: 'projects', name: 'Projects', component: () => import('@/views/Projects.vue') },
      { path: 'projects/:id', name: 'ProjectDetail', component: () => import('@/views/ProjectDetail.vue') },
      { path: 'kanban/:projectId?', name: 'Kanban', component: () => import('@/views/Kanban.vue') },
      { path: 'tasks', name: 'Tasks', component: () => import('@/views/Tasks.vue') },
      { path: 'documents', name: 'Documents', component: () => import('@/views/Documents.vue') },
      { path: 'documents/:id', name: 'DocEditor', component: () => import('@/views/DocEditor.vue') },
    ]
  }
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