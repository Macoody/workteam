<template>
  <div class="projects-page">
    <div class="header">
      <span>项目管理</span>
      <el-button type="primary" size="small" @click="showCreate = true">新建项目</el-button>
    </div>
    <div class="section">
      <div v-if="projects.length === 0" class="el-empty">暂无项目</div>
      <div v-else class="project-grid">
        <div v-for="p in projects" :key="p.id" class="project-card" @click="$router.push(`/kanban?project=${p.id}`)">
          <div class="project-color" :style="{ background: p.color || '#409eff' }"></div>
          <div class="project-info">
            <div class="project-name">{{ p.name }}</div>
            <div class="project-meta">创建于 {{ p.created_at?.slice(0, 10) }}</div>
          </div>
          <div class="project-actions" @click.stop>
            <el-dropdown trigger="click">
              <el-button size="small" text>···</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openEdit(p)">修改名称</el-dropdown-item>
                  <el-dropdown-item v-if="auth.user?.role === 'admin'" @click="handleDelete(p.id)" style="color:#f56c6c">删除项目</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </div>

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

    <el-dialog v-model="showEdit" title="修改项目名称" width="400px">
      <el-form :model="editForm" label-position="top" @submit.prevent="handleEdit">
        <el-form-item label="项目名称">
          <el-input v-model="editForm.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" native-type="submit" style="width:100%" @click="handleEdit">保存</el-button>
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
const showEdit = ref(false)
const loading = ref(false)
const form = reactive({ name: '', description: '' })
const editForm = reactive({ id: null, name: '' })
const projects = ref([])

onMounted(async () => {
  await auth.getMe()
  projects.value = await projectStore.fetchProjects()
})

function openEdit(p) {
  editForm.id = p.id
  editForm.name = p.name
  showEdit.value = true
}

async function handleEdit() {
  if (!editForm.name) { ElMessage.warning('请输入项目名称'); return }
  loading.value = true
  try {
    await api.put(`/projects/${editForm.id}`, { name: editForm.name })
    ElMessage.success('修改成功')
    showEdit.value = false
    projects.value = await projectStore.fetchProjects()
  } catch (e) {
    ElMessage.error('修改失败')
  } finally {
    loading.value = false
  }
}

async function handleDelete(id) {
  try {
    await api.delete(`/projects/${id}`)
    ElMessage.success('删除成功')
    projects.value = await projectStore.fetchProjects()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

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
.projects-page { padding: 0; }
.header { padding: 15px 20px; background: white; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.section { padding: 20px; }
.project-grid { display: grid; grid-template-columns: repeat(auto-fill, 240px); gap: 20px; }
.project-card { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.2s; position: relative; }
.project-card:hover { transform: translateY(-2px); }
.project-color { height: 8px; }
.project-info { padding: 15px; }
.project-name { font-weight: bold; font-size: 16px; margin-bottom: 5px; }
.project-meta { font-size: 12px; color: #999; }
.project-actions { position: absolute; top: 8px; right: 8px; opacity: 0; transition: opacity 0.2s; }
.project-card:hover .project-actions { opacity: 1; }
</style>