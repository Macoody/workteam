<template>
  <AppShell :title="doc?.title || '文档编辑'">
    <template #actions>
      <span class="pill">{{ saveStatusText }}</span>
      <el-button @click="$router.push('/documents')">返回列表</el-button>
      <el-button v-if="doc?.creator_id === auth.user?.id || auth.user?.role === 'admin'" type="danger" @click="deleteDoc">删除</el-button>
      <el-button @click="shareDoc">分享</el-button>
    </template>

    <div class="editor-shell">
      <div class="editor-toolbar">
        <el-button size="small" @click="execCmd('bold')" :type="isActive('bold') ? 'primary' : 'default'"><b>B</b></el-button>
        <el-button size="small" @click="execCmd('italic')" :type="isActive('italic') ? 'primary' : 'default'"><i>I</i></el-button>
        <el-button size="small" @click="execCmd('strike')" :type="isActive('strike') ? 'primary' : 'default'"><s>S</s></el-button>
        <el-divider direction="vertical" />
        <el-button size="small" @click="execCmd('heading', 1)" :type="isActive('heading', { level: 1 }) ? 'primary' : 'default'">H1</el-button>
        <el-button size="small" @click="execCmd('heading', 2)" :type="isActive('heading', { level: 2 }) ? 'primary' : 'default'">H2</el-button>
        <el-button size="small" @click="execCmd('bulletList')" :type="isActive('bulletList') ? 'primary' : 'default'">列表</el-button>
        <el-button size="small" @click="execCmd('orderedList')" :type="isActive('orderedList') ? 'primary' : 'default'">编号</el-button>
        <el-button size="small" @click="execCmd('blockquote')" :type="isActive('blockquote') ? 'primary' : 'default'">引用</el-button>
        <el-divider direction="vertical" />
        <el-button size="small" @click="setLink">链接</el-button>
        <el-button size="small" @click="undo">撤销</el-button>
        <el-button size="small" @click="redo">重做</el-button>
      </div>

      <div class="editor-area">
        <div v-if="loading" class="empty-card">加载中...</div>
        <EditorContent v-else-if="editor" :editor="editor" class="tiptap-editor" />
        <div v-else class="empty-card">编辑器初始化失败</div>
      </div>
    </div>

    <el-dialog v-model="shareDialog" title="分享文档" width="420px">
      <div v-if="shareLink">
        <div class="muted">分享链接已生成</div>
        <el-input v-model="shareLink" readonly style="margin-top: 10px" />
        <el-button type="primary" size="small" style="margin-top: 12px" @click="copyLink">复制链接</el-button>
      </div>
      <div v-else>
        <el-form-item label="访问权限">
          <el-select v-model="sharePerm" style="width: 100%">
            <el-option label="仅查看" value="readonly" />
            <el-option label="可编辑" value="write" />
          </el-select>
        </el-form-item>
        <el-button type="primary" :loading="genLoading" style="width: 100%" @click="genShare">生成分享链接</el-button>
      </div>
    </el-dialog>

    <el-dialog v-model="linkDialog" title="插入链接" width="360px">
      <el-form-item label="链接地址">
        <el-input v-model="linkUrl" placeholder="输入链接地址" />
      </el-form-item>
      <el-button type="primary" style="width: 100%" @click="insertLink">确定</el-button>
    </el-dialog>
  </AppShell>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import Highlight from '@tiptap/extension-highlight'
import { ElMessage } from 'element-plus'
import AppShell from '@/components/AppShell.vue'
import api from '@/api'

const AUTO_SAVE_DELAY = 1500

const route = useRoute()
const auth = useAuthStore()
const loading = ref(true)
const doc = ref(null)
const editor = ref(null)
const saveStatusText = ref('已保存')
let autoSaveTimer = null

const shareDialog = ref(false)
const shareLink = ref('')
const sharePerm = ref('readonly')
const genLoading = ref(false)

const linkDialog = ref(false)
const linkUrl = ref('')

