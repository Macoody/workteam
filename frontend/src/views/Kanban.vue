<template>
  <div class="kanban-page">
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
        <header class="header header-flex">
          <span>看板</span>
          <div class="header-right">
            <el-select v-model="selectedProject" placeholder="选择项目" size="small" @change="loadKanban" style="width:160px">
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
            <el-button size="small" @click="loadKanban">刷新</el-button>
          </div>
        </header>
        <div v-if="loading" style="text-align:center;padding:40px;color:#999">加载看板中...</div>
        <div v-else class="kanban-board">
          <div v-for="col in columns" :key="col.id" class="column">
            <div class="column-header">
              <span class="column-name">{{ col.name }}</span>
              <span class="column-count">{{ col.tasks?.length || 0 }}</span>
            </div>
            <div class="column-body">
              <div v-for="task in (col.tasks || [])" :key="task.id" class="task-card" @click="openTask(task)">
                <div class="task-title">{{ task.title }}</div>
                <div v-if="task.assignee_id" class="info-row">
                  <span class="info-label">负责人</span>
                  <span>{{ task.assignee_id }}</span>
                </div>
                <div v-if="task.due_date" class="info-row">
                  <span class="info-label">截止日期</span>
                  <span>{{ task.due_date }}</span>
                </div>
                <div v-if="task.priority" class="info-row">
                  <span class="info-label">优先级</span>
                  <el-tag :type="task.priority === 'high' ? 'danger' : task.priority === 'low' ? 'info' : 'warning'" size="small">{{ task.priority }}</el-tag>
                </div>
              </div>
              <div class="add-task-hint" @click="showAddTask(col.id)">+ 添加任务</div>
            </div>
          </div>
        </div>
      </el-main>
    </el-container>

    <!-- 任务详情抽屉 -->
    <el-drawer v-model="taskDrawer" :title="currentTask?.title" size="480px">
      <div v-if="currentTask">
        <el-form label-position="top">
          <el-form-item label="描述">
            <el-input v-model="editForm.description" type="textarea" rows="3" />
          </el-form-item>
          <el-form-item label="优先级">
            <el-select v-model="editForm.priority">
              <el-option label="低" value="low" />
              <el-option label="中" value="medium" />
              <el-option label="高" value="high" />
            </el-select>
          </el-form-item>
          <el-form-item label="负责人">
            <el-select v-model="editForm.assignee_id" clearable>
              <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="截止日期">
            <el-date-picker v-model="editForm.due_date" type="datetime" placeholder="选择日期时间" style="width:100%" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveTask">保存</el-button>
            <el-button type="danger" @click="deleteTask" style="margin-left:10px">删除</el-button>
          </el-form-item>
        </el-form>
        <el-divider />
        <h4>评论</h4>
        <div class="comment-list">
          <div v-for="c in comments" :key="c.id" class="comment-item">
            <div class="comment-user">{{ c.user?.display_name || c.user?.username }}</div>
            <div class="comment-content">{{ c.content }}</div>
            <div class="comment-time">{{ c.created_at }}</div>
          </div>
        </div>
        <el-input v-model="commentText" type="textarea" rows="2" placeholder="添加评论" style="margin-top:10px" />
        <el-button type="primary" size="small" @click="addComment" style="margin-top:5px">发送</el-button>
      </div>
    </el-drawer>

    <!-- 新建任务弹窗 -->
    <el-dialog v-model="addTaskDialog" title="新建任务" width="450px">
      <el-form :model="newTask" label-position="top" @submit.prevent="createTask">
        <el-form-item label="任务标题">
          <el-input v-model="newTask.title" placeholder="请输入任务标题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newTask.description" type="textarea" rows="3" placeholder="输入任务描述" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="newTask.priority" style="width:100%">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="newTask.assignee_id" clearable placeholder="选择成员" style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="newTask.due_date" type="datetime" placeholder="选择日期时间" style="width:100%" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="creating" native-type="submit" style="width:100%" @click="createTask">创建</el-button>
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
const projects = ref([])
const selectedProject = ref(null)
const columns = ref([])
const users = ref([])

const taskDrawer = ref(false)
const currentTask = ref(null)
const editForm = reactive({ description: '', priority: '', assignee_id: null, due_date: null })
const comments = ref([])
const commentText = ref('')
const saving = ref(false)

