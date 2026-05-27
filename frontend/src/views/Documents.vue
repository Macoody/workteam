<template>
  <div class="docs-page">
    <div class="header">
      <span>文档中心</span>
      <div class="header-actions">
        <el-button type="primary" size="small" @click="showCreate = true">新建文档</el-button>
        <el-button size="small" @click="loadDocs">刷新</el-button>
      </div>
    </div>
    <div class="section">
      <div v-if="docs.length === 0" class="el-empty">暂无文档</div>
      <div v-else class="doc-grid">
        <div v-for="d in docs" :key="d.id" class="doc-card" @click="$router.push(`/documents/${d.id}`)">
          <div class="doc-icon">📄</div>
          <div class="doc-info">
            <div class="doc-title">{{ d.title }}</div>
            <div class="doc-meta">{{ d.created_at?.slice(0, 10) }} · {{ d.file_type || '文档' }}</div>
          </div>
          <div class="doc-actions">
            <el-tag v-if="d.share_token" type="success" size="small">已分享</el-tag>
            <el-button size="small" @click.stop="shareDoc(d)">分享</el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreate" title="新建文档" width="400px">
      <el-form :model="form" label-position="top" @submit.prevent="handleCreate">
        <el-form-item label="文档标题">
          <el-input v-model="form.title" placeholder="输入文档标题" />
        </el-form-item>
        <el-form-item label="文档类型">
          <el-select v-model="form.type" style="width:100%">
            <el-option label="Word" value="doc" />
            <el-option label="Excel" value="sheet" />
            <el-option label="PPT" value="ppt" />
            <el-option label="其他" value="file" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-upload :auto-upload="false" :limit="1" ref="uploadRef">
            <el-button type="primary">上传文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" native-type="submit" style="width:100%" @click="handleCreate">创建</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>

    <el-dialog v-model="shareDialog" title="分享文档" width="400px">
      <div v-if="shareLink" class="share-result">
        <p>分享链接已生成：</p>
        <el-input v-model="shareLink" readonly />
        <el-button type="primary" size="small" @click="copyLink" style="margin-top:10px">复制链接</el-button>
      </div>
      <div v-else>
        <p>访问权限：</p>
        <el-select v-model="sharePerm" style="width:100%">
          <el-option label="仅查看" value="read" />
          <el-option label="可编辑" value="write" />
        </el-select>
        <el-button type="primary" :loading="genLoading" @click="genShare" style="margin-top:15px;width:100%">生成分享链接</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'
import { ElMessage } from 'element-plus'

const auth = useAuthStore()
const docs = ref([])
const showCreate = ref(false)
const loading = ref(false)
const form = reactive({ title: '', type: 'doc' })

const shareDialog = ref(false)
const shareLink = ref('')
const shareDocId = ref(null)
const sharePerm = ref('read')
const genLoading = ref(false)

onMounted(async () => {
  await auth.getMe()
  loadDocs()
})

async function loadDocs() {
  docs.value = await api.get('/documents')
}

async function handleCreate() {
  if (!form.title) { ElMessage.warning('请输入标题'); return }
  loading.value = true
  try {
    await api.post('/documents', form)
    ElMessage.success('创建成功')
    showCreate.value = false
    loadDocs()
  } catch (e) {
    ElMessage.error('创建失败')
  } finally {
    loading.value = false
  }
}

async function shareDoc(doc) {
  shareDocId.value = doc.id
  shareLink.value = doc.share_token ? `${window.location.origin}/share/${doc.share_token}` : ''
  sharePerm.value = 'read'
  shareDialog.value = true
}

async function genShare() {
  genLoading.value = true
  try {
    const res = await api.post(`/documents/${shareDocId.value}/share`, { permission: sharePerm.value })
    shareLink.value = `${window.location.origin}/share/${res.token}`
  } catch (e) {
    ElMessage.error('生成失败')
  } finally {
    genLoading.value = false
  }
}

function copyLink() {
  navigator.clipboard.writeText(shareLink.value)
  ElMessage.success('已复制')
}
</script>

<style scoped>
.docs-page { padding: 0; }
.header { padding: 15px 20px; background: white; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.header-actions { display: flex; gap: 10px; }
.section { padding: 20px; }
.doc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.doc-card { background: white; border-radius: 8px; padding: 16px; display: flex; align-items: center; gap: 12px; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.doc-card:hover { transform: translateY(-2px); }
.doc-icon { font-size: 32px; }
.doc-info { flex: 1; }
.doc-title { font-weight: bold; font-size: 15px; margin-bottom: 4px; }
.doc-meta { font-size: 12px; color: #999; }
.doc-actions { display: flex; align-items: center; gap: 8px; }
</style>