onMounted(async () => {
  const id = route.params.id
  if (!id) {
    loading.value = false
    return
  }

  try {
    const [me, currentDoc] = await Promise.all([
      auth.getMe(),
      api.get(`/documents/${id}`),
    ])
    doc.value = currentDoc
    initEditor(doc.value?.content || '')
  } catch (error) {
    console.error(error)
    saveStatusText.value = '加载失败'
  } finally {
    loading.value = false
  }
})

function initEditor(content) {
  editor.value = new Editor({
    extensions: [
      StarterKit,
      Link.configure({ openOnClick: false }),
      Image,
      Highlight.configure({ multicolor: true })
    ],
    content,
    editorProps: {
      attributes: {
        class: 'editor-prosemirror'
      }
    },
    onUpdate: () => {
      triggerAutoSave()
    }
  })
}

function triggerAutoSave() {
  saveStatusText.value = '未保存'
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    autoSave()
  }, AUTO_SAVE_DELAY)
}

async function autoSave() {
  if (!doc.value || !editor.value) return
  saveStatusText.value = '保存中...'

  try {
    const updated = await api.put(`/documents/${doc.value.id}`, {
      content: editor.value.getHTML()
    })
    doc.value = updated
    saveStatusText.value = `已自动保存 ${dayjs().format('HH:mm:ss')}`
  } catch (error) {
    console.error(error)
    saveStatusText.value = '保存失败'
    ElMessage.error(error?.response?.data?.detail || '文档自动保存失败')
  }
}

onBeforeUnmount(async () => {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
    await autoSave()
  }
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

function isActive(name, attrs) {
  return editor.value?.isActive(name, attrs) || false
}

function setLink() {
  linkUrl.value = editor.value?.getAttributes('link')?.href || ''
  linkDialog.value = true
}

function insertLink() {
  if (!editor.value) return
  if (!linkUrl.value) {
    editor.value.chain().focus().unsetLink().run()
  } else {
    editor.value.chain().focus().extendMarkRange('link').setLink({ href: linkUrl.value }).run()
  }
  linkDialog.value = false
}

function undo() {
  editor.value?.chain().focus().undo().run()
}

function redo() {
  editor.value?.chain().focus().redo().run()
}

function shareDoc() {
  shareLink.value = doc.value?.share_token ? `${location.origin}/api/documents/shared/${doc.value.share_token}` : ''
  shareDialog.value = true
}

async function genShare() {
  genLoading.value = true
  try {
    const res = await api.post(`/documents/${doc.value.id}/share?mode=${sharePerm.value}&expire_hours=72`)
    shareLink.value = `${location.origin}${res.share_url}`
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

async function deleteDoc() {
  try {
    await api.delete(`/documents/${doc.value.id}`)
    ElMessage.success('文档已删除')
    router.push('/documents')
  } catch {
    ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.editor-owner {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border: none;
  border-radius: 999px;
  color: #0f172a;
  font-size: 12px;
  font-weight: 600;
}

.tiptap-editor :deep(.editor-prosemirror) {
  min-height: 520px;
  padding: 24px;
  outline: none;
  cursor: text;
}

.tiptap-editor :deep(.editor-prosemirror p) {
  margin: 0.7em 0;
}

.tiptap-editor :deep(.editor-prosemirror h1) {
  font-size: 28px;
  margin: 1em 0 0.45em;
}

.tiptap-editor :deep(.editor-prosemirror h2) {
  font-size: 22px;
  margin: 1em 0 0.45em;
}

.tiptap-editor :deep(.editor-prosemirror ul),
.tiptap-editor :deep(.editor-prosemirror ol) {
  padding-left: 1.4em;
}

.tiptap-editor :deep(.editor-prosemirror blockquote) {
  border-left: 3px solid rgba(37, 99, 235, 0.35);
  margin: 1em 0;
  padding-left: 1em;
  color: #475569;
}

.tiptap-editor :deep(mark) {
  border-radius: 0.35em;
  padding: 0.08em 0.2em;
}
</style>
