<template>
  <div class="login-page">
    <div class="login-shell">
      <section class="login-hero">
        <div>
          <div class="login-brand-lockup">
            <img class="login-logo" :src="logoXudong" alt="徐东摆地摊 logo" />
            <div>
              <div class="login-brand-name">徐东摆地摊</div>
              <div class="login-brand-subtitle">轻量协作工作台</div>
            </div>
          </div>
          <h1>把项目、任务和文档收进一个简洁的工作台。</h1>
          <p>项目像摊位一样摆清楚，任务按货架排好，文档统一放进箱子里。打开就知道今天该看哪里、该推进什么。</p>
          <div class="login-workbench-preview">
            <button type="button" class="preview-tile" @click="go('/projects')">
              <span class="preview-icon teal">
                <el-icon><FolderOpened /></el-icon>
              </span>
              <span>
                <strong>项目摊位</strong>
                <em>协作空间一眼看清</em>
              </span>
              <el-icon class="preview-arrow"><ArrowRight /></el-icon>
            </button>
            <button type="button" class="preview-tile" @click="go('/tasks')">
              <span class="preview-icon orange">
                <el-icon><List /></el-icon>
              </span>
              <span>
                <strong>任务货架</strong>
                <em>待办事项集中推进</em>
              </span>
              <el-icon class="preview-arrow"><ArrowRight /></el-icon>
            </button>
            <button type="button" class="preview-tile" @click="go('/documents')">
              <span class="preview-icon blue">
                <el-icon><Document /></el-icon>
              </span>
              <span>
                <strong>文档箱</strong>
                <em>资料和输出统一沉淀</em>
              </span>
              <el-icon class="preview-arrow"><ArrowRight /></el-icon>
            </button>
          </div>
          <div class="login-version-row">
            <span class="login-version-pill">{{ currentVersion }}</span>
            <button type="button" class="login-version-link" @click="goVersions">查看更新</button>
          </div>
        </div>
        <div class="muted">徐东摆地摊 {{ currentVersion }}</div>
      </section>

      <section class="login-panel">
        <div class="login-panel-header">
          <h2>登录工作台</h2>
          <p>继续处理项目、文档和待办协作。</p>
        </div>

        <el-tabs v-model="activeTab">
          <el-tab-pane label="登录" name="login">
            <el-form :model="loginForm" label-position="top" @submit.prevent="handleLogin">
              <el-form-item label="用户名">
                <el-input v-model="loginForm.username" placeholder="输入用户名" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="loginForm.password" type="password" show-password placeholder="输入密码" />
              </el-form-item>
              <el-button type="primary" :loading="loading" native-type="submit" class="login-submit" @click="handleLogin">
                登录
              </el-button>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="注册" name="register">
            <el-form :model="regForm" label-position="top" @submit.prevent="handleRegister">
              <el-form-item label="用户名">
                <el-input v-model="regForm.username" placeholder="设置用户名" />
              </el-form-item>
              <el-form-item label="显示名称">
                <el-input v-model="regForm.display_name" placeholder="显示给团队的名字" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="regForm.password" type="password" show-password placeholder="设置密码" />
              </el-form-item>
              <el-button type="primary" :loading="loading" native-type="submit" class="login-submit" @click="handleRegister">
                注册并开始
              </el-button>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </section>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Document, FolderOpened, List } from '@element-plus/icons-vue'
import logoXudong from '@/assets/logo-xudong.svg'
import { currentVersion } from '@/data/versionHistory'

const auth = useAuthStore()
const router = useRouter()
const activeTab = ref('login')
const loading = ref(false)
const loginForm = reactive({ username: '', password: '' })
const regForm = reactive({ username: '', display_name: '', password: '' })

async function handleLogin() {
  const username = loginForm.username.trim()
  if (!username || !loginForm.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(username, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch {
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  const username = regForm.username.trim()
  if (!username || !regForm.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.register({ ...regForm, username })
    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
    loginForm.username = username
    loginForm.password = ''
  } catch {
    ElMessage.error('注册失败')
  } finally {
    loading.value = false
  }
}

function goVersions() {
  router.push('/versions')
}

function go(path) {
  router.push(path)
}
</script>

<style scoped>
.login-brand-lockup {
  display: flex;
  align-items: center;
  gap: 14px;
}

.login-logo {
  width: 64px;
  height: 64px;
  display: block;
  filter: drop-shadow(0 14px 22px rgba(15, 23, 42, 0.16));
}

.login-brand-name {
  color: #0f172a;
  font-size: 28px;
  font-weight: 900;
  line-height: 1.1;
}

.login-brand-subtitle {
  margin-top: 5px;
  color: #0f766e;
  font-size: 13px;
  font-weight: 800;
}

.login-workbench-preview {
  margin-top: 26px;
  display: grid;
  gap: 10px;
  max-width: 520px;
}

.preview-tile {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  color: #0f172a;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
  transition: 0.2s ease;
}

.preview-tile:hover {
  transform: translateY(-2px);
  border-color: rgba(20, 184, 166, 0.3);
  background: #ffffff;
}

.preview-icon {
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  display: inline-grid;
  place-items: center;
  border-radius: 13px;
  font-size: 20px;
}

.preview-icon.teal {
  background: #ccfbf1;
  color: #0f766e;
}

.preview-icon.orange {
  background: #ffedd5;
  color: #c2410c;
}

.preview-icon.blue {
  background: #dbeafe;
  color: #1d4ed8;
}

.preview-tile span:nth-child(2) {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 4px;
}

.preview-tile strong {
  font-size: 15px;
}

.preview-tile em {
  color: #64748b;
  font-size: 12px;
  font-style: normal;
}

.preview-arrow {
  color: #94a3b8;
}

.login-version-row {
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.login-version-pill {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  border-radius: 999px;
  background: rgba(20, 184, 166, 0.14);
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
}

.login-version-link {
  border: none;
  background: transparent;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

.login-version-link:hover {
  color: #0f766e;
}

@media (max-width: 560px) {
  .login-brand-lockup {
    gap: 10px;
  }

  .login-brand-name {
    font-size: 23px;
  }

  .login-brand-subtitle {
    font-size: 12px;
  }

  .login-logo {
    width: 54px;
    height: 54px;
  }

  .login-workbench-preview {
    margin-top: 20px;
    gap: 8px;
  }

  .preview-tile {
    gap: 10px;
    padding: 11px;
    border-radius: 14px;
  }

  .preview-icon {
    width: 34px;
    height: 34px;
    flex-basis: 34px;
    border-radius: 12px;
    font-size: 18px;
  }

  .login-version-row {
    margin-top: 14px;
  }

  .login-panel-header h2 {
    font-size: 22px;
  }
}
</style>
