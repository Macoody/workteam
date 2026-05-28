<template>
  <AppShell title="项目看板">
    <template #actions>
      <div class="kanban-actions">
        <el-select v-model="selectedProject" placeholder="选择项目" style="width: 220px" @change="handleProjectSwitch">
          <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
        </el-select>
        <el-button @click="loadKanban">刷新</el-button>
        <el-button type="success" class="create-task-button" @click="showAddTask">添加任务</el-button>
      </div>
    </template>

    <div v-if="!selectedProject" class="empty-card">先选择一个项目，再查看对应看板。</div>
    <div v-else-if="loading" class="empty-card">看板加载中...</div>
    <div v-else>
      <section class="project-hero">
        <div class="project-hero-label">当前项目</div>
        <h2 class="project-hero-title">{{ currentProject?.name || '未命名项目' }}</h2>
        <div v-if="currentProject?.description" class="project-hero-meta">{{ currentProject.description }}</div>
      </section>

      <div class="kanban-board">
        <div v-for="column in columns" :key="column.id" class="kanban-column">
          <div class="kanban-column-header">
            <div>
              <div class="item-title">{{ column.name }}</div>
              <div class="item-meta">当前 {{ column.tasks?.length || 0 }} 条任务</div>
            </div>
            <el-tag effect="light">{{ column.tasks?.length || 0 }}</el-tag>
          </div>

          <div class="kanban-task-list">
            <div v-for="task in column.tasks || []" :key="task.id" class="task-card" @click="openTask(task)">
              <div class="task-card-title">{{ task.title }}</div>
              <div class="task-card-meta">
                <span
                  v-if="task.assignee_id && resolveUser(task.assignee_id)"
                  class="user-pill"
                  :style="{ background: resolveUser(task.assignee_id).color || '#93c5fd' }"
                >
                  {{ resolveUser(task.assignee_id).display_name || resolveUser(task.assignee_id).username }}
                </span>
                <span v-if="latestDeliveryDate(task)" class="pill">{{ formatDate(latestDeliveryDate(task)) }}</span>
              </div>
              <div v-if="task.description" class="task-card-note">{{ task.description }}</div>
              <div v-if="task.linked_document_id" class="task-card-link">已关联文档</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-drawer v-model="taskDrawer" :title="currentTask?.title || '任务详情'" size="560px">
      <el-form v-if="currentTask" label-position="top">
        <el-form-item label="当前节点描述">
          <el-input v-model="editForm.description" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="节点产出">
          <el-input v-model="editForm.node_output" type="textarea" :rows="4" placeholder="补充当前节点的产出内容" />
        </el-form-item>
        <el-form-item label="关联文档">
          <el-select v-model="editForm.linked_document_id" clearable filterable style="width: 100%">
            <el-option v-for="doc in projectDocuments" :key="doc.id" :label="doc.title" :value="doc.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="editForm.assignee_id" clearable style="width: 100%">
            <el-option v-for="user in users" :key="user.id" :label="user.display_name || user.username" :value="user.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="交付时间">
          <el-date-picker
            v-model="editForm.due_date"
            type="datetime"
            style="width: 100%"
            :disabled="Boolean(currentTask?.due_date)"
          />
        </el-form-item>
        <div v-if="deliveryTimeline.length" class="delivery-stack">
          <div class="section-label">交付时间记录</div>
          <div class="delivery-item" v-for="(item, index) in deliveryTimeline" :key="`${item}-${index}`">
            <span class="delivery-index">{{ index === 0 ? '原始' : `延期 ${index}` }}</span>
            <span>{{ formatDate(item) }}</span>
          </div>
        </div>
        <div v-if="showExtensionPicker" class="extension-picker-wrap">
          <div class="section-label">延期时间</div>
          <div class="extension-panel">
            <el-date-picker
              v-model="extensionDate"
              type="datetime"
              style="width: 100%"
              :disabled="deliveryTimeline.length >= 5"
              placeholder="选择新的延期时间"
            />
            <el-button type="primary" :disabled="deliveryTimeline.length >= 5" @click="extendTask">确认延期</el-button>
          </div>
        </div>
        <div class="drawer-actions">
          <el-button type="primary" :loading="saving" @click="saveTask">保存</el-button>
          <el-button :disabled="deliveryTimeline.length >= 5" @click="showExtensionPicker = true">延期</el-button>
          <el-button v-if="canClaimTask" type="warning" :loading="claiming" @click="claimTask">领取任务</el-button>
          <el-button type="success" :loading="completing" @click="completeTask">完成任务</el-button>
          <el-button type="danger" @click="deleteTask">删除</el-button>
        </div>
      </el-form>

      <el-divider />
      <h4>评论</h4>
      <div v-if="comments.length === 0" class="muted" style="margin-bottom: 12px">还没有评论</div>
      <div v-else class="simple-list">
        <div v-for="comment in comments" :key="comment.id" class="simple-list-item">
          <div class="item-main">
            <div class="item-title">{{ comment.user?.display_name || comment.user?.username || '成员' }}</div>
            <div class="item-meta">{{ comment.content }}</div>
          </div>
          <span class="muted">{{ formatDate(comment.created_at) }}</span>
        </div>
      </div>
      <el-input
        v-model="commentText"
        type="textarea"
        :rows="3"
        placeholder="添加评论，可用 @用户名 或 @显示名 提醒成员"
        style="margin-top: 12px"
      />
      <el-button type="primary" size="small" style="margin-top: 8px" @click="addComment">发送</el-button>
    </el-drawer>

    <el-dialog v-model="addTaskDialog" title="新建任务" width="520px">
      <el-form :model="newTask" label-position="top" @submit.prevent="createTask">
        <el-form-item label="任务标题">
          <el-input v-model="newTask.title" placeholder="请输入任务标题" />
        </el-form-item>
        <el-form-item label="当前节点描述">
          <el-input v-model="newTask.description" type="textarea" :rows="4" placeholder="输入当前节点描述" />
        </el-form-item>
        <el-form-item label="节点产出">
          <el-input v-model="newTask.node_output" type="textarea" :rows="4" placeholder="输入节点产出" />
        </el-form-item>
        <el-form-item label="关联文档">
          <el-select v-model="newTask.linked_document_id" clearable filterable style="width: 100%">
            <el-option v-for="doc in projectDocuments" :key="doc.id" :label="doc.title" :value="doc.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="newTask.assignee_id" clearable style="width: 100%">
            <el-option v-for="user in users" :key="user.id" :label="user.display_name || user.username" :value="user.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="交付时间">
          <el-date-picker v-model="newTask.due_date" type="datetime" style="width: 100%" />
        </el-form-item>
        <el-button type="primary" :loading="creating" native-type="submit" style="width: 100%" @click="createTask">
          创建任务
        </el-button>
      </el-form>
    </el-dialog>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const projects = ref([])
