<template>
  <div class="verification-fields">
    <H5Label class="hr-field-label" :for="prefix + '-phone'">手机号</H5Label>
    <div class="phone-field">
      <span aria-hidden="true">+86</span>
      <H5Input :id="prefix + '-phone'" ref="phoneInput" v-model="phone" class="field"
        type="tel" inputmode="tel" autocomplete="tel-national" maxlength="24" placeholder="11 位中国大陆手机号"
        :disabled="disabled" :aria-invalid="Boolean(phoneError)" :aria-describedby="phoneError ? prefix + '-phone-error' : undefined" />
    </div>
    <p v-if="phoneError" :id="prefix + '-phone-error'" class="error" role="alert">{{ phoneError }}</p>

    <H5Label class="hr-field-label" :for="prefix + '-code'">短信验证码</H5Label>
    <div class="code-row">
      <H5Input :id="prefix + '-code'" ref="codeInput" v-model="code" class="field"
        inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="6 位验证码"
        :disabled="disabled" :aria-invalid="Boolean(codeError)" :aria-describedby="prefix + '-code-info'" />
      <H5Button class="code-send" :disabled="disabled || sending || secondsLeft > 0" @click="send">
        {{ sending ? '发送中…' : secondsLeft > 0 ? secondsLeft + ' 秒后重发' : challenge ? '重新发送' : '获取验证码' }}
      </H5Button>
    </div>
    <div :id="prefix + '-code-info'">
      <p v-if="codeError || sendError" class="error" role="alert">{{ codeError || sendError }}</p>
      <p v-else-if="challenge" class="verification-note" role="status">
        {{ expired ? '验证码已过期，请重新获取。' : '验证码已发送，5 分钟内有效。' }}
      </p>
      <p v-if="demo" class="verification-note demo-note" role="status">
        {{ challenge?.demo_code ? '本机演示验证码 ' + challenge.demo_code : '本机演示支持 1990000 开头的测试号码。' }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import H5Button from './H5Button'
import H5Input from './H5Input'
import { H5Label } from './H5Form'
import { requestSmsCode } from '../services/authService'
import type { PhoneProof, SmsChallenge, SmsPurpose } from '../services/authService'
import { ApiRequestError, StaleSessionError } from '../services/httpClient'

const props = defineProps<{ prefix: string; purpose: SmsPurpose; demo?: boolean; disabled?: boolean }>()
const phone = ref('')
const code = ref('')
const phoneInput = ref<{ focus(): void } | null>(null)
const codeInput = ref<{ focus(): void } | null>(null)
const phoneError = ref('')
const codeError = ref('')
const sendError = ref('')
const sending = ref(false)
const challenge = ref<(SmsChallenge & { expiresAt: number }) | null>(null)
const deadlines = reactive(new Map<string, number>())
const now = ref(Date.now())
const normalized = computed(() => phone.value.trim().replace(/[ -]/g, '').replace(/^\+86/, ''))
const secondsLeft = computed(() => Math.max(0, Math.ceil(((deadlines.get(normalized.value) ?? 0) - now.value) / 1000)))
const expired = computed(() => Boolean(challenge.value && challenge.value.expiresAt <= now.value))
let revision = 0
let timer: ReturnType<typeof setInterval> | undefined
let mounted = true

onMounted(() => { timer = setInterval(() => { now.value = Date.now() }, 1000) })
onBeforeUnmount(() => { mounted = false; clearInterval(timer) })
watch([normalized, () => props.purpose], () => {
  revision += 1
  challenge.value = null
  phoneError.value = codeError.value = sendError.value = ''
  code.value = ''
}, { flush: 'sync' })

function validatePhone() {
  if (/^1[3-9][0-9]{9}$/.test(normalized.value)) return true
  phoneError.value = '请输入 11 位中国大陆手机号。'
  void nextTick(() => phoneInput.value?.focus())
  return false
}

watch(code, () => { codeError.value = '' }, { flush: 'sync' })

function delay(number: string, seconds: number) {
  const moment = Date.now()
  deadlines.set(number, moment + seconds * 1000)
  now.value = moment
}

async function send() {
  now.value = Date.now()
  if (sending.value || props.disabled || secondsLeft.value > 0 || !validatePhone()) return
  sending.value = true
  const number = normalized.value
  const request = revision
  codeError.value = sendError.value = ''
  try {
    const result = await requestSmsCode(number, props.purpose)
    if (!mounted) return
    delay(number, result.resend_in)
    if (request !== revision) return
    challenge.value = { ...result, expiresAt: Date.now() + result.expires_in * 1000 }
    code.value = ''
    void nextTick(() => codeInput.value?.focus())
  } catch (failure) {
    if (!mounted || failure instanceof StaleSessionError) return
    if (failure instanceof ApiRequestError && typeof failure.data === 'object' && failure.data && 'retry_after' in failure.data) {
      const seconds = Number(failure.data.retry_after)
      if (Number.isFinite(seconds) && seconds > 0) delay(number, seconds)
    }
    if (request === revision) sendError.value = failure instanceof ApiRequestError ? failure.message : '发送失败，请稍后重试。'
  } finally {
    if (mounted) sending.value = false
  }
}

function proof(): PhoneProof | null {
  codeError.value = ''
  now.value = Date.now()
  if (sending.value || !validatePhone()) return null
  if (!challenge.value) codeError.value = '请先获取验证码。'
  else if (expired.value) codeError.value = '验证码已过期，请重新获取。'
  else if (!/^[0-9]{6}$/.test(code.value)) codeError.value = '请输入 6 位短信验证码。'
  if (!challenge.value || codeError.value) {
    void nextTick(() => codeInput.value?.focus())
    return null
  }
  return { phone: normalized.value, challenge_id: challenge.value.challenge_id, code: code.value }
}

function rejectCode(message: string, consumed = false) {
  if (consumed) {
    challenge.value = null
    code.value = ''
  }
  codeError.value = message
}

defineExpose({ proof, rejectCode, sending })
</script>

<style scoped>
.verification-fields { min-width: 0; }
.phone-field { position: relative; }
.phone-field span { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); font-size: 14px; color: var(--hr-ink-2); pointer-events: none; }
.phone-field .field { padding-left: 43px; }
.code-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: start; gap: 7px; }
.code-row .field { min-width: 0; }
.code-send { min-height: 46px; border-radius: 12px; border: 1px solid var(--hr-line-strong); padding: 5px 9px; background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-size: 13px; white-space: nowrap; }
.code-send:disabled { color: var(--hr-ink-2); background: var(--hr-paper-deep); }
.verification-note { margin: 6px 0; color: var(--hr-ink-2); font-size: 12px; line-height: 1.5; }
.demo-note { padding: 6px 8px; border-radius: 8px; background: var(--hr-plum-soft); color: var(--hr-plum); }
</style>
