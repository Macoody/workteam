<template>
  <AppShell title="徐东摆地摊" description="把项目、任务和文档收进一个简洁的工作台。">
    <section class="workbench-hero">
      <div class="workbench-hero-copy">
        <div class="workbench-kicker">今日摊位</div>
        <h2>项目有摊位，任务有去处，文档有地方放。</h2>
        <p>打开首页先看最要紧的三样东西，再从这里进入看板、任务列表或文档中心。</p>
      </div>
      <div class="workbench-actions" aria-label="工作台快捷入口">
        <button
          v-for="action in quickActions"
          :key="action.label"
          type="button"
          class="workbench-action"
          @click="go(action.to)"
        >
          <el-icon><component :is="action.icon" /></el-icon>
          <span>{{ action.label }}</span>
        </button>
      </div>
    </section>

    <div class="workbench-stats">
      <button
        v-for="item in statCards"
        :key="item.label"
        type="button"
        class="workbench-stat"
        @click="go(item.to)"
      >
        <span class="workbench-stat-icon">
          <el-icon><component :is="item.icon" /></el-icon>
        </span>
        <span class="workbench-stat-copy">
          <span class="stat-label">{{ item.label }}</span>
          <span class="stat-value">{{ item.value }}</span>
          <span class="stat-footnote">{{ item.footnote }}</span>
        </span>
      </button>
    </div>

    <div class="workbench-grid">
      <section class="panel workbench-panel">
        <div class="workbench-panel-header">
          <div>
            <h3 class="section-title">项目摊位</h3>
            <p>最近创建的协作空间</p>
          </div>
          <el-button text type="primary" @click="go('/projects')">全部项目</el-button>
        </div>
        <div v-if="latestProjects.length === 0" class="empty-card compact-empty">还没有项目，先创建一个新的协作空间。</div>
        <div v-else class="compact-stack">
          <button
            v-for="project in latestProjects"
            :key="project.id"
            type="button"
            class="compact-row"
            @click="goToKanban(project.id)"
          >
            <span class="row-mark project-mark">{{ project.name.slice(0, 1) }}</span>
            <span class="item-main">
              <span class="item-title">{{ project.name }}</span>
              <span class="item-meta">{{ project.description || '暂无项目说明' }}</span>
            </span>
            <el-icon class="row-arrow"><ArrowRight /></el-icon>
          </button>
        </div>
      </section>

      <section class="panel workbench-panel workbench-panel-wide">
        <div class="workbench-panel-header">
          <div>
            <h3 class="section-title">任务货架</h3>
            <p>最近需要推进的任务</p>
          </div>
          <el-button text type="primary" @click="go('/tasks')">全部任务</el-button>
        </div>
        <div v-if="recentTasks.length === 0" class="empty-card compact-empty">还没有任务，先从项目看板里创建第一条任务。</div>
        <div v-else class="compact-stack task-stack">
          <button
            v-for="task in recentTasks"
            :key="task.id"
            type="button"
            class="compact-row task-jump-card"
            @click="openTask(task)"
          >
            <span class="status-pill" :style="statusPillStyle(task)">
              {{ resolveTaskStatus(task) }}
            </span>
            <span class="item-main">
              <span class="item-title">{{ task.title }}</span>
              <span class="item-meta">
                {{ resolveProjectName(task.project_id) }}
                <span v-if="resolveUser(task.assignee_id)" class="meta-separator">·</span>
                <span
                  v-if="resolveUser(task.assignee_id)"
                  class="user-pill"
                  :style="{ background: resolveUser(task.assignee_id).color || '#93c5fd' }"
                  :title="userPresenceTitle(resolveUser(task.assignee_id))"
                >
                  <span class="mini-presence-dot" :class="{ online: isUserOnline(resolveUser(task.assignee_id)) }"></span>
                  {{ resolveUser(task.assignee_id).display_name || resolveUser(task.assignee_id).username }}
                  <span class="user-presence-text">{{ userPresenceText(resolveUser(task.assignee_id)) }}</span>
                </span>
                <span v-if="latestDeliveryDate(task)"> · 交付 {{ formatDate(latestDeliveryDate(task)) }}</span>
              </span>
              <span v-if="task.recent_comments?.length" class="task-comment-stack">
                <span v-for="comment in task.recent_comments" :key="comment.id" class="task-comment-chip">
                  <span class="task-comment-author">
                    {{ comment.user?.display_name || comment.user?.username || '成员' }}
                  </span>
                  <span class="task-comment-text">{{ comment.content }}</span>
                </span>
              </span>
            </span>
            <el-icon class="row-arrow"><ArrowRight /></el-icon>
          </button>
        </div>
      </section>

      <section class="panel workbench-panel">
        <div class="workbench-panel-header">
          <div>
            <h3 class="section-title">文档箱</h3>
            <p>近期沉淀的资料</p>
          </div>
          <el-button text type="primary" @click="go('/documents')">全部文档</el-button>
        </div>
        <div v-if="latestDocuments.length === 0" class="empty-card compact-empty">还没有文档，先创建一篇项目记录或说明文档。</div>
        <div v-else class="compact-stack">
          <button
            v-for="doc in latestDocuments"
            :key="doc.id"
            type="button"
            class="compact-row"
            @click="go(`/documents/${doc.id}`)"
          >
            <span class="row-mark doc-mark">
              <el-icon><Document /></el-icon>
            </span>
            <span class="item-main">
              <span class="item-title">{{ doc.title }}</span>
              <span class="item-meta">{{ docTypeLabel(doc.doc_type) }} · 最后编辑 {{ documentEditorName(doc) }} · {{ formatDate(documentEditedAt(doc)) }}</span>
            </span>
            <el-icon class="row-arrow"><ArrowRight /></el-icon>
          </button>
        </div>
      </section>

      <section class="panel workbench-panel">
        <div class="workbench-panel-header">
          <div>
            <h3 class="section-title">@我的提醒</h3>
            <p>新的评论和协作提醒</p>
          </div>
        </div>
        <div v-if="unreadMentionNotifications.length === 0" class="empty-card compact-empty">暂时没有新的 @ 提醒。</div>
        <div v-else class="compact-stack">
          <button
            v-for="item in unreadMentionNotifications"
            :key="item.id"
            type="button"
            class="mention-card"
            @click="openMention(item)"
          >
            <span class="item-main">
              <span class="item-title">
                {{ item.mentioned_by?.display_name || item.mentioned_by?.username || '成员' }}
                @了你
              </span>
              <span class="item-meta">{{ item.project_name || resolveProjectName(item.project_id) }} · {{ item.task_title }}</span>
              <span class="mention-preview">{{ item.comment_content }}</span>
            </span>
            <span class="mention-time">{{ formatDate(item.created_at) }}</span>
          </button>
        </div>
      </section>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { ArrowRight, Document, FolderOpened, List, Odometer } from '@element-plus/icons-vue'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'
