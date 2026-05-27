<template>
  <AppShell title="工作日志" description="每天结束前记录当天的工作内容和进展，便于回顾和协作同步。">
    <template #actions>
      <el-date-picker
        v-model="filterDate"
        type="date"
        placeholder="筛选日期"
        style="width: 160px"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        @change="loadLogs"
      />
      <el-button @click="loadLogs">刷新</el-button>
    </template>

    <div class="log-shell">
      <!-- 写日志 -->
      <section class="log-compose panel">
        <div class="compose-header">
          <div class="compose-date">
            <span class="compose-label">今日工作日志</span>
            <span class="compose-day">{{ todayLabel }}</span>
          </div>
          <el-button v-if="myTodayLog" size="small" @click="startEdit(myTodayLog)">编辑</el-button>
        </div>

        <div class="compose-body">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            placeholder="今天做了什么？遇到了什么问题？明天的计划是什么？"
            :autosize="{ minRows: 4, maxRows: 12 }"
          />
          <div class="compose-footer">
            <span class="compose-hint">同一天可多次提交，自动覆盖</span>
            <el-button type="primary" :loading="saving" @click="submitLog">
              {{ myTodayLog ? '更新日志' : '提交日志' }}
            </el-button>
          </div>
          <!-- 成员筛选 -->
          <div v-if="members.length" class="member-filter">
            <button
              type="button"
              class="member-chip"
              :class="{ active: selectedUserId === null }"
              @click="selectedUserId = null"
            >全部</button>
            <button
              v-for="member in members"
              :key="member.id"
              type="button"
              class="member-chip"
              :class="{ active: selectedUserId === member.id }"
              :style="{ background: selectedUserId === member.id ? member.color : (member.color + '33') }"
              @click="selectedUserId = selectedUserId === member.id ? null : member.id"
            >{{ member.display_name || member.username }}</button>
          </div>
        </div>
      </section>

      <!-- 历史日志列表 -->
      <section class="log-history">
        <div v-if="loading && filteredLogs.length === 0" class="empty-card">加载中...</div>
        <div v-else-if="filteredLogs.length === 0" class="empty-card">还没有日志，开始写第一条吧。</div>
        <div v-else class="log-list">
          <div v-for="log in filteredLogs" :key="log.id" class="log-card">
            <div class="log-card-header">
              <div class="log-meta">
                <span class="log-author">
                  <span class="log-dot" :style="{ background: log.user?.color || '#93c5fd' }"></span>
                  {{ log.user?.display_name || log.user?.username || `成员 #${log.user_id}` }}
                </span>
                <span class="log-date">{{ formatDate(log.log_date) }}</span>
              </div>
              <div class="log-actions" v-if="log.user_id === auth.user?.id">
                <el-button size="small" @click="startEdit(log)">编辑</el-button>
                <el-button size="small" type="danger" plain @click="deleteLog(log)">删除</el-button>
              </div>
            </div>
            <div class="log-content">{{ log.content }}</div>
          </div>
        </div>
      </section>
    </div>

    <!-- 编辑 Dialog -->
    <el-dialog v-model="editDialog" title="编辑日志" width="600px">
      <el-input
        v-model="editForm.content"
        type="textarea"
        :rows="6"
        :autosize="{ minRows: 4, maxRows: 12 }"
      />
      <el-button type="primary" :loading="saving" style="width: 100%; margin-top: 16px" @click="saveEdit">
        保存修改
      </el-button>
    </el-dialog>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'

const auth = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const logs = ref([])
const members = ref([])
const selectedUserId = ref(null)
const filterDate = ref(dayjs().format('YYYY-MM-DD'))
const editDialog = ref(false)
const editingLog = ref(null)

const form = reactive({ content: '' })
const editForm = reactive({ content: '' })

const todayLabel = computed(() => dayjs().format('YYYY-MM-DD'))

const myTodayLog = computed(() => {
  return logs.value.find(
    log => log.user_id === auth.user?.id && log.log_date && dayjs(log.log_date).format('YYYY-MM-DD') === todayLabel.value
  )
})

const filteredLogs = computed(() => {
  if (!selectedUserId.value) return logs.value
  return logs.value.filter(log => log.user_id === selectedUserId.value)
})

onMounted(async () => {
  await auth.getMe()
  await loadLogs()
  await loadMembers()
})

async function loadLogs() {
  loading.value = true
  try {
    const params = filterDate.value ? `?date_str=${filterDate.value}` : ''
    logs.value = await api.get(`/worklogs${params}`)
    if (myTodayLog.value) {
      form.content = myTodayLog.value.content
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('日志加载失败')
  } finally {
    loading.value = false
  }
}

async function loadMembers() {
  try {
    members.value = await api.get('/auth/users')
  } catch (error) {
    console.error(error)
  }
}

async function submitLog() {
  if (!form.content.trim()) {
    ElMessage.warning('日志内容不能为空')
    return
  }
  saving.value = true
  try {
    const payload = {
      log_date: dayjs().format('YYYY-MM-DDTHH:mm:ss'),
      content: form.content.trim()
    }
    await api.post('/worklogs', payload)
    ElMessage.success('日志已保存')
    await loadLogs()
  } catch (error) {
    const detail = error?.response?.data?.detail
    ElMessage.error(detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function startEdit(log) {
  editingLog.value = log
  editForm.content = log.content
  editDialog.value = true
}

async function saveEdit() {
  if (!editForm.content.trim()) {
    ElMessage.warning('日志内容不能为空')
    return
  }
  saving.value = true
  try {
    await api.put(`/worklogs/${editingLog.value.id}`, {
      content: editForm.content.trim()
    })
    ElMessage.success('日志已更新')
    editDialog.value = false
    await loadLogs()
  } catch (error) {
    const detail = error?.response?.data?.detail
    ElMessage.error(detail || '更新失败')
  } finally {
    saving.value = false
  }
}

async function deleteLog(log) {
  try {
    await ElMessageBox.confirm('确定删除这条日志吗？', '删除日志', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await api.delete(`/worklogs/${log.id}`)
    ElMessage.success('日志已删除')
    await loadLogs()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    const detail = error?.response?.data?.detail
    ElMessage.error(detail || '删除失败')
  }
}

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}
</script>

<style scoped>
.log-shell {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.log-compose {
  padding: 20px 24px;
}

.compose-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.compose-date {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.compose-label {
  font-size: 13px;
  color: var(--wt-muted);
}

.compose-day {
  font-size: 18px;
  font-weight: 600;
}

.compose-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.compose-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.compose-hint {
  font-size: 12px;
  color: var(--wt-muted);
}

.log-history {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-card {
  background: var(--wt-surface-strong, #fff);
  border: 1px solid var(--wt-border);
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.log-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.log-author {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
}

.log-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  flex-shrink: 0;
}

.log-date {
  font-size: 13px;
  color: var(--wt-muted);
}

.log-actions {
  display: flex;
  gap: 6px;
}

.log-content {
  font-size: 14px;
  line-height: 1.7;
  color: var(--wt-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.member-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.member-chip {
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  color: #0f172a;
}
</style>