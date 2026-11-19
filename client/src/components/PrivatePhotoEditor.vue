<template>
  <section class="photo-field" :aria-label="label">
    <div class="photo-heading">
      <strong>{{ label }}</strong>
      <span>选填 · 仅自己可见</span>
    </div>
    <img v-if="preview" :src="preview" :alt="draftUrl ? '待保存的照片' : label" class="photo-preview" :class="{ avatar }" />
    <p v-if="processing || loading" class="photo-status" role="status">{{ processing ? '正在准备照片…' : '正在读取照片…' }}</p>
    <p v-else-if="modelValue === null" class="photo-status">保存后将移除原照片。</p>
    <p v-else-if="draftUrl" class="photo-status">{{ savedPath ? '保存后将替换原照片。' : '保存后将添加这张照片。' }}</p>
    <div v-if="error || readError" class="photo-status photo-error" role="alert">
      {{ error || readError }}
      <H5Button v-if="readError && !error" class="photo-button" :disabled="disabled" @click="reload">重试</H5Button>
    </div>
    <div class="photo-actions">
      <H5Button class="photo-button" :disabled="locked" @click="pick('album')">{{ preview ? '更换照片' : '从相册选图' }}</H5Button>
      <H5Button class="photo-button" :disabled="locked" @click="pick('camera')">拍照</H5Button>
      <H5Button v-if="modelValue !== null && (draftUrl || savedPath)" class="photo-button" :disabled="locked"
        @click="resetPhoto(savedPath ? null : undefined)">移除照片</H5Button>
      <H5Button v-if="savedPath && modelValue !== undefined" class="photo-button" :disabled="locked"
        @click="resetPhoto(undefined)">保留原照片</H5Button>
    </div>
    <PhotoInput />
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onBeforeUnmount, ref } from 'vue'
import H5Button from './H5Button'
import { usePrivatePhoto } from './usePrivatePhoto'
import { currentEpoch, releaseBlobUrl } from '../services/httpClient'
import type { PrivatePhotoPayload } from '../services/privatePhotoService'
import { encodeJpeg } from '../utils/image'

const props = defineProps<{
  label: string
  modelValue?: PrivatePhotoPayload | null
  savedPath?: string
  disabled?: boolean
  avatar?: boolean
}>()
const emit = defineEmits<{
  'update:modelValue': [PrivatePhotoPayload | null | undefined]
  'update:processing': [boolean]
}>()
const draftUrl = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const error = ref('')
const processing = ref(false)
const locked = computed(() => props.disabled || processing.value)
const { url: savedUrl, loading, error: readError, reload } = usePrivatePhoto(() =>
  props.modelValue === undefined ? props.savedPath : undefined
)
const preview = computed(() => props.modelValue === null ? null : draftUrl.value || savedUrl.value)
let mounted = true
const PhotoInput = defineComponent({
  setup: () => () => h('input', { ref: fileInput, type: 'file', accept: 'image/*', hidden: true, onChange: readPhoto })
})

function clearDraft() {
  releaseBlobUrl(draftUrl.value)
  draftUrl.value = null
}

function resetPhoto(value: null | undefined) {
  clearDraft()
  error.value = ''
  emit('update:modelValue', value)
}

function pick(source: 'camera' | 'album') {
  const input = fileInput.value
  if (!input || locked.value) return
  if (source === 'camera') input.setAttribute('capture', 'environment')
  else input.removeAttribute('capture')
  input.click()
}

async function readPhoto(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || locked.value) return
  const epoch = currentEpoch()
  const active = () => mounted && epoch === currentEpoch()
  const path = URL.createObjectURL(file)
  processing.value = true
  emit('update:processing', true)
  error.value = ''
  try {
    const encoded = await encodeJpeg(path, props.avatar ? 512 : 1024)
    if (!active()) {
      releaseBlobUrl(encoded.previewUrl)
      return
    }
    clearDraft()
    draftUrl.value = encoded.previewUrl
    emit('update:modelValue', { image_base64: encoded.base64, mime: encoded.mime })
  } catch (failure) {
    if (active()) error.value = failure instanceof Error ? failure.message : '无法读取照片，请重新选择。'
  } finally {
    releaseBlobUrl(path)
    if (mounted) {
      processing.value = false
      emit('update:processing', false)
    }
  }
}

onBeforeUnmount(() => {
  mounted = false
  clearDraft()
  emit('update:processing', false)
})
</script>

<style scoped>
.photo-field {
  display: grid; gap: 8px; margin-block: 10px; padding: 12px;
  min-width: 0; border: 1px solid var(--hr-line); border-radius: var(--hr-radius);
  background: var(--hr-paper);
}
.photo-heading,.photo-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.photo-heading strong { font-size: 14px; }
.photo-heading span,.photo-status { color: var(--hr-ink-2); font-size: 13px; line-height: 1.5; }
.photo-status { margin: 0; }
.photo-error { color: var(--hr-danger); }
.photo-error .photo-button { margin-inline-start: 8px; }
.photo-preview { display: block; width: 100%; height: min(34vh, 240px); object-fit: contain; background: var(--hr-paper-deep); border-radius: 10px; }
.photo-preview.avatar { width: 88px; height: 88px; object-fit: cover; }
.photo-button {
  min-height: 44px; padding: 7px 11px; font-size: 13px; border: 1px solid var(--hr-line);
  border-radius: 999px; color: var(--hr-rose-deep); background: var(--hr-surface);
}
.photo-button:disabled { opacity: .6; }
</style>
