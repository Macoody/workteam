<template>
  <div class="projects-page">
    <div class="logo">徐东摆地摊</div>
    <el-container>
      <el-aside class="sidebar">
        <div class="sidebar-footer">
          <div class="user-info">
            <div class="user-name">{{ auth.user?.display_name }}</div>
          </div>
        </div>
        <router-link to="/dashboard" class="nav-item">总览</router-link>
        <router-link to="/projects" class="nav-item active">项目</router-link>
        <router-link to="/documents" class="nav-item">文档中心</router-link>
      </el-aside>
      <el-main class="main">
        <header class="header">
          <span>项目管理</span>
          <el-button type="primary" size="small" @click="showCreate = true">新建项目</el-button>
        </header>
        <div class="section">
          <div v-if="projects.length === 0" class="el-empty">暂无项目</div>
          <div v-else class="project-grid">
            <div v-for="p in projects" :key="p.id" class="project-card" @click="$router.push(`/kanban?project=${p.id}`)">
              <div class="project-color" :style="{ background: p.color || '#667eea' }"></div>
              <div class="project-info">
                <div class="project-name">{{ p.name }}</div>
                <div class="project-meta">创建于 {{ p.created_at?.slice(0, 10) }}</div>
              </div>
            </div>
          </div>
        </div>
      </el-main>
    </el-container>

    <el-dialog v-model="showCreate" title="新建项目" width="400px">
      <el-form :model="form" label-position="top" @submit.prevent="handleCreate">
        <el-form-item label="项目名称">
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="form.description" type="textarea" placeholder="简要描述项目" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" native-type="submit" style="width:100%" @click="handleCreate">创建</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import { ElMessage } from 'element-plus'
import api from '@/api'

const auth = useAuthStore()
const projectStore = useProjectStore()
const showCreate = ref(false)
const loading = ref(false)
const form = reactive({ name: '', description: '' })
const projects = ref([])

onMounted(async () => {
  await auth.getMe()
  projects.value = await projectStore.fetchProjects()
})

async function handleCreate() {
  if (!form.name) { ElMessage.warning('请输入项目名称'); return }
  loading.value = true
  try {
    await projectStore.createProject(form)
    ElMessage.success('项目创建成功')
    showCreate.value = false
    form.name = ''
    form.description = ''
  } catch (e) {
    ElMessage.error('创建失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.projects-page { display: flex; min-height: 100vh; }
.logo { position: fixed; top: 0; left: 0; width: 220px; height: 60px; background: #1a1a2e; color: white; display: flex; align-items: center; padding: 0 20px; font-size: 14px; font-weight: bold; z-index: 10; }
.sidebar { width: 220px; background: #1a1a2e; color: #fff; display: flex; flex-direction: column; padding-top: 60px; position: fixed; top: 0; left: 0; height: 100vh; }
.sidebar-footer { padding: 20px; border-bottom: 1px solid rgba(255,255,255,.1); }
.user-name { font-size: 14px; font-weight: 600; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 14px 20px; color: #a0aec0; text-decoration: none; transition: .2s; border-bottom: 1px solid rgba(255,255,255,.05); }
.nav-item:hover, .nav-item.active { background: rgba(255,255,255,.08); color: #fff; }
.main { margin-left: 220px; flex: 1; padding: 30px 40px; overflow-y: auto; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
.header span { font-size: 24px; font-weight: 700; color: #1a1a2e; }
.section { }
.project-grid { display: grid; grid-template-columns: repeat(auto-fill, 240px); gap: 20px; }
.project-card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.06); cursor: pointer; transition: transform 0.2s; }
.project-card:hover { transform: translateY(-2px); }
.project-color { height: 8px; }
.project-info { padding: 15px; }
.project-name { font-weight: 600; font-size: 15px; margin-bottom: 5px; color: #1a1a2e; }
.project-meta { font-size: 12px; color: #888; }
</style>