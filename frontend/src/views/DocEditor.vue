<template>
  <div class="doc-editor-page">
    <div class="logo">徐东摆地摊</div>
    <el-container>
      <el-aside class="sidebar">
        <div class="sidebar-footer">
          <div class="user-name">{{ auth.user?.display_name }}</div>
        </div>
        <router-link to="/dashboard" class="nav-item">总览</router-link>
        <router-link to="/projects" class="nav-item">项目</router-link>
        <router-link to="/documents" class="nav-item active">文档中心</router-link>
      </el-aside>
      <el-main class="main">
        <header class="header header-flex">
          <div class="header-left">
            <el-button size="small" @click="$router.push('/documents')">返回</el-button>
            <span class="doc-title">{{ doc?.title }}</span>
          </div>
          <div class="header-right">
            <span class="save-status" :class="saveStatusClass">{{ saveStatusText }}</span>
            <el-button size="small" @click="shareDoc">分享文档</el-button>
            <el-button size="small" type="primary" @click="saveDoc">保存</el-button>
          </div>
        </header>
        <div class="editor-toolbar">
          <el-button size="small" @click="execCmd('bold')" :type="activeMarks.includes('bold')?'primary':'default'"><b>B</b></el-button>
          <el-button size="small" @click="execCmd('italic')" :type="activeMarks.includes('italic')?'primary':'default'"><i>I</i></el-button>
          <el-button size="small" @click="execCmd('strike')" :type="activeMarks.includes('strike')?'primary':'default'"><s>S</s></el-button>
          <el-divider direction="vertical" />
          <el-button size="small" @click="execCmd('heading', 1)">H1</el-button>
          <el-button size="small" @click="execCmd('heading', 2)">H2</el-button>
          <el-button size="small" @click="execCmd('bulletList')">列表</el-button>
          <el-button size="small" @click="execCmd('orderedList')">编号</el-button>
          <el-button size="small" @click="execCmd('blockquote')">引用</el-button>
          <el-divider direction="vertical" />
          <el-button size="small" @click="setLink">链接</el-button>
          <el-button size="small" @click="showUpload = true">上传附件</el-button>
          <el-button size="small" @click="undo">撤销</el-button>
          <el-button size="small" @click="redo">重做</el-button>
        </div>
        <div class="editor-area">
          <div v-if="loading" style="text-align:center;padding:40px">加载中...</div>
          <div v-else ref="editorRef" class="tiptap-editor"></div>
        </div>

        <!-- 附件列表 -->
        <div v-if="attachments.length" class="attachment-list">
          <h4>附件</h4>
          <div v-for="att in attachments" :key="att.id" class="attachment-item">
            <span class="att-name">{{ att.original_name || att.filename }}</span>
            <el-button size="small" type="danger" @click="delAttachment(att.id)">删除</el-button>
          </div>
        </div>

        <el-dialog v-model="showUpload" title="上传附件" width="400px">
          <el-upload drag :auto-upload="false" :limit="5" ref="uploadRef" multiple>
            <el-button type="primary">选择文件</el-button>
          </el-upload>
          <el-button type="primary" :loading="uploading" @click="doUpload" style="margin-top:15px;width:100%">上传</el-button>
        </el-dialog>

        <el-dialog v-model="shareDialog" title="分享文档" width="400px">
          <div v-if="shareLink">
            <p>分享链接已生成：</p>
            <el-input v-model="shareLink" readonly style="margin-top:10px" />
            <el-button type="primary" size="small" @click="copyLink" style="margin-top:10px">复制链接</el-button>
          </div>
          <div v-else>
            <el-form-item label="访问权限">
              <el-select v-model="sharePerm" style="width:100%">
                <el-option label="仅查看" value="readonly" />
                <el-option label="可编辑" value="write" />
              </el-select>
            </el-form-item>
            <el-button type="primary" :loading="genLoading" @click="genShare" style="width:100%">生成分享链接</el-button>
          </div>
        </el-dialog>

        <el-dialog v-model="linkDialog" title="插入链接" width="350px">
          <el-form-item label="链接地址">
            <el-input v-model="linkUrl" placeholder="输入链接地址" />
          </el-form-item>
          <el-button type="primary" @click="insertLink" style="width:100%">确定</el-button>
        </el-dialog>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Editor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import api from '@/api'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const auth = useAuthStore()