const addTaskDialog = ref(false)
const newTask = reactive({ title: '', description: '', priority: 'medium', assignee_id: null, due_date: null })
const addColId = ref(null)
const creating = ref(false)
onMounted(async () => {
  await auth.getMe()
  const proj_data = await api.get('/projects')
  projects.value = proj_data
  if (projects.value.length > 0) {
    selectedProject.value = projects.value[0].id
    await loadKanban()
  }
  // 加载成员列表（用于下拉选择负责人）
  try {
    const user_data = await api.get('/users')
    users.value = user_data
  } catch (e) {
    console.error('loadUsers failed', e)
  }
})

async function loadKanban() {
  if (!selectedProject.value) return
  loading.value = true
  try {
    const data = await api.get(`/kanban?project_id=${selectedProject.value}`)
    columns.value = data.columns || []
  } catch (e) {
    // Fallback: load tasks and group by column
    const tasks = await api.get(`/tasks?project_id=${selectedProject.value}`)
    columns.value = tasks
  }
  loading.value = false
}

async function openTask(task) {
  currentTask.value = task
  editForm.description = task.description || ''
  editForm.priority = task.priority || 'medium'
  editForm.assignee_id = task.assignee_id
  editForm.due_date = task.due_date
  comments.value = await api.get(`/tasks/${task.id}/comments`)
  taskDrawer.value = true
}

async function saveTask() {
  saving.value = true
  try {
    await api.put(`/tasks/${currentTask.value.id}`, editForm)
    ElMessage.success('保存成功')
    taskDrawer.value = false
    loadKanban()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function deleteTask() {
  try {
    await api.delete(`/tasks/${currentTask.value.id}`)
    ElMessage.success('删除成功')
    taskDrawer.value = false
    loadKanban()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function addComment() {
  if (!commentText.value.trim()) return
  try {
    await api.post(`/tasks/${currentTask.value.id}/comments`, { content: commentText.value })
    commentText.value = ''
    comments.value = await api.get(`/tasks/${currentTask.value.id}/comments`)
  } catch (e) {
    ElMessage.error('评论失败')
  }
}

function showAddTask(colId) {
  addColId.value = colId
  newTask.title = ''
  newTask.description = ''
  newTask.priority = 'medium'
  newTask.assignee_id = null
  newTask.due_date = null
  addTaskDialog.value = true
}

async function createTask() {
  if (!newTask.title) { ElMessage.warning('请输入任务标题'); return }
  creating.value = true
  try {
    await api.post('/tasks', {
      ...newTask,
      column_id: addColId.value,
      project_id: selectedProject.value
    })
    ElMessage.success('任务创建成功')
    addTaskDialog.value = false
    loadKanban()
  } catch (e) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.kanban-page { display: flex; height: 100vh; background: #f0f2f5; }
.logo { position: fixed; top: 0; left: 0; width: 200px; height: 60px; background: #545c64; color: white; display: flex; align-items: center; padding: 0 20px; font-size: 14px; font-weight: bold; z-index: 10; }
.sidebar { width: 200px; background: #fff; border-right: 1px solid #eee; padding-top: 60px; }
.sidebar-footer { padding: 10px; border-bottom: 1px solid #eee; }
.user-name { font-weight: bold; }
.nav-item { display: block; padding: 12px 20px; color: #333; text-decoration: none; border-bottom: 1px solid #f0f0f0; }
.nav-item.active { background: #ecf5ff; color: #409eff; }
.main { margin-left: 200px; }
.header { padding: 15px 20px; background: white; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.header-flex { justify-content: space-between; }
.header-right { display: flex; gap: 10px; align-items: center; }
.kanban-board { display: flex; gap: 16px; padding: 20px; overflow-x: auto; height: calc(100vh - 60px); align-items: flex-start; }
.column { width: 280px; background: #f5f5f5; border-radius: 8px; min-height: 200px; }
.column-header { padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e0e0e0; }
.column-name { font-weight: bold; }
.column-count { background: #ddd; border-radius: 10px; padding: 2px 8px; font-size: 12px; }
.column-body { padding: 10px; min-height: 100px; }
.task-card { background: white; border-radius: 6px; padding: 12px; margin-bottom: 8px; cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.task-title { font-weight: 500; margin-bottom: 8px; }
.info-row { display: flex; justify-content: space-between; font-size: 12px; color: #666; margin-top: 4px; }
.info-label { color: #999; }
.add-task-hint { text-align: center; padding: 10px; color: #999; cursor: pointer; }
.add-task-hint:hover { color: #409eff; }
.comment-list { max-height: 300px; overflow-y: auto; }
.comment-item { padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
.comment-user { font-weight: bold; font-size: 13px; }
.comment-content { margin-top: 4px; font-size: 14px; }
.comment-time { font-size: 12px; color: #999; margin-top: 4px; }
</style>