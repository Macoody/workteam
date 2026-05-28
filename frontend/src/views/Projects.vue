<template>
  <AppShell title="项目管理" description="从项目进入看板推进任务，项目本身也支持直接维护。">
    <template #actions>
      <el-button type="primary" @click="openCreate">新建项目</el-button>
    </template>

    <div v-if="projects.length === 0" class="empty-card">还没有项目，先创建一个新的协作空间。</div>
    <div v-else class="project-grid">
      <div
        v-for="project in projects"
        :key="project.id"
        class="project-card"
        @click="goToKanban(project.id)"
      >
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px">
          <div class="pill">项目 #{{ project.id }}</div>
          <div style="display: flex; gap: 8px">
            <el-button size="small" @click.stop="openEdit(project)">编辑</el-button>
            <el-button
              v-if="canDeleteProject"
              size="small"
              type="danger"
              plain
              @click.stop="confirmDelete(project)"
            >
              删除
            </el-button>
          </div>
        </div>

        <div style="margin-top: 18px" class="item-title">{{ project.name }}</div>
        <div class="item-meta">{{ project.description || '暂无项目说明' }}</div>

        <div class="project-stats">
          <div
            v-for="item in projectStatusItems(project)"
            :key="item.label"
            class="project-stat-item"
            :style="{ background: item.tint, color: item.color, boxShadow: `inset 0 0 0 1px ${item.ring}` }"
          >
            <div class="project-stat-label">{{ item.label }}</div>
            <div class="project-stat-value">{{ item.value }}</div>
          </div>
        </div>

        <div style="margin-top: 18px; display: flex; justify-content: space-between; align-items: center">
          <span class="muted">创建于 {{ formatDate(project.created_at) }}</span>
          <el-tag effect="light">{{ project.task_count || 0 }} 个任务</el-tag>
        </div>
      </div>
    </div>

    <el-dialog v-model="showDialog" :title="editingProjectId ? '编辑项目' : '新建项目'" width="420px">
      <el-form :model="form" label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="项目名称">
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="简要描述项目目标或范围" />
        </el-form-item>
        <el-button type="primary" :loading="saving" native-type="submit" style="width: 100%" @click="handleSubmit">
          {{ editingProjectId ? '保存修改' : '创建项目' }}
        </el-button>
      </el-form>
    </el-dialog>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'

const router = useRouter()
const auth = useAuthStore()
const projectStore = useProjectStore()
const showDialog = ref(false)
const saving = ref(false)
const editingProjectId = ref(null)
const form = reactive({ name: '', description: '' })
const projects = ref([])
const projectStatsById = ref({})
const statusPalette = [
  { label: '待处理', key: 'pending_count', color: '#64748b', tint: 'rgba(148, 163, 184, 0.16)', ring: 'rgba(148, 163, 184, 0.28)' },
  { label: '进行中', key: 'in_progress_count', color: '#2563eb', tint: 'rgba(59, 130, 246, 0.14)', ring: 'rgba(59, 130, 246, 0.24)' },
  { label: '待验收', key: 'review_count', color: '#d97706', tint: 'rgba(245, 158, 11, 0.16)', ring: 'rgba(245, 158, 11, 0.26)' },
  { label: '已完成', key: 'done_count', color: '#059669', tint: 'rgba(16, 185, 129, 0.14)', ring: 'rgba(16, 185, 129, 0.24)' }
]

const canDeleteProject = computed(() => auth.user?.role === 'admin')

onMounted(async () => {
  await auth.getMe()
  await refreshProjects()
})

async function refreshProjects() {
  const projectList = await projectStore.fetchProjects()
  const statsEntries = await Promise.all(
    (projectList || []).map(async project => {
      const columns = await api.get(`/kanban/project/${project.id}`)
      const stats = {
        pending_count: 0,
        in_progress_count: 0,
        review_count: 0,
        done_count: 0,
        task_count: 0
      }
      ;(columns || []).forEach(column => {
        const count = column.tasks?.length || 0
        stats.task_count += count
        if (column.name === '待处理') stats.pending_count = count
        if (column.name === '进行中') stats.in_progress_count = count
        if (column.name === '待验收') stats.review_count = count
        if (column.name === '已完成') stats.done_count = count
      })
      return [project.id, stats]
    })
  )
  projectStatsById.value = Object.fromEntries(statsEntries)
  projects.value = projectList
}

function openCreate() {
  editingProjectId.value = null
  form.name = ''
  form.description = ''
  showDialog.value = true
}

function openEdit(project) {
  editingProjectId.value = project.id
  form.name = project.name
  form.description = project.description || ''
  showDialog.value = true
}

async function handleSubmit() {
  if (!form.name) {
    ElMessage.warning('请输入项目名称')
    return
  }

  saving.value = true
  try {
    if (editingProjectId.value) {
      await projectStore.updateProject(editingProjectId.value, form)
      ElMessage.success('项目已更新')
    } else {
      await projectStore.createProject(form)
      ElMessage.success('项目创建成功')
    }
    showDialog.value = false
    await refreshProjects()
  } catch (error) {
    const detail = error?.response?.data?.detail
    ElMessage.error(detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function confirmDelete(project) {
  try {
    await ElMessageBox.confirm(`确定删除项目“${project.name}”吗？`, '删除项目', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await projectStore.deleteProject(project.id)
    ElMessage.success('项目已删除')
    await refreshProjects()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    const detail = error?.response?.data?.detail
    ElMessage.error(detail || '删除失败')
  }
}

function goToKanban(projectId) {
  router.push(`/kanban?project=${projectId}`)
}

function projectStatusItems(project) {
  const stats = projectStatsById.value[project.id] || {}
  return statusPalette.map(item => ({
    ...item,
    value: stats[item.key] ?? project?.[item.key] ?? 0
  }))
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD') : '--'
}
</script>

<style scoped>
.project-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 18px;
}

.project-stat-item {
  border-radius: 16px;
  padding: 12px 10px;
}

.project-stat-label {
  font-size: 12px;
  font-weight: 600;
  opacity: 0.9;
}

.project-stat-value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 800;
  line-height: 1;
}
</style>
