<template>
  <HerlogSheet title="修改密码" :busy="saving" @close="emit('close')">
    <H5Form id="change-password-form" @submit.prevent="submit">
      <H5Label class="hr-field-label" for="previous-password">当前密码</H5Label>
      <H5Input id="previous-password" v-model="current" class="field" type="password" autocomplete="current-password" :disabled="saving" required />
      <H5Label class="hr-field-label" for="new-password">新密码</H5Label>
      <H5Input id="new-password" v-model="next" class="field" type="password" autocomplete="new-password" :disabled="saving" minlength="8" maxlength="72" required />
      <p class="muted">至少 8 个字符。保存后，各设备需重新登录。</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </H5Form>
    <template #actions>
      <H5Button class="primary" type="submit" form="change-password-form" :disabled="saving">{{ saving ? '保存中…' : '保存新密码' }}</H5Button>
    </template>
  </HerlogSheet>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import H5Button from '../../components/H5Button'
import H5Form, { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { changePassword } from '../../services/homeService'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'

const emit = defineEmits<{ close: []; saved: [] }>()
const current = ref('')
const next = ref('')
const error = ref('')
const saving = ref(false)

async function submit() {
  if (saving.value) return
  if (current.value === next.value) {
    error.value = '新密码需与当前密码不同。'
    return
  }
  const epoch = currentEpoch()
  saving.value = true
  error.value = ''
  try {
    await changePassword(current.value, next.value)
    if (epoch === currentEpoch()) emit('saved')
  } catch (failure) {
    if (epoch !== currentEpoch()) return
    error.value = failure instanceof ApiRequestError && failure.status > 0
      ? failure.message : '暂时无法确认保存结果。请先确认是否还能使用当前密码登录。'
  } finally {
    saving.value = false
  }
}
</script>
