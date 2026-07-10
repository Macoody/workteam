<template>
  <AppShell title="成员管理" description="集中维护团队成员，支持新增、编辑、颜色选择和停用账号。">
    <template #actions>
      <el-button type="primary" @click="openCreate">添加成员</el-button>
      <el-button @click="loadMembers">刷新</el-button>
    </template>

    <div class="panel table-panel">
      <el-table :data="members" style="width: 100%" v-loading="loading">
        <el-table-column prop="display_name" label="成员" min-width="200">
          <template #default="{ row }">
            <div class="member-identity">
              <span class="member-avatar-wrap">
                <span class="member-color-dot" :style="{ background: row.color || '#93c5fd' }"></span>
                <span class="member-online-dot" :class="{ online: isUserOnline(row) }"></span>
              </span>
              <div>
                <button type="button" class="member-name-button" @click.stop="openMemberTasks(row)">
                  {{ memberName(row) }}
                </button>
                <div class="item-meta">@{{ row.username }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="标记色" width="120">
          <template #default="{ row }">
            <span class="member-color-pill" :style="{ background: row.color || '#93c5fd' }"></span>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag effect="light">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" width="160">
          <template #default="{ row }">
            {{ row.phone || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="在线状态" width="180">
          <template #default="{ row }">
            <div class="member-presence" :title="userPresenceTitle(row)">
              <span class="presence-dot" :class="{ online: isUserOnline(row) }"></span>
              <span :class="{ 'presence-online-text': isUserOnline(row), 'text-muted': !isUserOnline(row) }">
                {{ userPresenceText(row) }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="最后活跃时间" width="180">
          <template #default="{ row }">
            <span :class="row.last_active_time ? '' : 'text-muted'">
              {{ formatDate(row.last_active_time) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <div style="display: flex; gap: 8px">
              <el-button size="small" @click="openEdit(row)">编辑</el-button>
              <el-button
                size="small"
                type="danger"
                plain
                :disabled="row.id === auth.user?.id"
                @click="confirmDelete(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-drawer
      v-model="memberTasksDrawer"
      :title="selectedMember ? `${memberName(selectedMember)} 的任务` : '成员任务'"
      size="min(680px, 92vw)"
      append-to-body
    >
      <div class="drawer-toolbar">
        <div>
          <div class="drawer-summary-title">{{ selectedMember ? `@${selectedMember.username}` : '' }}</div>
          <div class="drawer-summary-meta">{{ memberTasks.length }} 个任务</div>
        </div>
        <el-button size="small" :loading="memberTasksLoading" @click="loadMemberTasks()">刷新</el-button>
      </div>

      <div class="member-task-list-wrap" v-loading="memberTasksLoading">
        <el-empty v-if="!memberTasksLoading && !memberTasks.length" description="这个成员暂时没有归属任务" />
        <div v-else class="member-task-list">
          <div
            v-for="task in memberTasks"
            :key="task.id"
            class="member-task-item"
            :class="{ completed: taskStatusName(task) === '已完成' }"
            :style="{ borderColor: task.column_color || '#e5e7eb' }"
          >
            <div class="member-task-header">
              <div class="member-task-title">
                {{ task.title }}
                <el-tag v-if="task.recurrence_rule_id" size="small" effect="light" class="task-kind-tag">周期</el-tag>
              </div>
              <el-tag :type="statusTagType(task)" effect="light" class="status-tag">
                {{ taskStatusName(task) }}
              </el-tag>
            </div>
            <div class="member-task-meta">
              <span>{{ resolveProjectName(task.project_id) }}</span>
              <span>{{ taskTimeText(task) }}</span>
            </div>
            <div v-if="task.node_output" class="member-task-output">{{ task.node_output }}</div>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="showDialog" :title="editingUserId ? '编辑成员' : '添加成员'" width="520px">
      <el-form :model="form" label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="用户名" v-if="!editingUserId">
          <el-input v-model="form.username" placeholder="用于登录的用户名" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="form.display_name" placeholder="团队里显示的名字" />
        </el-form-item>
        <el-form-item label="成员颜色">
          <div class="color-grid">
            <button
              v-for="option in USER_COLOR_OPTIONS"
              :key="option.value"
              type="button"
              class="color-swatch"
              :class="{ active: form.color === option.value }"
              :style="{ background: option.value }"
              @click="form.color = option.value"
            >
              <span>{{ option.name }}</span>
            </button>
          </div>
        </el-form-item>
        <el-form-item :label="editingUserId ? '重置密码' : '初始密码'">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="editingUserId ? '留空则不修改密码' : '设置初始密码'"
          />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="成员" value="member" />
            <el-option label="管理员" value="admin" />
            <el-option label="访客" value="guest" />
          </el-select>
        </el-form-item>
        <el-button type="primary" :loading="saving" style="width: 100%" native-type="submit" @click="handleSubmit">
          {{ editingUserId ? '保存修改' : '创建成员' }}
        </el-button>
      </el-form>
    </el-dialog>
  </AppShell>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'
import { USER_COLOR_OPTIONS } from '@/utils/userColors'
import { isUserOnline, userPresenceText, userPresenceTitle } from '@/utils/presence'

const auth = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const editingUserId = ref(null)
const members = ref([])
const projects = ref([])
const memberTasksDrawer = ref(false)
const selectedMember = ref(null)
const memberTasks = ref([])
const memberTasksLoading = ref(false)
let membersRefreshTimer = null
const form = reactive({
  username: '',
  display_name: '',
  password: '',
  phone: '',
  role: 'member',
  color: '#93c5fd'
})

onMounted(async () => {
  await auth.getMe()
  await Promise.all([
    loadMembers(),
    loadProjects()
  ])
  membersRefreshTimer = window.setInterval(() => {
    loadMembers(true)
  }, 30000)
})

onUnmounted(() => {
  if (membersRefreshTimer) {
    window.clearInterval(membersRefreshTimer)
    membersRefreshTimer = null
  }
})

async function loadMembers(silent = false) {
  if (!silent) loading.value = true
  try {
    members.value = await api.get('/auth/users')
  } catch (error) {
    console.error(error)
    if (!silent) ElMessage.error('成员列表加载失败')
  } finally {
    if (!silent) loading.value = false
  }
}

async function loadProjects() {
  try {
    projects.value = await api.get('/projects')
  } catch (error) {
    console.error(error)
  }
}

async function openMemberTasks(user) {
  selectedMember.value = user
  memberTasks.value = []
  memberTasksDrawer.value = true
  await loadMemberTasks(user)
}

async function loadMemberTasks(user = selectedMember.value) {
  if (!user?.id) return
  const targetUserId = user.id
  memberTasksLoading.value = true
  try {
    const tasks = await api.get(`/tasks?assignee_id=${encodeURIComponent(targetUserId)}`)
    if (selectedMember.value?.id === targetUserId) {
      memberTasks.value = sortTasksByLatest(tasks)
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('成员任务加载失败')
  } finally {
    memberTasksLoading.value = false
  }
}

function openCreate() {
  editingUserId.value = null
  resetForm()
  showDialog.value = true
}

function openEdit(user) {
  editingUserId.value = user.id
  form.username = user.username
  form.display_name = user.display_name || ''
  form.password = ''
  form.phone = user.phone || ''
  form.role = user.role || 'member'
  form.color = user.color || '#93c5fd'
  showDialog.value = true
}

async function handleSubmit() {
  if (!editingUserId.value && (!form.username || !form.password)) {
    ElMessage.warning('请填写用户名和初始密码')
    return
  }

  saving.value = true
  try {
    if (editingUserId.value) {
      await api.put(`/auth/users/${editingUserId.value}`, {
        display_name: form.display_name,
        password: form.password || undefined,
        phone: form.phone,
        role: form.role,
        color: form.color
      })
      ElMessage.success('成员信息已更新')
    } else {
      await api.post('/auth/users', form)
      ElMessage.success('成员创建成功')
    }
    showDialog.value = false
    resetForm()
    await loadMembers()
  } catch (error) {
    const detail = error?.response?.data?.detail
    ElMessage.error(detail || '成员保存失败')
  } finally {
    saving.value = false
  }
}

async function confirmDelete(user) {
  try {
    await ElMessageBox.confirm(`确定删除成员“${memberName(user)}”吗？`, '删除成员', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await api.delete(`/auth/users/${user.id}`)
    ElMessage.success('成员已删除')
    await loadMembers()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    const detail = error?.response?.data?.detail
    ElMessage.error(detail || '删除失败')
  }
}

function resetForm() {
  form.username = ''
  form.display_name = ''
  form.password = ''
  form.phone = ''
  form.role = 'member'
  form.color = '#93c5fd'
}

function roleLabel(role) {
  if (role === 'admin') return '管理员'
  if (role === 'guest') return '访客'
  return '成员'
}

function memberName(user) {
  return user?.display_name || user?.username || '成员'
}

function resolveProjectName(projectId) {
  const project = projects.value.find(item => item.id === projectId)
  return project?.name || `项目 #${projectId}`
}

function taskStatusName(task) {
  return task?.column_name || '未知状态'
}

function statusTagType(task) {
  const status = taskStatusName(task)
  if (status === '已完成') return 'success'
  if (status === '进行中') return 'warning'
  if (status === '待验收') return 'primary'
  if (status === '待处理') return 'info'
  return 'info'
}

function latestDeliveryDate(task) {
  const dates = task?.delivery_dates || []
  return dates[dates.length - 1] || task?.due_date || null
}

function isCompletionStatus(task) {
  return ['待验收', '已完成'].includes(taskStatusName(task))
}

function taskTimeText(task) {
  if (isCompletionStatus(task) && task?.completed_at) return `完成 ${formatTaskDate(task.completed_at)}`
  const deliveryDate = latestDeliveryDate(task)
  return deliveryDate ? `交付 ${formatTaskDate(deliveryDate)}` : '--'
}

function latestTaskTime(task) {
  if (isCompletionStatus(task) && task?.completed_at) return task.completed_at
  return latestDeliveryDate(task) || task?.updated_at || task?.created_at || null
}

function sortTasksByLatest(list) {
  return [...(list || [])].sort((left, right) => {
    const rightTime = dayjs(latestTaskTime(right)).valueOf() || 0
    const leftTime = dayjs(latestTaskTime(left)).valueOf() || 0
    return rightTime - leftTime || (right?.id || 0) - (left?.id || 0)
  })
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}

function formatTaskDate(value) {
  return value ? dayjs(value).format('MM-DD HH:mm') : '--'
}
</script>

<style scoped>
.member-identity {
  display: flex;
  align-items: center;
  gap: 10px;
}

.member-name-button {
  appearance: none;
  display: inline-flex;
  max-width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: #0f172a;
  font: inherit;
  font-weight: 700;
  line-height: 1.4;
  text-align: left;
  cursor: pointer;
}

.member-name-button:hover {
  color: #2563eb;
}

.member-color-dot {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.9);
}

.member-avatar-wrap {
  position: relative;
  display: inline-flex;
}

.member-online-dot {
  position: absolute;
  right: -4px;
  bottom: -4px;
  width: 9px;
  height: 9px;
  border: 2px solid #fff;
  border-radius: 999px;
  background: #cbd5e1;
}

.member-online-dot.online {
  background: #22c55e;
}

.member-presence {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.presence-online-text {
  color: #15803d;
  font-weight: 700;
}

.member-color-pill {
  display: inline-block;
  width: 46px;
  height: 16px;
  border-radius: 999px;
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.color-swatch {
  border: 2px solid transparent;
  border-radius: 14px;
  padding: 12px 8px;
  color: #0f172a;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.color-swatch.active {
  border-color: #0f172a;
}

.text-muted {
  color: #999;
  font-size: 12px;
}

.drawer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.drawer-summary-title {
  color: #0f172a;
  font-size: 14px;
  font-weight: 700;
}

.drawer-summary-meta {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}

.member-task-list-wrap {
  min-height: 220px;
}

.member-task-list {
  display: grid;
  gap: 12px;
}

.member-task-item {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-left-width: 4px;
  border-radius: 8px;
  background: #fff;
}

.member-task-item.completed {
  background: #f8fafc;
}

.member-task-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.member-task-title {
  min-width: 0;
  color: #0f172a;
  font-weight: 700;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.task-kind-tag {
  margin-left: 8px;
  vertical-align: 1px;
}

.status-tag {
  flex: 0 0 auto;
  min-width: 64px;
  justify-content: center;
}

.member-task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  color: #64748b;
  font-size: 12px;
}

.member-task-output {
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

@media (max-width: 640px) {
  .member-presence {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
    font-size: 12px;
  }

  .member-color-pill {
    width: 34px;
  }

  .color-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .drawer-toolbar,
  .member-task-header {
    align-items: stretch;
    flex-direction: column;
  }

  .status-tag {
    width: fit-content;
  }
}
</style>