const loading = ref(true)
const doc = ref(null)
const editorRef = ref(null)
const editor = ref(null)
const activeMarks = ref([])
const attachments = ref([])
const showUpload = ref(false)
const uploadRef = ref(null)
const uploading = ref(false)

// 保存状态
const saveStatus = ref('saved') // 'saved' | 'saving' | 'unsaved'
const saveStatusText = ref('已保存')
const saveStatusClass = ref('status-saved')

let autoSaveTimer = null
const AUTO_SAVE_DELAY = 3000 // 3秒无操作自动保存

const shareDialog = ref(false)
const shareLink = ref('')
const sharePerm = ref('readonly')
const genLoading = ref(false)

const linkDialog = ref(false)
const linkUrl = ref('')

onMounted(async () => {
  await auth.getMe()
  const id = route.params.id
  if (!id) { loading.value = false; return }
  try {
    doc.value = await api.get(`/documents/${id}`)
    attachments.value = await api.get(`/documents/${id}/attachments`) || []
  } catch (e) {
    console.error(e)
  }
  initEditor()
  loading.value = false
})

function initEditor() {
  editor.value = new Editor({
    element: editorRef.value,
    extensions: [
      StarterKit,
      Link.configure({ openOnClick: false }),
      Image,
    ],
    content: doc.value?.content || '',
    onUpdate: ({ editor: e }) => {
      triggerAutoSave()
    },
    onSelectionUpdate: ({ editor: e }) => {
      updateActiveMarks()
    }
  })
}

function updateActiveMarks() {
  const marks = []
  if (!editor.value) return
  editor.value.chain().command(({ commands }) => {
    // 通过检测 active 状态获取当前 marks
    return true
  }).run()
  // 更简单的方式：直接从 editor state 读取
  const { selection } = editor.value.state
  activeMarks.value = selection.$from.marks().map(m => m.type.name)
}

function triggerAutoSave() {
  saveStatus.value = 'unsaved'
  saveStatusText.value = '未保存'
  saveStatusClass.value = 'status-unsaved'

  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    autoSave()
  }, AUTO_SAVE_DELAY)
}

async function autoSave() {
  if (!doc.value || !editor.value) return
  saveStatus.value = 'saving'
  saveStatusText.value = '保存中...'
  saveStatusClass.value = 'status-saving'

  const content = editor.value.getHTML()
  try {
    await api.put(`/documents/${doc.value.id}`, { content })
    saveStatus.value = 'saved'
    saveStatusText.value = '已保存 ' + dayjs().format('HH:mm:ss')
    saveStatusClass.value = 'status-saved'
  } catch (e) {
    console.error(e)
    saveStatus.value = 'unsaved'
    saveStatusText.value = '保存失败'
    saveStatusClass.value = 'status-unsaved'
  }
}

onBeforeUnmount(() => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  editor.value?.destroy()
})

function execCmd(command, value) {
  if (!editor.value) return
  if (command === 'bold') editor.value.chain().focus().toggleBold().run()
  else if (command === 'italic') editor.value.chain().focus().toggleItalic().run()
  else if (command === 'strike') editor.value.chain().focus().toggleStrike().run()
  else if (command === 'heading') editor.value.chain().focus().toggleHeading({ level: value }).run()
  else if (command === 'bulletList') editor.value.chain().focus().toggleBulletList().run()
  else if (command === 'orderedList') editor.value.chain().focus().toggleOrderedList().run()
  else if (command === 'blockquote') editor.value.chain().focus().toggleBlockquote().run()
}

function setLink() {
  linkDialog.value = true
  linkUrl.value = ''
}

