<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="title">徐东摆地摊团队协作系统</h1>
      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" @submit.prevent="handleLogin">
            <el-form-item label="用户名">
              <el-input v-model="loginForm.username" placeholder="输入用户名" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="loginForm.password" type="password" show-password placeholder="输入密码" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" native-type="submit" style="width:100%" @click="handleLogin">
                登录
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form :model="regForm" @submit.prevent="handleRegister" label-position="top">
            <el-form-item label="用户名">
              <el-input v-model="regForm.username" placeholder="设置用户名" />
            </el-form-item>
            <el-form-item label="显示名称">
              <el-input v-model="regForm.display_name" placeholder="你的显示名称" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="regForm.password" type="password" show-password placeholder="设置密码" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" native-type="submit" style="width:100%" @click="handleRegister">
                注册
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
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
  } catch (e) {
    ElMessage.error('登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  loading.value = true
  try {
    await auth.register(regForm)
    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
    loginForm.username = regForm.username
  } catch (e) {
    ElMessage.error('注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  width: 100vw; height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  background: white; padding: 40px; border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2); width: 400px;
}
.title { text-align: center; margin-bottom: 30px; color: #333; font-size: 20px; }
</style>