const selectedProject = ref(null)
const columns = ref([])
const users = ref([])
const projectDocuments = ref([])

const taskDrawer = ref(false)
const currentTask = ref(null)
const editForm = reactive({
  description: '',
  node_output: '',
  linked_document_id: null,
  assignee_id: null,
  due_date: null
})
const comments = ref([])
const commentText = ref('')
const saving = ref(false)
const claiming = ref(false)
const completing = ref(false)
const extensionDate = ref(null)
const showExtensionPicker = ref(false)

const addTaskDialog = ref(false)
const newTask = reactive({
  title: '',
  description: '',
  node_output: '',
  linked_document_id: null,
  assignee_id: null,
  due_date: null
})
const creating = ref(false)

const deliveryTimeline = computed(() => currentTask.value?.delivery_dates || [])
const currentProject = computed(() => projects.value.find(item => item.id === selectedProject.value) || null)
const canClaimTask = computed(() => currentTask.value && currentTask.value.column_id === getPendingColumnId())

onMounted(async () => {
  await auth.getMe()
  const [projectList, userList] = await Promise.all([
    api.get('/projects'),
    api.get('/auth/users')
  ])
  projects.value = projectList || []
  users.value = userList || []

  const queryProjectId = Number(route.query.project)
  if (queryProjectId) {
    selectedProject.value = queryProjectId
  } else if (projects.value.length) {
    selectedProject.value = projects.value[0].id
  }

  if (selectedProject.value) {
    await loadKanban()
    await openTaskFromQuery()
  }
})

async function handleProjectSwitch() {
  await loadKanban()
}

async function loadKanban() {
  if (!selectedProject.value) return
  loading.value = true
  router.replace({ query: { project: String(selectedProject.value) } })
  try {
    const [columnList, documentList] = await Promise.all([
      api.get(`/kanban/project/${selectedProject.value}`),
      api.get('/documents')
    ])
    columns.value = columnList || []
    projectDocuments.value = documentList || []
    await openTaskFromQuery()
  } catch (error) {
    console.error(error)
    ElMessage.error('看板加载失败')
  } finally {
    loading.value = false
  }
}

async function openTask(task) {
  currentTask.value = { ...task }
  editForm.description = task.description || ''
  editForm.node_output = task.node_output || ''
  editForm.linked_document_id = task.linked_document_id || null
  editForm.assignee_id = task.assignee_id
  editForm.due_date = task.due_date
  extensionDate.value = null
  showExtensionPicker.value = false
  comments.value = await api.get(`/tasks/${task.id}/comments`)
  taskDrawer.value = true
}

