<template>
  <div class="dashboard">
    <div class="logo">徐东摆地摊</div>
    <el-container>
      <el-aside class="sidebar">
        <div class="sidebar-footer">
          <div class="user-info">
            <div class="user-name">{{ auth.user?.display_name || auth.user?.username }}</div>
            <div class="user-role">{{ auth.user?.role === 'admin' ? '管理员' : '成员' }}</div>
          </div>
        </div>
        <router-link to="/dashboard" class="nav-item active">
          <span>总览</span>
        </router-link>
        <router-link to="/projects" class="nav-item">
          <span>项目</span>
        </router-link>
        <router-link to="/documents" class="nav-item">
          <span>文档中心</span>
        </router-link>
      </el-aside>
      <el-main class="main">
        <header class="header">
          <span>仪表盘</span>
          <el-button size="small" @click="auth.logout()">退出</el-button>
        </header>
        <div class="section">
          <div class="stats">
            <div class="stat-card">
              <div class="stat-num">{{ stats.projects }}</div>
              <div class="stat-label">项目总数</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ stats.tasks }}</div>
              <div class="stat-label">任务总数</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ stats.my_tasks }}</div>
              <div class="stat-label">我的任务</div>
            </div>
            <div class="stat-card">
              <div class="stat-num">{{ stats.documents }}</div>
              <div class="stat-label">文档数量</div>
            </div>
          </div>
          <h3 class="task-list-title">任务列表</h3>
          <div v-if="recentTasks.length === 0" class="el-empty">暂无任务</div>
          <div v-else class="task-list">
            <div v-for="task in recentTasks" :key="task.id" class="task-item">
              <div class="task-title">{{ task.title }}</div>
              <div class="task-project">{{ task.project_id }}</div>
              <el-tag :type="task.priority === 'high' ? 'danger' : task.priority === 'low' ? 'info' : 'warning'" size="small">
                {{ task.priority }}
              </el-tag>
            </div>
          </div>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const auth = useAuthStore()
const stats = ref({ projects: 0, tasks: 0, my_tasks: 0, documents: 0 })
const recentTasks = ref([])

onMounted(async () => {
  await auth.getMe()
  try {
    const [projects, tasks, myTasks, docs] = await Promise.all([
      api.get('/projects'),
      api.get('/tasks'),
      api.get('/tasks?my_tasks=true'),
      api.get('/documents')
    ])
    stats.value = {
      projects: Array.isArray(projects) ? projects.length : 0,
      tasks: Array.isArray(tasks) ? tasks.length : 0,
      my_tasks: Array.isArray(myTasks) ? myTasks.length : 0,
      documents: Array.isArray(docs) ? docs.length : 0
    }
    recentTasks.value = (tasks || []).slice(0, 10)
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.dashboard { display: flex; min-height: 100vh; }
.logo { position: fixed; top: 0; left: 0; width: 220px; height: 60px; background: #1a1a2e; color: white; display: flex; align-items: center; padding: 0 20px; font-size: 14px; font-weight: bold; z-index: 10; }
.sidebar { width: 220px; background: #1a1a2e; color: #fff; display: flex; flex-direction: column; padding-top: 60px; position: fixed; top: 0; left: 0; height: 100vh; }
.sidebar-footer { padding: 20px; border-bottom: 1px solid rgba(255,255,255,.1); }
.user-info { }
.user-name { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.user-role { font-size: 12px; color: #a0aec0; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 14px 20px; color: #a0aec0; text-decoration: none; transition: .2s; border-bottom: 1px solid rgba(255,255,255,.05); }
.nav-item:hover, .nav-item.active { background: rgba(255,255,255,.08); color: #fff; }
.main { margin-left: 220px; flex: 1; padding: 30px 40px; overflow-y: auto; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
.header span { font-size: 24px; font-weight: 700; color: #1a1a2e; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 40px; }
.stat-card { background: #fff; border-radius: 12px; padding: 24px; text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,.06); }
.stat-num { font-size: 36px; font-weight: 700; color: #667eea; }
.stat-label { font-size: 14px; color: #888; margin-top: 6px; }
.task-list-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; }
.task-list { background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.06); }
.task-item { display: flex; align-items: center; gap: 12px; padding: 16px 20px; border-bottom: 1px solid #f0f0f0; cursor: pointer; transition: .2s; }
.task-item:hover { background: #f9fafb; }
.task-item:last-child { border-bottom: none; }
.task-title { flex: 1; font-size: 14px; color: #1a1a2e; }
.task-project { font-size: 12px; color: #888; }
</style>