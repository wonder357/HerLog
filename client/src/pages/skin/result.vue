<template>
  <view>
    <HerlogHeading title="观察结果" :description="analysis.site + ' · ' + formatMoment(analysis.captured_at)" />

    <view v-if="error" class="skin-alert skin-alert-error" role="alert">{{ error }}</view>
    <template v-if="expired">
      <view class="skin-actions">
        <SkinButton class="skin-button" @click="emit('discarded')">{{ returnLabel ?? '返回皮肤' }}</SkinButton>
        <SkinButton class="skin-button skin-primary" @click="emit('retake')">重拍</SkinButton>
      </view>
    </template>
    <template v-else>
      <view v-if="analysis.quality.level === 'limited'" class="skin-alert" role="status">
        {{ analysis.quality.message }}
      </view>
      <image v-if="previewUrl" class="skin-photo skin-block" :src="previewUrl" mode="aspectFit" aria-label="待保存的照片" />
      <view class="skin-panel skin-block">
        <ObservationCopy :observation="analysis" />
      </view>
      <view v-if="!analysis.demo_sample" class="skin-muted skin-block">
        模型 {{ analysis.model_id }}
        <text v-if="analysis.inference_ms != null"> · 推理 {{ (analysis.inference_ms / 1000).toFixed(1) }} 秒</text>
      </view>
      <view class="skin-actions result-actions">
        <SkinButton v-if="uncertain" class="skin-button skin-link" :disabled="busy" @click="emit('discarded')">{{ returnLabel ?? '返回皮肤' }}</SkinButton>
        <template v-else>
          <SkinButton class="skin-button skin-link" :disabled="busy" @click="discard(false)">不保存</SkinButton>
          <SkinButton class="skin-button" :disabled="busy" @click="discard(true)">重拍</SkinButton>
        </template>
        <SkinButton class="skin-button skin-primary" :disabled="busy" @click="save">
          {{ busy ? busyLabel : uncertain ? '重试保存' : '保存' }}
        </SkinButton>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import SkinButton from '../../components/H5Button'
import HerlogHeading from '../../components/HerlogHeading.vue'
import { ref } from 'vue'
import { formatMoment } from '../../shared/dates'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import { discardPending, saveObservation } from '../../services/skinService'
import type { SkinAnalysis } from '../../services/types'
import ObservationCopy from './ObservationCopy.vue'

const props = defineProps<{ analysis: SkinAnalysis; previewUrl?: string; returnLabel?: string }>()
const emit = defineEmits<{ saved: []; expired: []; discarded: []; retake: [] }>()
const error = ref('')
const busy = ref(false)
const busyLabel = ref('')
const uncertain = ref(false)
const expired = ref(false)

async function save() {
  if (busy.value || expired.value) return
  const epoch = currentEpoch()
  busy.value = true
  busyLabel.value = '保存中…'
  error.value = ''
  try {
    await saveObservation(props.analysis.analysis_id)
    if (epoch === currentEpoch()) emit('saved')
  } catch (failure) {
    if (epoch !== currentEpoch() || failure instanceof StaleSessionError) return
    if (failure instanceof ApiRequestError && failure.status === 410) {
      expired.value = true
      error.value = '这张结果已过期，请重新拍一次'
      emit('expired')
    } else {
      uncertain.value = failure instanceof ApiRequestError && (failure.status === 0 || failure.status >= 500)
      error.value = uncertain.value
        ? '保存状态暂未确认，可以重试或回历史查看'
        : '这次保存没有完成，可以重试'
    }
  } finally {
    busy.value = false
  }
}

async function discard(retake: boolean) {
  if (busy.value) return
  const epoch = currentEpoch()
  busy.value = true
  busyLabel.value = retake ? '准备重拍…' : '正在返回…'
  try {
    await discardPending(props.analysis.analysis_id)
  } catch {
    // 服务端 TTL 会释放未提交的草稿。
  } finally {
    if (epoch === currentEpoch()) {
      if (retake) emit('retake')
      else emit('discarded')
    }
    busy.value = false
  }
}
</script>

<style scoped>
.result-actions { position: sticky; bottom: 0; padding: 8px 0; background: var(--skin-paper); }
</style>
