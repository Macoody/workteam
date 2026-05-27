<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="brand">
        <img class="brand-logo" :src="logoXudong" alt="徐东 logo" />
        <div>
          <div class="brand-title">徐东摆地摊</div>
          <div class="brand-subtitle">轻量协作台</div>
        </div>
      </div>

      <nav class="app-nav">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="app-nav-item"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="app-sidebar-footer">
        <div class="app-user-card">
          <div class="app-user-name">{{ auth.user?.display_name || auth.user?.username || '用户' }}</div>
          <div class="app-user-role">{{ roleLabel }}</div>
        </div>
        <el-button plain size="small" class="logout-btn" @click="auth.logout()">退出登录</el-button>
      </div>
    </aside>

    <main class="app-main">
      <header class="page-header">
        <div>
          <h1 class="page-title">{{ title }}</h1>
          <p v-if="description" class="page-description">{{ description }}</p>
        </div>
        <div v-if="$slots.actions" class="page-actions">
          <slot name="actions" />
        </div>
      </header>

      <section class="page-body">
        <slot />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { Odometer, FolderOpened, Grid, List, Document, Calendar, User } from '@element-plus/icons-vue'
import logoXudong from '@/assets/logo-xudong.svg'

defineProps({
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  }
})

const navItems = [
  { to: '/dashboard', label: '总览', icon: Odometer },
  { to: '/projects', label: '项目', icon: FolderOpened },
  { to: '/members', label: '成员', icon: User },
  { to: '/kanban', label: '看板', icon: Grid },
  { to: '/tasks', label: '任务', icon: List },
  { to: '/documents', label: '文档', icon: Document },
  { to: '/logs', label: '日志', icon: Calendar }
]

const roleMap = {
  admin: '管理员',
  member: '成员',
  guest: '访客'
}

const auth = useAuthStore()
const roleLabel = computed(() => roleMap[auth.user?.role] || '团队成员')
</script>
