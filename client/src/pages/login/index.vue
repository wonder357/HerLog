<template>
  <view class="page">
    <view class="brand">
      <view class="name">她记</view>
      <view class="sub">女性健康记录助手</view>
    </view>

    <view class="form">
      <input v-model="username" class="field" placeholder="用户名" maxlength="32" />
      <input v-model="password" class="field" password placeholder="密码（至少 8 位）" maxlength="72" />
      <text v-if="fieldError" class="error">{{ fieldError }}</text>
      <text v-if="formError" class="error">{{ formError }}</text>
      <button class="primary" :disabled="submitting" @tap="submit">
        {{ submitting ? '请稍候…' : mode === 'login' ? '登录' : '注册' }}
      </button>
      <view class="switch" @tap="switchMode">
        {{ mode === 'login' ? '还没有账号？注册' : '已有账号？去登录' }}
      </view>
      <view class="hint">比赛版使用模拟账号：用户名 + 密码，不需要手机号。</view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { ApiRequestError } from '../../services/httpClient'

const auth = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const fieldError = ref('')
const formError = ref('')
const submitting = ref(false)

function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  fieldError.value = ''
  formError.value = ''
}

function validate(): boolean {
  fieldError.value = ''
  const name = username.value.trim()
  if (name.length < 2 || name.length > 32) {
    fieldError.value = '用户名需为 2–32 个字符'
    return false
  }
  if (mode.value === 'register' && password.value.length < 8) {
    fieldError.value = '密码至少 8 位'
    return false
  }
  if (!password.value) {
    fieldError.value = '请填写密码'
    return false
  }
  return true
}

async function submit() {
  if (submitting.value || !validate()) {
    return
  }
  submitting.value = true
  formError.value = ''
  try {
    if (mode.value === 'register') {
      const result = await auth.register(username.value.trim(), password.value)
      // 注册成功回登录页并带回用户名。
      mode.value = 'login'
      username.value = result.username
      password.value = ''
      uni.showToast({ title: '注册成功，请登录', icon: 'none' })
      return
    }
    await auth.login(username.value.trim(), password.value)
    uni.switchTab({ url: '/pages/home/index' })
  } catch (failure) {
    const message = failure instanceof ApiRequestError ? failure.message : '请求失败，请稍后重试'
    if (failure instanceof ApiRequestError && failure.status === 409) {
      fieldError.value = message
      return
    }
    formError.value = message
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 64px 24px 32px;
  box-sizing: border-box;
}
.brand {
  margin-bottom: 36px;
}
.name {
  font-size: 34px;
  font-weight: 700;
  letter-spacing: 4px;
  color: #b4544a;
}
.sub {
  margin-top: 8px;
  color: #8a7f7a;
  font-size: 14px;
}
.form {
  background: #ffffff;
  border-radius: 20px;
  padding: 20px 16px;
}
.switch {
  margin-top: 16px;
  text-align: center;
  color: #b4544a;
  font-size: 14px;
}
.hint {
  margin-top: 18px;
  font-size: 12px;
  color: #a89d98;
  line-height: 1.6;
}
</style>
