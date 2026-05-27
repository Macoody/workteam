<template>
  <div class="dashboard">
    <div class="logo">徐东摆地摊</div>
    <el-container>
      <el-aside class="sidebar">
        <div class="sidebar-footer">
          <div class="user-info">
            <div class="user-name">{{ auth.user?.display_name || auth.user?.username }}</div>
            <div class="user-role">{{ auth.user?.role }}</div>
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
.dashboard { display: flex; height: 100vh; background: #f5f5f5; }
.logo { position: fixed; top: 0; left: 0; width: 200px; height: 60px; background: #545c64; color: white; display: flex; align-items: center; padding: 0 20px; font-size: 14px; font-weight: bold; z-index: 10; }
.sidebar { width: 200px; background: #fff; border-right: 1px solid #eee; padding-top: 60px; }
.sidebar-footer { padding: 10px; border-bottom: 1px solid #eee; }
.user-name { font-weight: bold; font-size: 14px; }
.user-role { font-size: 12px; color: #999; }
.nav-item { display: block; padding: 12px 20px; color: #333; text-decoration: none; border-bottom: 1px solid #f0f0f0; }
.nav-item.active { background: #ecf5ff; color: #409eff; }
.main { margin-left: 200px; }
.header { padding: 15px 20px; background: white; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.section { padding: 20px; }
.stats { display: flex; gap: 20px; margin-bottom: 30px; }
.stat-card { flex: 1; background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.stat-num { font-size: 28px; font-weight: bold; color: #409eff; }
.stat-label { color: #666; margin-top: 5px; }
.task-list-title { margin-bottom: 15px; font-size: 16px; }
.task-list { background: white; border-radius: 8px; overflow: hidden; }
.task-item { padding: 12px 15px; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; gap: 10px; }
.task-title { flex: 1; font-weight: 500; }
.task-project { color: #999; font-size: 12px; }
</style>