<template>
  <div class="tasks-page">
    <div class="logo">徐东摆地摊</div>
    <el-container>
      <el-aside class="sidebar">
        <div class="sidebar-footer">
          <div class="user-name">{{ auth.user?.display_name }}</div>
        </div>
        <router-link to="/dashboard" class="nav-item">总览</router-link>
        <router-link to="/projects" class="nav-item">项目</router-link>
        <router-link to="/documents" class="nav-item">文档中心</router-link>
      </el-aside>
      <el-main class="main">
        <header class="header">
          <span>任务列表</span>
          <div class="header-right">
            <el-select v-model="filterProject" placeholder="全部项目" size="small" clearable @change="loadTasks" style="width:140px">
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
            <el-button size="small" @click="loadTasks">刷新</el-button>
          </div>
        </header>
        <div class="section">
          <el-table :data="tasks" style="width:100%" v-loading="loading">
            <el-table-column prop="title" label="标题" />
            <el-table-column prop="priority" label="优先级" width="100">
              <template #default="{ row }">
                <el-tag :type="row.priority === 'high' ? 'danger' : row.priority === 'low' ? 'info' : 'warning'" size="small">
                  {{ row.priority }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="assignee_id" label="负责人" width="120" />
            <el-table-column prop="due_date" label="截止日期" width="150" />
            <el-table-column prop="project_id" label="项目" width="100" />
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-main>
    </el-container>

    <el-dialog v-model="editDialog" title="编辑任务" width="450px">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="标题"><el-input v-model="editForm.title" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="editForm.description" type="textarea" rows="3" /></el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="editForm.priority" style="width:100%">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="editForm.assignee_id" clearable style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="editForm.due_date" type="datetime" style="width:100%" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" style="width:100%" @click="saveTask">保存</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'
import { ElMessage } from 'element-plus'

const auth = useAuthStore()
const loading = ref(false)
const tasks = ref([])
const projects = ref([])
const filterProject = ref(null)
const users = ref([])
const editDialog = ref(false)
const currentTask = ref(null)
const editForm = reactive({ title: '', description: '', priority: 'medium', assignee_id: null, due_date: null })
const saving = ref(false)

onMounted(async () => {
  await auth.getMe()
  projects.value = await api.get('/projects')
  users.value = [] // TODO: fetch users
  loadTasks()
})

async function loadTasks() {
  loading.value = true
  try {
    const params = filterProject.value ? `?project_id=${filterProject.value}` : ''
    tasks.value = await api.get(`/tasks${params}`)
  } catch (e) {
    console.error(e)
  }
  loading.value = false
}

function openEdit(task) {
  currentTask.value = task
  editForm.title = task.title
  editForm.description = task.description || ''
  editForm.priority = task.priority || 'medium'
  editForm.assignee_id = task.assignee_id
  editForm.due_date = task.due_date
  editDialog.value = true
}

async function saveTask() {
  saving.value = true
  try {
    await api.put(`/tasks/${currentTask.value.id}`, editForm)
    ElMessage.success('保存成功')
    editDialog.value = false
    loadTasks()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.tasks-page { display: flex; height: 100vh; background: #f5f5f5; }
.logo { position: fixed; top: 0; left: 0; width: 200px; height: 60px; background: #545c64; color: white; display: flex; align-items: center; padding: 0 20px; font-size: 14px; font-weight: bold; z-index: 10; }
.sidebar { width: 200px; background: #fff; border-right: 1px solid #eee; padding-top: 60px; }
.sidebar-footer { padding: 10px; border-bottom: 1px solid #eee; }
.user-name { font-weight: bold; }
.nav-item { display: block; padding: 12px 20px; color: #333; text-decoration: none; border-bottom: 1px solid #f0f0f0; }
.nav-item.active { background: #ecf5ff; color: #409eff; }
.main { margin-left: 200px; }
.header { padding: 15px 20px; background: white; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.header-right { display: flex; gap: 10px; }
.section { padding: 20px; }
</style>