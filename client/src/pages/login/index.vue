<template>
  <view class="page auth plain-bottom">
    <view class="auth-hero">
      <view class="logo">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="8.6" />
          <path d="M12 7.4c1.9 2.6 3 4 3 5.2a3 3 0 0 1-6 0c0-1.2 1.1-2.6 3-5.2z" />
        </svg>
      </view>
      <view class="auth-title">{{ mode === 'login' ? '欢迎回来' : '建立账号' }}</view>
      <view class="auth-sub">
        {{ mode === 'login' ? '用账号继续记录今天' : '用户名加密码，不需要手机号' }}
      </view>
    </view>

    <view class="auth-card">
      <view class="field-label">用户名</view>
      <input
        v-model="username"
        class="control"
        placeholder="2–32 个字符"
        placeholder-class="ph"
        maxlength="32"
      />

      <view class="field-label">密码</view>
      <input
        v-model="password"
        class="control"
        password
        :placeholder="mode === 'register' ? '至少 8 位' : '登录密码'"
        placeholder-class="ph"
        maxlength="72"
      />

      <text v-if="fieldError" class="error">{{ fieldError }}</text>
      <text v-if="formError" class="error">{{ formError }}</text>

      <button class="btn block submit" :disabled="submitting" @tap="submit">
        {{ submitting ? '请稍候…' : mode === 'login' ? '登录' : '注册' }}
      </button>

      <view class="auth-note">
        {{ mode === 'login' ? '登录后才能查看你的记录；退出登录不会删除数据。' : '注册成功后回到登录页，用同一组账号登录。' }}
      </view>
    </view>

    <view class="auth-foot" @tap="switchMode">
      <text>{{ mode === 'login' ? '还没有账号？' : '已有账号？' }}</text>
      <text class="auth-foot-link">{{ mode === 'login' ? '注册' : '去登录' }}</text>
    </view>

    <view class="auth-glow" />
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
.auth {
  position: relative;
  overflow: hidden;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 40%, var(--page) 100%),
    var(--hero-grad);
}
.auth-hero {
  position: relative;
  z-index: 1;
  padding: calc(56px + var(--status-bar-height, 0px)) 16px 26px;
  text-align: center;
}
.logo {
  width: 66px;
  height: 66px;
  margin: 0 auto 14px;
  border-radius: 19px;
  background: linear-gradient(150deg, #d6788b 0%, #a82760 52%, #9c3b50 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 18px 34px -16px rgba(156, 59, 80, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.35);
}
.auth-title {
  font-size: 26px;
  line-height: 34px;
  font-weight: 600;
  letter-spacing: 1px;
  color: var(--ink);
}
.auth-sub {
  margin-top: 6px;
  font-size: 13px;
  line-height: 20px;
  color: var(--ink-2);
}
.auth-card {
  position: relative;
  z-index: 1;
  margin: 0 16px;
  padding: 6px 16px 18px;
  border-radius: 12px;
  background: var(--card-grad);
  border: 1px solid var(--card-line);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9), var(--card-shadow);
}
.submit {
  margin-top: 18px;
}
.auth-note {
  margin-top: 12px;
  font-size: 12px;
  line-height: 18px;
  color: var(--ink-2);
  text-align: center;
}
.auth-foot {
  position: relative;
  z-index: 1;
  width: fit-content;
  margin: 18px auto 0;
  padding: 7px 14px;
  border-radius: 16px;
  background: rgba(255, 252, 250, 0.92);
  box-shadow: 0 10px 24px -18px rgba(156, 59, 80, 0.5);
  font-size: 13px;
  color: var(--ink-2);
  text-align: center;
}
.auth-foot-link {
  margin-left: 4px;
  color: var(--berry);
  font-weight: 600;
}
.auth-glow {
  position: absolute;
  left: 50%;
  bottom: -140px;
  width: 300px;
  height: 300px;
  margin-left: -150px;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, rgba(242, 180, 188, 0.5) 0%, rgba(242, 180, 188, 0) 70%);
  pointer-events: none;
}
</style>
