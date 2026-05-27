<template>
  <div class="login-page">
    <div class="login-shell">
      <section class="login-hero">
        <div>
          <div class="pill">徐东摆地摊</div>
          <h1>把项目、任务和文档收进一个简洁的工作台。</h1>
          <p>先把团队协作流程跑顺，再逐步细化任务与交付逻辑。现在这版界面会更轻、更统一，也更适合继续迭代。</p>
          <div class="hero-badges">
            <span class="hero-badge">项目概览</span>
            <span class="hero-badge">看板协作</span>
            <span class="hero-badge">文档沉淀</span>
          </div>
        </div>
        <div class="muted">徐东摆地摊 v1.0</div>
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

const auth = useAuthStore()
const router = useRouter()
const activeTab = ref('login')
const loading = ref(false)
const loginForm = reactive({ username: '', password: '' })
const regForm = reactive({ username: '', display_name: '', password: '' })

async function handleLogin() {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch {
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!regForm.username || !regForm.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.register(regForm)
    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
    loginForm.username = regForm.username
    loginForm.password = ''
  } catch {
    ElMessage.error('注册失败')
  } finally {
    loading.value = false
  }
}
</script>
