<template>
  <AppShell title="任务列表" description="集中查看任务条目，方便后面继续打磨任务筛选、流转和规则。">
    <template #actions>
      <el-select v-model="filterProject" placeholder="全部项目" clearable style="width: 220px" @change="loadTasks">
        <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
      </el-select>
      <el-button @click="loadTasks">刷新</el-button>
    </template>

    <div class="panel table-panel">
      <el-table :data="tasks" style="width: 100%" v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column label="负责人" width="160">
          <template #default="{ row }">
            <span v-if="resolveUser(row.assignee_id)" class="user-chip" :style="{ background: resolveUser(row.assignee_id).color || '#93c5fd' }">
              {{ resolveUser(row.assignee_id).display_name || resolveUser(row.assignee_id).username }}
            </span>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column label="交付时间" width="150">
          <template #default="{ row }">
            {{ formatDate(latestDeliveryDate(row)) }}
          </template>
        </el-table-column>
        <el-table-column label="项目" min-width="160">
          <template #default="{ row }">
            {{ resolveProjectName(row.project_id) }}
          </template>
        </el-table-column>
        <el-table-column label="节点产出" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.node_output || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="editDialog" title="编辑任务" width="560px">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="所属项目">
          <el-select v-model="editForm.project_id" style="width: 100%" @change="handleProjectChange">
            <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="看板列">
          <el-select v-model="editForm.column_id" style="width: 100%">
            <el-option v-for="column in availableColumns" :key="column.id" :label="column.name" :value="column.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="当前节点描述">
          <el-input v-model="editForm.description" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="节点产出">
          <el-input v-model="editForm.node_output" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="关联文档">
          <el-select v-model="editForm.linked_document_id" clearable filterable style="width: 100%">
            <el-option v-for="doc in availableDocuments" :key="doc.id" :label="doc.title" :value="doc.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="editForm.assignee_id" clearable style="width: 100%">
            <el-option v-for="user in users" :key="user.id" :label="user.display_name || user.username" :value="user.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="交付时间">
          <el-date-picker v-model="editForm.due_date" type="datetime" style="width: 100%" :disabled="Boolean(currentTask?.due_date)" />
        </el-form-item>
        <div v-if="deliveryTimeline.length" class="delivery-stack">
          <div class="delivery-item" v-for="(item, index) in deliveryTimeline" :key="`${item}-${index}`">
            <span>{{ index === 0 ? '原始交付时间' : `延期 ${index}` }}</span>
            <span>{{ formatDate(item) }}</span>
          </div>
        </div>
        <div v-if="showExtensionPicker" class="extension-picker-wrap">
          <div class="extension-title">延期时间</div>
          <div class="extension-row">
            <el-date-picker v-model="extensionDate" type="datetime" style="width: 100%" :disabled="deliveryTimeline.length >= 5" />
            <el-button type="primary" :disabled="deliveryTimeline.length >= 5" @click="extendTask">确认延期</el-button>
          </div>
        </div>
        <div class="action-row">
          <el-button type="primary" :loading="saving" @click="saveTask">保存任务</el-button>
          <el-button :disabled="deliveryTimeline.length >= 5" @click="showExtensionPicker = true">延期</el-button>
          <el-button type="success" :loading="completing" @click="completeTask">完成任务</el-button>
        </div>
      </el-form>
    </el-dialog>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'

const auth = useAuthStore()
const loading = ref(false)
const tasks = ref([])
const projects = ref([])
const filterProject = ref(null)
const users = ref([])
const columnsByProject = ref({})
const documentsByProject = ref({})
const editDialog = ref(false)
const currentTask = ref(null)
const editForm = reactive({
  project_id: null,
  column_id: null,
  title: '',
  description: '',
  node_output: '',
  linked_document_id: null,
  assignee_id: null,
  due_date: null
})
const saving = ref(false)
const completing = ref(false)
const extensionDate = ref(null)
const showExtensionPicker = ref(false)

const availableColumns = computed(() => columnsByProject.value[editForm.project_id] || [])
const availableDocuments = computed(() => documentsByProject.value[editForm.project_id] || [])
const deliveryTimeline = computed(() => currentTask.value?.delivery_dates || [])

onMounted(async () => {
  await auth.getMe()
  const [projectList, userList] = await Promise.all([
    api.get('/projects'),
    api.get('/auth/users')
  ])
  projects.value = projectList || []
  users.value = userList || []
  await loadTasks()
})

