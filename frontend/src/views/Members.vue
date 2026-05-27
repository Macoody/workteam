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
              <span class="member-color-dot" :style="{ background: row.color || '#93c5fd' }"></span>
              <div>
                <div class="item-title">{{ row.display_name || row.username }}</div>
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
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="最后使用" width="180">
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
import { onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'
import { USER_COLOR_OPTIONS } from '@/utils/userColors'

const auth = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const editingUserId = ref(null)
const members = ref([])
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
  await loadMembers()
})

async function loadMembers() {
  loading.value = true
  try {
    members.value = await api.get('/auth/users')
  } catch (error) {
    console.error(error)
    ElMessage.error('成员列表加载失败')
  } finally {
    loading.value = false
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
    await ElMessageBox.confirm(`确定删除成员“${user.display_name || user.username}”吗？`, '删除成员', {
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

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}
</script>

<style scoped>
.member-identity {
  display: flex;
  align-items: center;
  gap: 10px;
}

.member-color-dot {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.9);
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
</style>