function insertLink() {
  if (!linkUrl.value) return
  editor.value?.chain().focus().setLink({ href: linkUrl.value }).run()
  linkDialog.value = false
}

function undo() { editor.value?.chain().focus().undo().run() }
function redo() { editor.value?.chain().focus().redo().run() }

async function saveDoc() {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  await autoSave()
}

async function doUpload() {
  if (!doc.value) return
  uploading.value = true
  try {
    const files = uploadRef.value?.uploadFiles || []
    for (const f of files) {
      const formData = new FormData()
      formData.append('file', f.raw)
      await api.post(`/documents/${doc.value.id}/attachments`, formData)
    }
    ElMessage.success('上传成功')
    attachments.value = await api.get(`/documents/${doc.value.id}/attachments`) || []
    showUpload.value = false
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

async function delAttachment(id) {
  try {
    await api.delete(`/documents/${doc.value.id}/attachments/${id}`)
    attachments.value = attachments.value.filter(a => a.id !== id)
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function shareDoc() {
  shareLink.value = doc.value?.share_token ? `${location.origin}/share/${doc.value.share_token}` : ''
  shareDialog.value = true
}

async function genShare() {
  genLoading.value = true
  try {
    const res = await api.post(`/documents/${doc.value.id}/share?mode=${sharePerm.value}&expire_hours=72`)
    shareLink.value = `${location.origin}/share/${res.share_token}`
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
.doc-editor-page { display: flex; height: 100vh; background: #f5f5f5; }
.logo { position: fixed; top: 0; left: 0; width: 200px; height: 60px; background: #545c64; color: white; display: flex; align-items: center; padding: 0 20px; font-size: 14px; font-weight: bold; z-index: 10; }
.sidebar { width: 200px; background: #fff; border-right: 1px solid #eee; padding-top: 60px; }
.sidebar-footer { padding: 10px; border-bottom: 1px solid #eee; }
.user-name { font-weight: bold; }
.nav-item { display: block; padding: 12px 20px; color: #333; text-decoration: none; border-bottom: 1px solid #f0f0f0; }
.nav-item.active { background: #ecf5ff; color: #409eff; }
.main { margin-left: 200px; display: flex; flex-direction: column; }
.header { padding: 12px 20px; background: white; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
.header-flex { justify-content: space-between; }
.header-left { display: flex; align-items: center; gap: 12px; }
.header-right { display: flex; gap: 10px; align-items: center; }
.doc-title { font-weight: bold; font-size: 16px; }
.save-status { font-size: 12px; padding: 2px 8px; border-radius: 4px; }
.status-saved { color: #67c23a; background: #f0f9eb; }
.status-saving { color: #e6a23c; background: #fdf6ec; }
.status-unsaved { color: #909399; background: #f4f4f5; }
.editor-toolbar { padding: 8px 20px; background: #fafafa; border-bottom: 1px solid #eee; display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
.editor-area { flex: 1; overflow-y: auto; padding: 20px; background: white; }
.tiptap-editor { min-height: 400px; outline: none; }
.tiptap-editor :deep(.ProseMirror) { min-height: 400px; padding: 20px; outline: none; }
.tiptap-editor :deep(.ProseMirror p) { margin: 0.5em 0; }
.tiptap-editor :deep(h1) { font-size: 24px; font-weight: bold; margin: 1em 0 0.5em; }
.tiptap-editor :deep(h2) { font-size: 20px; font-weight: bold; margin: 1em 0 0.5em; }
.tiptap-editor :deep(ul), .tiptap-editor :deep(ol) { padding-left: 1.5em; }
.tiptap-editor :deep(blockquote) { border-left: 3px solid #ddd; padding-left: 1em; color: #666; }
.tiptap-editor :deep(a) { color: #409eff; }
.attachment-list { padding: 15px 20px; background: #fafafa; border-top: 1px solid #eee; }
.attachment-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee; }
.att-name { font-size: 14px; }
</style>