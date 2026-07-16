<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="brand">
        <img class="brand-logo" :src="logoXudong" alt="徐东 logo" />
        <div class="brand-copy">
          <div class="brand-title">徐东摆地摊</div>
          <div class="brand-subtitle">轻量协作台</div>
          <router-link to="/versions" class="brand-version">{{ currentVersion }}</router-link>
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
          <div class="app-user-name-row">
            <span class="presence-dot" :class="{ online: isUserOnline(auth.user) }"></span>
            <span class="app-user-name">{{ auth.user?.display_name || auth.user?.username || '用户' }}</span>
          </div>
          <div class="app-user-role">{{ roleLabel }}</div>
          <div class="app-user-presence">{{ userPresenceText(auth.user) }}</div>
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
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Odometer, FolderOpened, List, Document, Calendar, User, CollectionTag, Cellphone } from '@element-plus/icons-vue'
import logoXudong from '@/assets/logo-xudong.svg'
import { currentVersion } from '@/data/versionHistory'
import { isUserOnline, userPresenceText } from '@/utils/presence'

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
  { to: '/tasks', label: '任务', icon: List },
  { to: '/digital-employees', label: '数字员工', icon: Cellphone },
  { to: '/documents', label: '文档', icon: Document },
  { to: '/logs', label: '工作日志', icon: Calendar },
  { to: '/versions', label: '版本更新', icon: CollectionTag }
]

const roleMap = {
  admin: '管理员',
  member: '成员',
  guest: '访客'
}

const auth = useAuthStore()
const route = useRoute()
const roleLabel = computed(() => roleMap[auth.user?.role] || '团队成员')

onMounted(() => {
  auth.startPresence()
})

watch(
  () => route.fullPath,
  () => {
    auth.heartbeatPresence()
  }
)

</script>