import { isUserOnline, userPresenceText, userPresenceTitle } from '@/utils/presence'

const router = useRouter()
const auth = useAuthStore()
const stats = ref({ projects: 0, tasks: 0, myTasks: 0, documents: 0 })
const recentTasks = ref([])
const projects = ref([])
const documents = ref([])
const users = ref([])
const columnsById = ref({})
const mentionNotifications = ref([])
let usersRefreshTimer = null

const statCards = computed(() => [
  { label: '项目', value: stats.value.projects, footnote: '协作空间', to: '/projects', icon: FolderOpened },
  { label: '任务', value: stats.value.tasks, footnote: '全部事项', to: '/tasks', icon: List },
  { label: '我的待办', value: stats.value.myTasks, footnote: '待推进', to: '/tasks', icon: Odometer },
  { label: '文档', value: stats.value.documents, footnote: '资料沉淀', to: '/documents', icon: Document }
])
const quickActions = [
  { label: '项目', to: '/projects', icon: FolderOpened },
  { label: '任务', to: '/tasks', icon: List },
  { label: '文档', to: '/documents', icon: Document }
]
const latestProjects = computed(() => projects.value.slice(0, 4))
const latestDocuments = computed(() =>
  documents.value
    .slice()
    .sort((a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0))
    .slice(0, 4)
)
const unreadMentionNotifications = computed(() => mentionNotifications.value.filter(item => !item.is_read))

