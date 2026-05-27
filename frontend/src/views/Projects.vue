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

        <div style="margin-top: 18px; display: flex; justify-content: space-between; align-items: center">
          <span class="muted">创建于 {{ formatDate(project.created_at) }}</span>
          <el-tag effect="light">{{ project.task_count || 0 }} 列</el-tag>
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

const router = useRouter()
const auth = useAuthStore()
const projectStore = useProjectStore()
const showDialog = ref(false)
const saving = ref(false)
const editingProjectId = ref(null)
const form = reactive({ name: '', description: '' })
const projects = ref([])

const canDeleteProject = computed(() => auth.user?.username === 'mac')

onMounted(async () => {
  await auth.getMe()
  await refreshProjects()
})

async function refreshProjects() {
  projects.value = await projectStore.fetchProjects()
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

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD') : '--'
}
</script>
