<template>
  <el-container class="layout-container">
    <el-header class="header">
      <div class="header-left">
        <h2>工作团队</h2>
      </div>
      <div class="header-right">
        <span>{{ auth.user?.display_name || auth.user?.username || '用户' }}</span>
        <el-button @click="auth.logout()" size="small">退出</el-button>
      </div>
    </el-header>
    <el-container>
      <el-aside width="200px" class="sidebar">
        <el-menu :default-active="$route.path" router>
          <el-menu-item index="/dashboard">
            <el-icon><Odometer /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/projects">
            <el-icon><Folder /></el-icon>
            <span>项目管理</span>
          </el-menu-item>
          <el-menu-item index="/kanban">
            <el-icon><SGrid /></el-icon>
            <span>看板</span>
          </el-menu-item>
          <el-menu-item index="/tasks">
            <el-icon><List /></el-icon>
            <span>任务列表</span>
          </el-menu-item>
          <el-menu-item index="/documents">
            <el-icon><Document /></el-icon>
            <span>文档管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { Odometer, Folder, SGrid, List, Document } from '@element-plus/icons-vue'

const auth = useAuthStore()
onMounted(() => auth.getMe())
</script>

<style scoped>
.layout-container { height: 100vh; }
.header {
  display: flex; align-items: center; justify-content: space-between;
  background: #545c64; color: white; padding: 0 20px;
}
.header h2 { margin: 0; font-size: 18px; }
.header-right { display: flex; align-items: center; gap: 15px; }
.sidebar { background: #f5f5f5; }
.main-content { background: #fff; padding: 20px; }
</style>