onMounted(async () => {
  await auth.getMe()
  try {
    const [projectList, taskList, myTasks, docs, userList, mentions] = await Promise.all([
      api.get('/projects'),
      api.get('/tasks'),
      api.get('/tasks?my_tasks=true'),
      api.get('/documents'),
      api.get('/auth/users'),
      api.get('/tasks/comment-mentions/me')
    ])
    projects.value = projectList || []
    documents.value = docs || []
    users.value = userList || []
    mentionNotifications.value = mentions || []
    const kanbanResults = await Promise.allSettled(
      (projectList || []).map(project => api.get(`/kanban/project/${project.id}`))
    )
    const nextColumnsById = {}
    kanbanResults.forEach(result => {
      if (result.status === 'fulfilled') {
        (result.value || []).forEach(column => {
          nextColumnsById[column.id] = {
            name: column.name,
            color: column.color || '#94a3b8'
          }
        })
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
    usersRefreshTimer = window.setInterval(refreshUsers, 30000)
  } catch (error) {
    console.error(error)
  }
})

onUnmounted(() => {
  if (usersRefreshTimer) {
    window.clearInterval(usersRefreshTimer)
    usersRefreshTimer = null
  }
})

async function refreshUsers() {
  try {
    users.value = await api.get('/auth/users')
  } catch (error) {
    console.error(error)
  }
}

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
  return value ? dayjs(value).format('MM-DD HH:mm') : '--'
}

function docTypeLabel(type) {
  if (type === 'sheet') return '表格'
  if (type === 'ppt') return '演示'
  if (type === 'file') return '文件'
  return '文档'
}

function documentEditorName(doc) {
  const user = doc?.last_editor || doc?.creator
  return user?.display_name || user?.username || '未知成员'
}

function documentEditedAt(doc) {
  return doc?.last_edited_at || doc?.updated_at || doc?.created_at
}

async function openMention(item) {
  try {
    if (!item.is_read) {
      await api.post(`/tasks/comment-mentions/${item.id}/read`)
      item.is_read = true
    }
  } catch (error) {
    console.error(error)
  }
  router.push(`/kanban?project=${item.project_id}&task=${item.task_id}`)
}

function openTask(task) {
  router.push(`/kanban?project=${task.project_id}&task=${task.id}`)
}

function go(path) {
  router.push(path)
}

function goToKanban(projectId) {
  router.push(`/kanban?project=${projectId}`)
}
</script>

<style scoped>
.workbench-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
  padding: 28px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(240, 253, 250, 0.88)),
    linear-gradient(90deg, rgba(249, 115, 22, 0.08), rgba(20, 184, 166, 0.08));
  box-shadow: var(--wt-shadow);
  overflow: hidden;
}

.workbench-hero-copy {
  max-width: 680px;
}

.workbench-kicker {
  margin-bottom: 12px;
  color: #0f766e;
  font-size: 13px;
  font-weight: 800;
}

.workbench-hero h2 {
  margin: 0;
  font-size: 34px;
  line-height: 1.16;
}

.workbench-hero p {
  margin: 12px 0 0;
  color: #475569;
  font-size: 15px;
  line-height: 1.7;
}

.workbench-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.workbench-action {
  min-width: 88px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  background: #0f172a;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: 0.2s ease;
}

.workbench-action:hover {
  transform: translateY(-2px);
  background: #134e4a;
}

.workbench-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.workbench-stat {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--wt-border);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: var(--wt-shadow);
  text-align: left;
  cursor: pointer;
  transition: 0.2s ease;
}

.workbench-stat:hover {
  transform: translateY(-2px);
  border-color: rgba(20, 184, 166, 0.26);
}

.workbench-stat-icon {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  display: inline-grid;
  place-items: center;
  border-radius: 14px;
  background: #ecfeff;
  color: #0f766e;
  font-size: 20px;
}

