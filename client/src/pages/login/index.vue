<template>
  <view class="hr-page auth-page">
    <main class="auth-shell" aria-labelledby="auth-title">
      <header class="auth-header">
        <img class="auth-bloom" src="/static/home-cosmos.png" alt="" />
        <div class="auth-brand">
          <img class="brand-mark" src="/static/herlog-icon.svg" alt="" />
          <span>她记 HerLog</span>
        </div>
        <h1 id="auth-title">{{ registering ? '创建账号' : '欢迎回来' }}</h1>
        <p>{{ registering ? '开始记录自己的身体变化。' : '登录后继续查看你的健康记录。' }}</p>
      </header>

      <H5Form class="card auth-form" novalidate @submit.prevent="submit">
        <div v-if="!registering" class="auth-methods" role="group" aria-label="登录方式">
          <H5Button class="auth-method" :aria-pressed="method === 'phone'" :disabled="formBusy" @click="setMethod('phone')">手机号登录</H5Button>
          <H5Button class="auth-method" :aria-pressed="method === 'password'" :disabled="formBusy" @click="setMethod('password')">账号密码</H5Button>
        </div>

        <template v-if="usesPhone">
          <PhoneVerificationFields v-if="smsAvailable" ref="verification" prefix="auth" :purpose="registering ? 'register' : 'login'"
            :demo="options?.sms_mode === 'demo'" :disabled="submitting" />
          <div v-else class="auth-status" :role="optionsLoading ? 'status' : 'alert'">
            <p>{{ optionsLoading ? '正在读取短信服务…' : optionsFailed ? '暂时无法读取验证方式。' : '短信验证暂不可用。' }}</p>
            <H5Button v-if="!optionsLoading" class="hr-action" @click="loadOptions">重新检查</H5Button>
          </div>
        </template>

        <template v-if="!usesPhone || registering">
          <H5Label class="hr-field-label" for="auth-username">用户名</H5Label>
          <H5Input id="auth-username" ref="usernameInput" v-model="username" class="field"
            placeholder="输入用户名" autocomplete="username" autocapitalize="none" :spellcheck="false" maxlength="32"
            :disabled="submitting" :aria-invalid="fieldIssue === 'username'"
            :aria-describedby="fieldIssue === 'username' ? 'auth-field-error' : undefined" />

          <H5Label class="hr-field-label" for="auth-password">密码</H5Label>
          <div class="password-control">
            <H5Input id="auth-password" ref="passwordInput" v-model="password" class="field"
              :type="showPassword ? 'text' : 'password'" :autocomplete="registering ? 'new-password' : 'current-password'"
              :placeholder="registering ? '至少 8 个字符' : '输入密码'" maxlength="72" :disabled="submitting"
              :aria-invalid="fieldIssue === 'password'" :aria-describedby="fieldIssue === 'password' ? 'auth-field-error' : undefined" />
            <H5Button class="password-toggle" :aria-pressed="showPassword" :disabled="submitting" @click="showPassword = !showPassword">
              {{ showPassword ? '隐藏密码' : '显示密码' }}
            </H5Button>
          </div>

          <template v-if="registering">
            <H5Label class="hr-field-label" for="auth-confirm">确认密码</H5Label>
            <H5Input id="auth-confirm" ref="confirmInput" v-model="confirmPassword" class="field"
              :type="showPassword ? 'text' : 'password'" autocomplete="new-password" maxlength="72"
              placeholder="再次输入密码" :disabled="submitting" :aria-invalid="fieldIssue === 'confirm'"
              :aria-describedby="fieldIssue === 'confirm' ? 'auth-field-error' : undefined" />
          </template>
        </template>

        <p v-if="fieldError || formError" id="auth-field-error" class="error" role="alert">{{ fieldError || formError }}</p>
        <H5Button type="submit" class="primary" :disabled="formBusy || (usesPhone && !smsAvailable) || (registering && optionsLoading)">
          {{ submitting ? '请稍候…' : registering ? '创建账号' : '登录' }}
        </H5Button>
        <p v-if="registering && usesPhone && smsAvailable" class="auth-help">验证成功后会直接进入首页。</p>
        <p v-else-if="!registering && method === 'password' && smsAvailable" class="auth-help">老账号可在登录后到「我的」绑定手机号。</p>
      </H5Form>

      <div class="auth-switch">
        <span>{{ registering ? '已有账号？' : '还没有账号？' }}</span>
        <H5Button class="hr-action" :disabled="formBusy" @click="switchMode">{{ registering ? '去登录' : '注册' }}</H5Button>
      </div>
      <footer class="auth-footer">
        <H5Button class="hr-action" aria-haspopup="dialog" @click="privacyVisible = true">账号与隐私</H5Button>
      </footer>

      <HerlogSheet v-if="privacyVisible" title="账号与隐私" @close="privacyVisible = false">
        <ul class="privacy-copy">
          <li>登录手机号用于接收验证码和验证账号。填写在资料里的联系电话是独立字段。</li>
          <li>发送短信时，收件号码交给短信服务商完成投递。经期、体重和皮肤记录按账号保存。</li>
          <li>已有账号请先用用户名和密码登录，在「我的」绑定手机号，原有记录会保留。</li>
        </ul>
        <template #actions><H5Button class="primary" @click="privacyVisible = false">完成</H5Button></template>
      </HerlogSheet>
    </main>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import H5Form, { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogSheet from '../../components/HerlogSheet.vue'
import PhoneVerificationFields from '../../components/PhoneVerificationFields.vue'
import { useAuthStore } from '../../stores/auth'
import { fetchAuthOptions } from '../../services/authService'
import type { AuthOptions, PhoneProof } from '../../services/authService'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'

const auth = useAuthStore()
const registering = ref(false)
const method = ref<'phone' | 'password'>('password')
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const usernameInput = ref<{ focus: () => void } | null>(null)
const passwordInput = ref<{ focus: () => void } | null>(null)
const confirmInput = ref<{ focus: () => void } | null>(null)
const verification = ref<{ proof(): PhoneProof | null; rejectCode(message: string): void; sending: boolean } | null>(null)
const fieldIssue = ref<'username' | 'password' | 'confirm' | null>(null)
const fieldError = ref('')
const formError = ref('')
const submitting = ref(false)
const privacyVisible = ref(false)
const options = ref<AuthOptions | null>(null)
const optionsLoading = ref(false)
const optionsFailed = ref(false)
let methodChosen = false

const smsAvailable = computed(() => Boolean(options.value && options.value.sms_mode !== 'disabled'))
const usesPhone = computed(() => registering.value ? Boolean(options.value?.requires_phone) : method.value === 'phone')
const formBusy = computed(() => submitting.value || Boolean(verification.value?.sending))

async function loadOptions() {
  if (optionsLoading.value) return
  optionsFailed.value = false
  optionsLoading.value = true
  try {
    options.value = await fetchAuthOptions()
    if (smsAvailable.value && !methodChosen && !username.value && !password.value) method.value = 'phone'
  } catch {
    optionsFailed.value = true
  } finally {
    optionsLoading.value = false
  }
}
onMounted(loadOptions)

function clearError() {
  fieldIssue.value = null
  fieldError.value = formError.value = ''
}
watch([username, password, confirmPassword], clearError)

function setMethod(value: 'phone' | 'password') {
  methodChosen = true
  if (method.value === value) return
  method.value = value
  showPassword.value = false
  clearError()
}

function switchMode() {
  registering.value = !registering.value
  showPassword.value = false
  password.value = confirmPassword.value = ''
  clearError()
}

function invalid(field: 'username' | 'password' | 'confirm', message: string): false {
  fieldIssue.value = field
  fieldError.value = message
  void nextTick(() => ({ username: usernameInput, password: passwordInput, confirm: confirmInput })[field].value?.focus())
  return false
}

function validateCredentials() {
  const size = username.value.trim().length
  if (size < 2 || size > 32) return invalid('username', '用户名需为 2–32 个字符。')
  if (!password.value) return invalid('password', '请填写密码。')
  if (!registering.value) return true
  if (password.value.length < 8) return invalid('password', '密码至少 8 个字符。')
  if (new TextEncoder().encode(password.value).length > 72) return invalid('password', '密码过长，请缩短后重试。')
  if (confirmPassword.value !== password.value) return invalid('confirm', '两次输入的密码不一致。')
  return true
}

async function submit() {
  if (formBusy.value || (registering.value && optionsLoading.value)) return
  clearError()
  const proof = usesPhone.value ? verification.value?.proof() : null
  if (usesPhone.value && !proof) return
  if ((!usesPhone.value || registering.value) && !validateCredentials()) return
  submitting.value = true
  try {
    if (registering.value && proof) {
      await auth.registerByPhone(proof, username.value.trim(), password.value)
    } else if (registering.value) {
      const result = await auth.register(username.value.trim(), password.value)
      registering.value = false
      setMethod('password')
      username.value = result.username
      password.value = confirmPassword.value = ''
      showPassword.value = false
      uni.showToast({ title: '注册成功，请登录', icon: 'none' })
      return
    } else if (proof) {
      await auth.loginByPhone(proof)
    } else {
      await auth.login(username.value.trim(), password.value)
    }
    password.value = confirmPassword.value = ''
    uni.switchTab({ url: '/pages/home/index' })
  } catch (failure) {
    if (failure instanceof StaleSessionError) return
    if (!(failure instanceof ApiRequestError)) {
      formError.value = '请求失败，请稍后重试。'
    } else if (failure.status === 409 && failure.message === '该用户名已被注册') {
      invalid('username', failure.message)
    } else if (failure.data && typeof failure.data === 'object' && 'reason' in failure.data && failure.data.reason === 'sms_invalid') {
      verification.value?.rejectCode(failure.message)
    } else {
      formError.value = failure.message
    }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.auth-page { padding-top: calc(clamp(20px, 5vh, 52px) + env(safe-area-inset-top)); }
.auth-shell { width: min(100%, 410px); margin: 0 auto; }
.auth-header { position: relative; isolation: isolate; overflow: hidden; margin-bottom: 12px; padding: 14px 15px 13px; border: 1px solid var(--hr-line); border-radius: var(--hr-radius-lg); background: linear-gradient(125deg, var(--hr-peach), var(--hr-rose-soft)); }
.auth-bloom { position: absolute; z-index: -1; right: -58px; bottom: -30px; width: 238px; opacity: .54; pointer-events: none; }
.auth-brand { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--hr-rose-deep); font-weight: 650; }
.brand-mark { width: 34px; height: 34px; border-radius: 9px; }
.auth-header h1 { margin: 7px 0 3px; font: 700 clamp(25px, 7vw, 31px)/1.2 var(--hr-font); }
.auth-header p { margin: 0; max-width: 80%; color: var(--hr-ink-2); font-size: 13px; }
.auth-form { padding: 14px; margin: 0; }
.auth-methods { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px; padding: 3px; margin-bottom: 9px; border: 1px solid var(--hr-line); border-radius: 14px; background: var(--hr-paper); }
.auth-method { min-height: 44px; border: 0; border-radius: 10px; background: transparent; color: var(--hr-ink-2); font: 650 14px var(--hr-font); }
.auth-method[aria-pressed="true"] { background: var(--hr-rose-soft); color: var(--hr-rose-deep); }
.auth-form .primary { margin-top: 12px; }
.password-control { position: relative; }
.password-control .field { padding-right: 88px; }
.password-toggle { position: absolute; right: 4px; top: 1px; min-height: 44px; border: 0; background: transparent; color: var(--hr-rose-deep); font-size: 13px; border-radius: 10px; padding: 0 7px; }
.auth-help, .auth-status { color: var(--hr-ink-2); font-size: 13px; line-height: 1.5; }
.auth-help { margin: 7px 0 0; }
.auth-status { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 4px 8px; border-radius: 10px; background: var(--hr-paper); }
.auth-status p { margin: 0; }
.auth-status .hr-action { flex-shrink: 0; padding: 0 4px; }
.auth-switch, .auth-footer { display: flex; justify-content: center; align-items: center; color: var(--hr-ink-2); font-size: 13px; }
.auth-switch { margin-top: 5px; }
.auth-footer .hr-action { color: var(--hr-ink-2); }
.privacy-copy { margin: 0; padding-left: 1.2em; font-size: 14px; line-height: 1.55; }
.privacy-copy li + li { margin-top: 8px; }
</style>
