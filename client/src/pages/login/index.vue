<template>
  <view class="hr-page auth-page">
    <view class="auth-shell">
      <header class="auth-heading">
        <span class="brand-mark" aria-hidden="true"><span /></span>
        <view class="brand-name">她记 HerLog</view>
        <h1>{{ mode === 'login' ? '欢迎回来' : '创建账号' }}</h1>
        <view class="muted">女性健康记录助手</view>
      </header>

      <H5Form class="card auth-form" novalidate @submit.prevent="submit">
        <H5Label class="hr-field-label" for="auth-username">用户名</H5Label>
        <H5Input id="auth-username" ref="usernameInput" v-model="username" class="field"
          autocomplete="username" autocapitalize="none" :spellcheck="false" maxlength="32"
          :aria-invalid="fieldIssue === 'username'" :aria-describedby="fieldIssue === 'username' ? 'username-error' : undefined" />
        <view v-if="fieldIssue === 'username'" id="username-error" class="error" role="alert">{{ fieldError }}</view>

        <H5Label class="hr-field-label" for="auth-password">密码</H5Label>
        <view class="password-control">
          <H5Input id="auth-password" ref="passwordInput" v-model="password" class="field"
            :type="showPassword ? 'text' : 'password'" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
            :aria-invalid="fieldIssue === 'password'"
            :aria-describedby="fieldIssue === 'password' ? 'password-error' : mode === 'register' ? 'password-help' : undefined"
            maxlength="72" />
          <H5Button class="password-toggle" :aria-pressed="showPassword" @click="showPassword = !showPassword">
            {{ showPassword ? '隐藏密码' : '显示密码' }}
          </H5Button>
        </view>
        <view v-if="fieldIssue === 'password'" id="password-error" class="error" role="alert">{{ fieldError }}</view>
        <view v-else-if="mode === 'register'" id="password-help" class="muted password-help">至少 8 位字符</view>
        <view v-if="formError" class="error" role="alert">{{ formError }}</view>

        <H5Button type="submit" class="primary" :disabled="submitting">
          {{ submitting ? '请稍候…' : mode === 'login' ? '登录' : '注册' }}
        </H5Button>
      </H5Form>

      <H5Button class="hr-action mode-switch" :disabled="submitting" @click="switchMode">
        {{ mode === 'login' ? '还没有账号？注册' : '已有账号？去登录' }}
      </H5Button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import H5Button from '../../components/H5Button'
import H5Form, { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import { useAuthStore } from '../../stores/auth'
import { ApiRequestError } from '../../services/httpClient'

const auth = useAuthStore()
const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const usernameInput = ref<{ focus: () => void } | null>(null)
const passwordInput = ref<{ focus: () => void } | null>(null)
const fieldIssue = ref<'username' | 'password' | null>(null)
const fieldError = ref('')
const formError = ref('')
const submitting = ref(false)

function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  showPassword.value = false
  fieldIssue.value = null
  fieldError.value = ''
  formError.value = ''
}

function invalid(field: 'username' | 'password', message: string): false {
  fieldIssue.value = field
  fieldError.value = message
  void nextTick(() => (field === 'username' ? usernameInput.value : passwordInput.value)?.focus())
  return false
}

function validate(): boolean {
  fieldIssue.value = null
  fieldError.value = ''
  const name = username.value.trim()
  if (name.length < 2 || name.length > 32) return invalid('username', '用户名需为 2–32 个字符')
  if (!password.value) return invalid('password', '请填写密码')
  if (mode.value === 'register' && password.value.length < 8) return invalid('password', '密码至少 8 位')
  return true
}

async function submit() {
  if (submitting.value || !validate()) return
  submitting.value = true
  formError.value = ''
  try {
    if (mode.value === 'register') {
      const result = await auth.register(username.value.trim(), password.value)
      mode.value = 'login'
      username.value = result.username
      password.value = ''
      showPassword.value = false
      uni.showToast({ title: '注册成功，请登录', icon: 'none' })
      return
    }
    await auth.login(username.value.trim(), password.value)
    uni.switchTab({ url: '/pages/home/index' })
  } catch (failure) {
    const message = failure instanceof ApiRequestError ? failure.message : '请求失败，请稍后重试'
    if (failure instanceof ApiRequestError && failure.status === 409) invalid('username', message)
    else formError.value = message
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-page { padding-top: calc(clamp(42px, 9vh, 86px) + env(safe-area-inset-top)); }
.auth-shell { width: min(100%, 400px); margin: 0 auto; display: grid; gap: 12px; justify-items: stretch; }
.auth-heading { text-align: center; margin-bottom: 8px; }
.brand-mark {
  display: grid; place-items: center; width: 58px; height: 58px; margin: 0 auto 11px; border-radius: 18px;
  background: linear-gradient(145deg, var(--hr-rose), var(--hr-rose-deep)); color: #fff;
  box-shadow: 0 10px 21px -13px #7f3652cc;
}
.brand-mark > span {
  display: grid; place-items: center; width: 28px; height: 28px;
  border: 2px solid currentColor; border-radius: 50%;
}
.brand-mark > span::after { content: ""; width: 11px; height: 11px; border-radius: 50%; border: 2px solid currentColor; }
.brand-name { font-size: 14px; font-weight: 650; color: var(--hr-rose-deep); }
h1 { margin: 4px 0 3px; font-size: 30px; line-height: 1.25; }
.auth-form { padding: 16px; margin: 0; }
.auth-form .primary { margin-top: 10px; }
.password-control { position: relative; }
.password-control .field { padding-right: 92px; }
.password-toggle {
  position: absolute; right: 4px; top: 1px; min-height: 44px; border: 0;
  background: transparent; color: var(--hr-rose-deep); font-size: 13px; border-radius: 10px; padding: 0 7px;
}
.password-help { margin-bottom: 6px; }
.mode-switch { justify-self: center; }
</style>
