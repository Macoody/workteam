<template>
  <AppShell title="文档中心" description="把过程资料和输出文档集中沉淀，方便项目协作和后续复用。">
    <template #actions>
      <el-button type="primary" @click="showCreate = true">新建文档</el-button>
      <el-button @click="loadDocs">刷新</el-button>
    </template>

    <div v-if="docs.length === 0" class="empty-card">还没有文档，先创建一篇项目记录或说明文档。</div>
    <div v-else class="doc-grid">
      <div v-for="doc in docs" :key="doc.id" class="doc-card" @click="$router.push(`/documents/${doc.id}`)">
        <div style="display: flex; justify-content: space-between; gap: 12px; align-items: flex-start">
          <div class="pill">{{ docTypeLabel(doc.doc_type) }}</div>
          <el-tag v-if="doc.is_public" type="success" effect="light">已分享</el-tag>
        </div>
        <div style="margin-top: 18px" class="item-title">{{ doc.title }}</div>
        <div class="item-meta">最后编辑 {{ documentEditorName(doc) }} · {{ formatDate(documentEditedAt(doc)) }}</div>
        <div class="item-meta">创建于 {{ formatDate(doc.created_at) }}</div>
        <div style="margin-top: 18px; display: flex; justify-content: space-between; align-items: center">
          <span class="muted">{{ doc.view_count || 0 }} 次浏览</span>
          <div class="doc-card-actions">
            <el-button size="small" @click.stop="openRename(doc)">改名</el-button>
            <el-button size="small" @click.stop="shareDoc(doc)">分享</el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreate" title="新建文档" width="420px">
      <el-form :model="form" label-position="top" @submit.prevent="handleCreate">
        <el-form-item label="文档标题">
          <el-input v-model="form.title" placeholder="输入文档标题" />
        </el-form-item>
        <el-form-item label="文档类型">
          <el-select v-model="form.doc_type" style="width: 100%">
            <el-option label="文档" value="doc" />
            <el-option label="表格" value="sheet" />
            <el-option label="演示" value="ppt" />
            <el-option label="其他" value="file" />
          </el-select>
        </el-form-item>
        <el-button type="primary" :loading="loading" native-type="submit" style="width: 100%">
          创建文档
        </el-button>
      </el-form>
    </el-dialog>

    <el-dialog v-model="renameDialog" title="修改标题" width="420px">
      <el-form :model="renameForm" label-position="top" @submit.prevent="saveRename">
        <el-form-item label="文档标题">
          <el-input v-model="renameForm.title" placeholder="输入新的文档标题" @keyup.enter="saveRename" />
        </el-form-item>
        <el-button type="primary" :loading="renameLoading" native-type="submit" style="width: 100%">
          保存标题
        </el-button>
      </el-form>
    </el-dialog>

    <el-dialog v-model="shareDialog" title="分享文档" width="420px">
      <div v-if="shareLink">
        <div class="muted">分享链接已生成</div>
        <el-input v-model="shareLink" readonly style="margin-top: 10px" />
        <el-button type="primary" size="small" style="margin-top: 12px" @click="copyLink">复制链接</el-button>
      </div>
      <div v-else>
        <div class="muted" style="margin-bottom: 10px">设置访问权限后生成链接</div>
        <el-select v-model="sharePerm" style="width: 100%">
          <el-option label="仅查看" value="readonly" />
          <el-option label="可编辑" value="write" />
        </el-select>
        <el-button type="primary" :loading="genLoading" style="margin-top: 14px; width: 100%" @click="genShare">
          生成分享链接
        </el-button>
      </div>
    </el-dialog>
  </AppShell>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'

const auth = useAuthStore()
const docs = ref([])
const showCreate = ref(false)
const loading = ref(false)
const form = reactive({ title: '', doc_type: 'doc', content: '' })
const renameDialog = ref(false)
const renameLoading = ref(false)
const renameForm = reactive({ id: null, title: '' })

const shareDialog = ref(false)
const shareLink = ref('')
const shareDocId = ref(null)
const sharePerm = ref('readonly')
const genLoading = ref(false)

onMounted(async () => {
  await auth.getMe()
  await loadDocs()
})

async function loadDocs() {
  docs.value = await api.get('/documents')
}

async function handleCreate() {
  const title = form.title.trim()
  if (!title) {
    ElMessage.warning('请输入标题')
    return
  }
  loading.value = true
  try {
    await api.post('/documents', { ...form, title })
    ElMessage.success('创建成功')
    showCreate.value = false
    form.title = ''
    form.doc_type = 'doc'
    await loadDocs()
  } catch {
    ElMessage.error('创建失败')
  } finally {
    loading.value = false
  }
}

function openRename(doc) {
  renameForm.id = doc.id
  renameForm.title = doc.title || ''
  renameDialog.value = true
}

async function saveRename() {
  const title = renameForm.title.trim()
  if (!title) {
    ElMessage.warning('请输入标题')
    return
  }
  renameLoading.value = true
  try {
    await api.put(`/documents/${renameForm.id}`, { title })
    ElMessage.success('标题已保存')
    renameDialog.value = false
    await loadDocs()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    renameLoading.value = false
  }
}

function shareDoc(doc) {
  shareDocId.value = doc.id
  shareLink.value = doc.share_token ? `${window.location.origin}/api/documents/shared/${doc.share_token}` : ''
  sharePerm.value = doc.share_mode || 'readonly'
  shareDialog.value = true
}

async function genShare() {
  genLoading.value = true
  try {
    const res = await api.post(`/documents/${shareDocId.value}/share?mode=${sharePerm.value}&expire_hours=72`)
    shareLink.value = `${window.location.origin}${res.share_url}`
  } catch {
    ElMessage.error('生成失败')
  } finally {
    genLoading.value = false
  }
}

function copyLink() {
  navigator.clipboard.writeText(shareLink.value)
  ElMessage.success('已复制')
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

function formatDate(value) {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
}
</script>

<style scoped>
.doc-card-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.doc-card-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}
</style>