async function openTaskFromQuery() {
  const taskId = Number(route.query.task)
  if (!taskId) return
  const targetTask = columns.value.flatMap(column => column.tasks || []).find(task => task.id === taskId)
  if (!targetTask) return
  if (currentTask.value?.id === targetTask.id && taskDrawer.value) return
  await openTask(targetTask)
}

async function saveTask() {
  saving.value = true
  try {
    const updated = await api.put(`/tasks/${currentTask.value.id}`, editForm)
    currentTask.value = updated
    ElMessage.success('保存成功')
    await loadKanban()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
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
    editForm.due_date = updated.due_date
    extensionDate.value = null
    showExtensionPicker.value = false
    ElMessage.success('已记录延期时间')
    await loadKanban()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '延期失败')
  }
}

async function completeTask() {
  completing.value = true
  try {
    const updated = await api.post(`/tasks/${currentTask.value.id}/complete`)
    currentTask.value = updated
    taskDrawer.value = false
    ElMessage.success(auth.user?.role === 'admin' ? '任务已归档到已完成' : '任务已移入待验收')
    await loadKanban()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '操作失败')
  } finally {
    completing.value = false
  }
}

async function deleteTask() {
  try {
    await api.delete(`/tasks/${currentTask.value.id}`)
    ElMessage.success('删除成功')
    taskDrawer.value = false
    await loadKanban()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function addComment() {
  if (!commentText.value.trim()) return
  try {
    await api.post(`/tasks/${currentTask.value.id}/comments`, { content: commentText.value })
    commentText.value = ''
    comments.value = await api.get(`/tasks/${currentTask.value.id}/comments`)
  } catch {
    ElMessage.error('评论失败')
  }
}

function resolvePendingColumnId() {
  const pendingColumn = columns.value.find(item => item.name === '待处理')
  return pendingColumn?.id || null
}

function showAddTask() {
  newTask.title = ''
  newTask.description = ''
  newTask.node_output = ''
  newTask.linked_document_id = null
  newTask.assignee_id = null
  newTask.due_date = null
  addTaskDialog.value = true
}

async function createTask() {
  if (!newTask.title) {
    ElMessage.warning('请输入任务标题')
    return
  }
  const pendingColumnId = resolvePendingColumnId()
  if (!pendingColumnId) {
    ElMessage.error('当前项目缺少待处理列，无法创建任务')
    return
  }
  creating.value = true
  try {
    await api.post('/tasks', {
      ...newTask,
      column_id: pendingColumnId,
      project_id: selectedProject.value
    })
    ElMessage.success('任务创建成功')
    addTaskDialog.value = false
    await loadKanban()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

async function claimTask() {
  claiming.value = true
  try {
    const updated = await api.post(`/tasks/${currentTask.value.id}/claim`)
    currentTask.value = updated
    editForm.assignee_id = updated.assignee_id
    ElMessage.success('任务已领取，已移入进行中')
    await loadKanban()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '领取失败')
  } finally {
    claiming.value = false
  }
}

function resolveUser(userId) {
  return users.value.find(item => item.id === userId) || null
}

function getPendingColumnId() {
  const pendingColumn = columns.value.find(item => item.name === '待处理')
  return pendingColumn?.id || null
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
.kanban-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.project-hero {
  margin-bottom: 20px;
  padding: 22px 24px;
  border-radius: 24px;
  background: linear-gradient(135deg, #eff6ff, #f8fafc 55%, #ecfdf5);
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.project-hero-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.project-hero-title {
  margin: 8px 0 0;
  color: #0f172a;
  font-size: 30px;
  line-height: 1.1;
}

.project-hero-meta {
  margin-top: 10px;
  color: #475569;
  font-size: 14px;
  line-height: 1.6;
}

.create-task-button {
  min-width: 112px;
  font-weight: 700;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  color: #0f172a;
  font-size: 12px;
  font-weight: 600;
}

.task-card-note {
  margin-top: 10px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.task-card-link {
  margin-top: 10px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
}

.delivery-stack {
  margin-bottom: 14px;
}

.section-label {
  margin-bottom: 10px;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.delivery-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #f8fafc;
  color: #0f172a;
}

.delivery-item + .delivery-item {
  margin-top: 8px;
}

.delivery-index {
  color: #64748b;
}

.extension-panel {
  display: flex;
  gap: 12px;
  margin-bottom: 18px;
}

.extension-picker-wrap {
  margin-bottom: 18px;
}

.drawer-actions {
  display: flex;
  gap: 10px;
}
</style>
