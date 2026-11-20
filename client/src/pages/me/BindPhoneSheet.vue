<template>
  <HerlogSheet title="登录手机号" :busy="busy" @close="emit('close')">
    <template v-if="auth.member?.verified_phone_hint">
      <p class="bound-phone">{{ auth.member.verified_phone_hint }} <span>已验证</span></p>
      <p class="muted">下次可用这个手机号接收验证码并登录原账号。</p>
    </template>
    <template v-else-if="optionsLoading">
      <p class="muted" role="status">正在读取验证方式…</p>
    </template>
    <div v-else-if="!options || options.sms_mode === 'disabled'" class="setup-status" role="alert">
      <p class="muted">短信验证暂不可用。</p>
      <H5Button class="hr-action" @click="loadOptions">重新检查</H5Button>
    </div>
    <H5Form v-else id="bind-phone-form" novalidate @submit.prevent="submit">
      <p class="muted">绑定后，手机号和原密码都可以登录同一个账号。</p>
      <PhoneVerificationFields ref="verification" prefix="binding" purpose="bind"
        :demo="options.sms_mode === 'demo'" :disabled="saving" />
      <H5Label class="hr-field-label" for="binding-password">当前密码</H5Label>
      <H5Input id="binding-password" ref="passwordInput" v-model="password" class="field"
        type="password" autocomplete="current-password" maxlength="72" :disabled="saving" />
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </H5Form>
    <template #actions>
      <H5Button v-if="!auth.member?.verified_phone_hint && options && options.sms_mode !== 'disabled'"
        class="primary" type="submit" form="bind-phone-form" :disabled="busy">{{ saving ? '绑定中…' : '验证并绑定' }}</H5Button>
      <H5Button v-else class="ghost" @click="emit('close')">关闭</H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import H5Button from '../../components/H5Button'
import H5Form, { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogSheet from '../../components/HerlogSheet.vue'
import PhoneVerificationFields from '../../components/PhoneVerificationFields.vue'
import { fetchAuthOptions } from '../../services/authService'
import type { AuthOptions, PhoneProof } from '../../services/authService'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import { useAuthStore } from '../../stores/auth'

const emit = defineEmits<{ close: []; saved: [] }>()
const auth = useAuthStore()
const options = ref<AuthOptions | null>(null)
const optionsLoading = ref(false)
const saving = ref(false)
const password = ref('')
const error = ref('')
const passwordInput = ref<{ focus(): void } | null>(null)
const verification = ref<{ proof(): PhoneProof | null; rejectCode(message: string, consumed?: boolean): void; sending: boolean } | null>(null)
const busy = computed(() => saving.value || Boolean(verification.value?.sending))

async function loadOptions() {
  if (optionsLoading.value) return
  optionsLoading.value = true
  try {
    options.value = await fetchAuthOptions()
  } catch {
    options.value = null
  } finally {
    optionsLoading.value = false
  }
}
onMounted(() => { if (!auth.member?.verified_phone_hint) void loadOptions() })

async function submit() {
  if (busy.value) return
  error.value = ''
  if (!password.value) {
    error.value = '请填写当前密码。'
    passwordInput.value?.focus()
    return
  }
  const proof = verification.value?.proof()
  if (!proof) return
  saving.value = true
  try {
    await auth.bindPhone(proof, password.value)
    password.value = ''
    emit('saved')
  } catch (failure) {
    if (failure instanceof StaleSessionError) return
    if (failure instanceof ApiRequestError && failure.data && typeof failure.data === 'object' && 'reason' in failure.data) {
      if (failure.data.reason === 'sms_invalid') {
        verification.value?.rejectCode(failure.message)
        return
      }
      if (failure.data.reason === 'sms_consumed') {
        verification.value?.rejectCode('请重新获取验证码。', true)
        password.value = ''
        passwordInput.value?.focus()
      }
    }
    error.value = failure instanceof ApiRequestError ? failure.message : '暂时无法确认绑定结果，请重试。'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.bound-phone { color: var(--hr-ink); font-size: 20px; font-weight: 650; }
.bound-phone span { margin-left: 5px; padding: 3px 7px; border-radius: 7px; background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-size: 12px; }
.setup-status { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
</style>
