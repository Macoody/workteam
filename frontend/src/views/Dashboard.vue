<template>
  <AppShell title="工作总览" description="快速查看项目规模、近期任务和当前协作节奏。">
    <div class="stats-grid">
      <div v-for="item in statCards" :key="item.label" class="stat-card">
        <div class="stat-label">{{ item.label }}</div>
        <div class="stat-value">{{ item.value }}</div>
        <div class="stat-footnote">{{ item.footnote }}</div>
      </div>
    </div>

    <div class="split-layout">
      <section class="panel">
        <h3 class="section-title">近期任务</h3>
        <div v-if="recentTasks.length === 0" class="empty-card">还没有任务，先从项目看板里创建第一条任务。</div>
        <div v-else class="simple-list">
          <div v-for="task in recentTasks" :key="task.id" class="simple-list-item">
            <span class="status-pill" :style="statusPillStyle(task)">
              {{ resolveTaskStatus(task) }}
            </span>
            <div class="item-main">
              <div class="item-title">{{ task.title }}</div>
              <div class="item-meta">
                {{ resolveProjectName(task.project_id) }}
                <span v-if="resolveUser(task.assignee_id)" class="meta-separator">·</span>
                <span
                  v-if="resolveUser(task.assignee_id)"
                  class="user-pill"
                  :style="{ background: resolveUser(task.assignee_id).color || '#93c5fd' }"
                >
                  {{ resolveUser(task.assignee_id).display_name || resolveUser(task.assignee_id).username }}
                </span>
                <span v-if="latestDeliveryDate(task)"> · 交付 {{ formatDate(latestDeliveryDate(task)) }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="panel">
        <h3 class="section-title">当前状态</h3>
        <div class="simple-list">
          <div class="simple-list-item">
            <div class="item-main">
              <div class="item-title">我的待办</div>
              <div class="item-meta">当前账号名下的任务数</div>
            </div>
            <strong>{{ stats.myTasks }}</strong>
          </div>
          <div class="simple-list-item">
            <div class="item-main">
              <div class="item-title">文档沉淀</div>
              <div class="item-meta">已经创建的文档数量</div>
            </div>
            <strong>{{ stats.documents }}</strong>
          </div>
          <div class="simple-list-item">
            <div class="item-main">
              <div class="item-title">活跃项目</div>
              <div class="item-meta">当前系统中的项目总数</div>
            </div>
            <strong>{{ stats.projects }}</strong>
          </div>
        </div>
      </section>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'

const auth = useAuthStore()
const stats = ref({ projects: 0, tasks: 0, myTasks: 0, documents: 0 })
const recentTasks = ref([])
const projects = ref([])
const users = ref([])
const columnsById = ref({})

const statCards = computed(() => [
  { label: '项目总数', value: stats.value.projects, footnote: '已创建的协作空间' },
  { label: '任务总数', value: stats.value.tasks, footnote: '系统中的全部任务' },
  { label: '我的任务', value: stats.value.myTasks, footnote: '待继续推进的事项' },
  { label: '文档数量', value: stats.value.documents, footnote: '沉淀中的知识资料' }
])

onMounted(async () => {
  await auth.getMe()
  try {
    const [projectList, taskList, myTasks, docs, userList] = await Promise.all([
      api.get('/projects'),
      api.get('/tasks'),
      api.get('/tasks?my_tasks=true'),
      api.get('/documents'),
      api.get('/auth/users')
    ])
    projects.value = projectList || []
    users.value = userList || []
    const kanbanLists = await Promise.all(
      (projectList || []).map(project => api.get(`/kanban/project/${project.id}`))
    )
    const nextColumnsById = {}
    kanbanLists.flat().forEach(column => {
      nextColumnsById[column.id] = {
        name: column.name,
        color: column.color || '#94a3b8'
      }
    })
    columnsById.value = nextColumnsById
    stats.value = {
      projects: Array.isArray(projectList) ? projectList.length : 0,
      tasks: Array.isArray(taskList) ? taskList.length : 0,
      myTasks: Array.isArray(myTasks) ? myTasks.length : 0,
      documents: Array.isArray(docs) ? docs.length : 0
    }
    recentTasks.value = (taskList || []).slice(0, 8)
  } catch (error) {
    console.error(error)
  }
})

function resolveProjectName(projectId) {
  const project = projects.value.find(item => item.id === projectId)
  return project?.name || `项目 #${projectId}`
}

function resolveUser(userId) {
  if (!userId) return null
  return users.value.find(item => item.id === userId) || null
}

function resolveTaskStatus(task) {
  return columnsById.value[task.column_id]?.name || '未分配状态'
}

function statusPillStyle(task) {
  const color = columnsById.value[task.column_id]?.color || '#94a3b8'
  return {
    background: `${color}1f`,
    color,
    boxShadow: `inset 0 0 0 1px ${color}33`
  }
}

function latestDeliveryDate(task) {
  const dates = task?.delivery_dates || []
  return dates[dates.length - 1] || task?.due_date || null
}

function formatDate(value) {
  return dayjs(value).format('MM-DD HH:mm')
}
</script>

<style scoped>
.meta-separator {
  margin: 0 6px;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  color: #0f172a;
  font-size: 12px;
  font-weight: 600;
  vertical-align: middle;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 76px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}
</style>