.workbench-stat-copy {
  min-width: 0;
  display: grid;
  gap: 5px;
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(260px, 0.9fr) minmax(360px, 1.35fr) minmax(260px, 0.9fr);
  gap: 18px;
  align-items: start;
}

.workbench-panel {
  min-width: 0;
  padding: 20px;
}

.workbench-panel-wide {
  grid-row: span 2;
}

.workbench-panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.workbench-panel-header p {
  margin: -6px 0 0;
  color: var(--wt-muted);
  font-size: 12px;
}

.compact-stack {
  display: grid;
  gap: 8px;
}

.compact-row,
.mention-card {
  width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.72);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: 0.2s ease;
}

.compact-row:hover,
.mention-card:hover {
  border-color: rgba(20, 184, 166, 0.24);
  background: #ffffff;
}

.compact-row .item-main,
.mention-card .item-main {
  display: grid;
  gap: 4px;
}

.row-mark {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  display: inline-grid;
  place-items: center;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 800;
}

.project-mark {
  background: #fef3c7;
  color: #92400e;
}

.doc-mark {
  background: #e0f2fe;
  color: #0369a1;
}

.row-arrow {
  flex: 0 0 auto;
  color: #94a3b8;
}

.compact-empty {
  padding: 24px 16px;
  box-shadow: none;
}

.task-stack {
  gap: 10px;
}

.task-jump-card {
  width: 100%;
}

.meta-separator {
  margin: 0 6px;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  color: #0f172a;
  font-size: 12px;
  font-weight: 600;
  vertical-align: middle;
}

.mini-presence-dot {
  width: 7px;
  height: 7px;
  flex: 0 0 7px;
  border-radius: 999px;
  background: #94a3b8;
}

.mini-presence-dot.online {
  background: #16a34a;
}

.user-presence-text {
  color: rgba(15, 23, 42, 0.68);
  font-size: 11px;
  font-weight: 700;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  min-width: 76px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.task-comment-stack {
  margin-top: 8px;
  display: grid;
  gap: 8px;
}

.task-comment-chip {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 8px 10px;
  border-radius: 12px;
  background: #f8fafc;
}

.task-comment-author {
  flex: 0 0 auto;
  color: #0f172a;
  font-size: 12px;
  font-weight: 700;
}

.task-comment-text {
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}

.mention-card {
  align-items: flex-start;
  justify-content: space-between;
}

.mention-preview {
  color: #475569;
  font-size: 13px;
  line-height: 1.5;
}

.mention-time {
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}

@media (max-width: 1180px) {
  .workbench-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workbench-panel-wide {
    grid-row: auto;
  }
}

@media (max-width: 920px) {
  .workbench-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .workbench-actions {
    justify-content: flex-start;
  }

  .workbench-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .workbench-hero {
    gap: 18px;
    margin-bottom: 14px;
    padding: 20px;
    border-radius: 18px;
  }

  .workbench-hero h2 {
    font-size: 24px;
    line-height: 1.2;
  }

  .workbench-action {
    width: 100%;
  }

  .workbench-actions {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .workbench-action {
    min-width: 0;
    height: 40px;
    padding: 0 8px;
    border-radius: 12px;
  }

  .workbench-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 14px;
  }

  .workbench-stat {
    align-items: flex-start;
    gap: 10px;
    padding: 12px;
    border-radius: 15px;
  }

  .workbench-stat-icon {
    width: 34px;
    height: 34px;
    flex-basis: 34px;
    border-radius: 12px;
  }

  .workbench-stat .stat-value {
    font-size: 24px;
  }

  .workbench-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .workbench-panel {
    padding: 16px;
    border-radius: 16px;
  }

  .compact-row,
  .mention-card {
    align-items: flex-start;
    padding: 10px;
    border-radius: 12px;
  }

  .status-pill {
    min-width: 66px;
  }

  .task-comment-chip {
    display: grid;
    gap: 4px;
  }

  .mention-card {
    display: grid;
    gap: 8px;
  }

  .mention-time,
  .user-presence-text {
    display: none;
  }
}
</style>
