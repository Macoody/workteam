<template>
  <el-container class="layout-container">
    <el-header class="header">
      <div class="header-left">
        <h2>徐东摆地摊</h2>
      </div>
      <div class="header-right">
        <span>{{ auth.user?.display_name || auth.user?.username || '用户' }}</span>
        <el-button @click="auth.logout()" size="small">退出</el-button>
      </div>
    </el-header>
    <el-container>
      <el-aside class="sidebar">
        <div class="sidebar-user">
          <div class="user-name">{{ auth.user?.display_name || auth.user?.username }}</div>
          <div class="user-role">{{ auth.user?.role === 'admin' ? '管理员' : '成员' }}</div>
        </div>
        <el-menu :default-active="$route.path" router class="sidebar-nav">
          <el-menu-item index="/dashboard">
            <el-icon><Odometer /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/projects">
            <el-icon><Folder /></el-icon>
            <span>项目管理</span>
          </el-menu-item>
          <el-menu-item index="/kanban">
            <el-icon><DataBoard /></el-icon>
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
import { Odometer, Folder, DataBoard, List, Document } from '@element-plus/icons-vue'

const auth = useAuthStore()
onMounted(() => auth.getMe())
</script>

<style scoped>
.layout-container { height: 100vh; }
.header {
  display: flex; align-items: center; justify-content: space-between;
  background: #1a1a2e; color: white; padding: 0 24px;
}
.header h2 { margin: 0; font-size: 18px; font-weight: 700; }
.header-right { display: flex; align-items: center; gap: 15px; }
.sidebar {
  width: 220px;
  background: #1a1a2e;
  display: flex; flex-direction: column;
}
.sidebar-user {
  padding: 24px 20px 20px;
  border-bottom: 1px solid rgba(255,255,255,.1);
}
.user-name { font-size: 14px; font-weight: 600; color: #fff; margin-bottom: 4px; }
.user-role { font-size: 12px; color: #a0aec0; }
.sidebar-nav {
  background: transparent;
  border: none;
  flex: 1;
}
:deep(.el-menu) { background: transparent; border: none; }
:deep(.el-menu-item) {
  color: #a0aec0;
  padding-left: 20px !important;
  margin: 4px 8px;
  border-radius: 8px;
  height: 44px;
}
:deep(.el-menu-item:hover) { background: rgba(255,255,255,.08); color: #fff; }
:deep(.el-menu-item.is-active) { background: rgba(255,255,255,.12); color: #fff; }
:deep(.el-menu-item .el-icon) { margin-right: 10px; color: inherit; }
.main-content { background: #f5f7fa; padding: 30px 40px; overflow-y: auto; }
</style>