async function loadTasks() {
  loading.value = true
  try {
    const params = filterProject.value ? `?project_id=${filterProject.value}` : ''
    tasks.value = await api.get(`/tasks${params}`)
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function openEdit(task) {
  currentTask.value = { ...task }
  editForm.project_id = task.project_id
  editForm.column_id = task.column_id
  editForm.title = task.title
  editForm.description = task.description || ''
  editForm.node_output = task.node_output || ''
  editForm.linked_document_id = task.linked_document_id || null
  editForm.assignee_id = task.assignee_id
  editForm.due_date = task.due_date
  extensionDate.value = null
  showExtensionPicker.value = false
  await Promise.all([
    ensureProjectColumns(task.project_id),
    ensureProjectDocuments(task.project_id)
  ])
  editDialog.value = true
}

async function ensureProjectColumns(projectId) {
  if (!projectId || columnsByProject.value[projectId]) return
  const columns = await api.get(`/kanban/project/${projectId}`)
  columnsByProject.value = {
    ...columnsByProject.value,
    [projectId]: (columns || []).map(column => ({
      id: column.id,
      name: column.name
    }))
  }
}

async function ensureProjectDocuments(projectId) {
  if (!projectId || documentsByProject.value[projectId]) return
  const documents = await api.get('/documents')
  documentsByProject.value = {
    ...documentsByProject.value,
    [projectId]: documents || []
  }
}

async function handleProjectChange(projectId) {
  await Promise.all([
    ensureProjectColumns(projectId),
    ensureProjectDocuments(projectId)
  ])
  const columns = columnsByProject.value[projectId] || []
  if (!columns.some(column => column.id === editForm.column_id)) {
    editForm.column_id = columns[0]?.id || null
  }
  if (!(availableDocuments.value || []).some(doc => doc.id === editForm.linked_document_id)) {
    editForm.linked_document_id = null
  }
}

async function saveTask() {
  if (!editForm.project_id || !editForm.column_id) {
    ElMessage.warning('请选择所属项目和看板列')
    return
  }

  saving.value = true
  try {
    const updated = await api.put(`/tasks/${currentTask.value.id}`, editForm)
    currentTask.value = updated
    ElMessage.success('保存成功')
    editDialog.value = false
    await loadTasks()
  } catch (error) {
    const detail = error?.response?.data?.detail
    ElMessage.error(detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function extendTask() {
  if (!extensionDate.value) {
    ElMessage.warning('请选择新的交付时间')
    return
  }
  try {
    const updated = await api.post(`/tasks/${currentTask.value.id}/extend-delivery`, {
      due_date: dayjs(extensionDate.value).toISOString()
    })
    currentTask.value = updated
    extensionDate.value = null
    editForm.due_date = updated.due_date
    showExtensionPicker.value = false
    ElMessage.success('已记录延期时间')
    await loadTasks()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '延期失败')
  }
}

async function completeTask() {
  completing.value = true
  try {
    await api.post(`/tasks/${currentTask.value.id}/complete`)
    ElMessage.success(auth.user?.role === 'admin' ? '任务已归档到已完成' : '任务已移入待验收')
    editDialog.value = false
    await loadTasks()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '操作失败')
  } finally {
    completing.value = false
  }
}

function resolveUser(userId) {
  if (!userId) return null
  return users.value.find(item => item.id === userId) || null
}

function resolveProjectName(projectId) {
  const project = projects.value.find(item => item.id === projectId)
  return project?.name || `项目 #${projectId}`
}

function latestDeliveryDate(task) {
  const dates = task?.delivery_dates || []
  return dates[dates.length - 1] || task?.due_date || null
}

function formatDate(value) {
  return value ? dayjs(value).format('MM-DD HH:mm') : '--'
}
</script>

<style scoped>
.user-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  color: #0f172a;
  font-size: 12px;
  font-weight: 600;
}

.delivery-stack {
  margin-bottom: 14px;
}

.delivery-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #f8fafc;
}

.delivery-item + .delivery-item {
  margin-top: 8px;
}

.extension-row,
.action-row {
  display: flex;
  gap: 12px;
}

.extension-picker-wrap {
  margin-bottom: 14px;
}

.extension-title {
  margin-bottom: 10px;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.action-row {
  margin-top: 16px;
}
</style>
