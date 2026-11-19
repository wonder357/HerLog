<template>
  <view class='herlog-skin'>
    <SkinResult
      v-if="step === 'result' && analysis"
      :analysis="analysis" :return-label="returnLabel"
      :preview-url="draft?.image.previewUrl"
      @saved="emit('saved')"
      @expired="releaseDraft"
      @discarded="emit('close')"
      @retake="retake"
    />
    <template v-else>
      <HerlogHeading title="拍照记录" back-label="取消" @back="emit('close')" />
      <view v-if="!draft" class="site-grid" role="group" aria-label="选择拍摄部位">
        <SkinButton v-for="item in SKIN_SITES" :key="item" class="skin-button" :class="{ 'site-selected': site === item }"
          :aria-pressed="site === item" :disabled="picking" @click="selectSite(item)">{{ item }}</SkinButton>
      </view>
      <view v-if="step !== 'site'" class="skin-panel">
        <view v-if="draft" class="skin-block skin-meta">
          <text>{{ site }}</text>
          <SkinButton v-if="step !== 'analyzing'" class="skin-button skin-link" :disabled="picking" @click="changeSite">更换部位</SkinButton>
        </view>
        <view v-if="draft" class="skin-alert">{{ SKIN_FLOWS.notice }}</view>
        <view v-if="error" class="skin-alert skin-alert-error" role="alert">{{ error }}</view>
        <image v-if="draft" class="skin-photo skin-block" :src="draft.image.previewUrl" mode="aspectFit" aria-label="所选照片" />
        <view v-else class="capture-example skin-block">
          <svg viewBox="0 0 120 120" role="img" :aria-label="`${site}取景示意`">
            <path v-if="faceSite" d="M60 14c-19 0-29 14-29 35v12c0 22 15 38 29 38s29-16 29-38V49c0-21-10-35-29-35Z M43 53h8m18 0h8m-17 0-4 15h7m-10 11q7 4 14 0" />
            <path v-else-if="site === '手臂'" d="M25 89l22-25 20-38q5-9 13-4t5 14L69 76 44 105Z" />
            <path v-else-if="site !== '其他'" d="M49 19v18q0 6-8 8L24 51q-11 4-14 16l-3 25h106l-3-25q-3-12-14-16l-17-6q-8-2-8-8V19 M38 91V75m44 16V75" />
            <path v-else d="M29 71c0-20 15-34 34-34s28 10 28 25-11 22-24 22H43q-14 0-14-13Z" />
            <rect v-for="frame in guide.frames" :key="frame.x" v-bind="frame" rx="5" class="capture-frame" />
          </svg>
          <view><strong>{{ site }}取景示意</strong><view class="skin-muted">{{ guide.tip }} 光线均匀，避开滤镜。</view></view>
        </view>
        <view v-if="step === 'analyzing'" class="skin-block skin-panel" role="status" aria-busy="true">
          <view>正在分析…</view>
          <view class="skin-skeleton" />
          <view class="skin-skeleton" />
          <view class="skin-skeleton" />
        </view>
        <view v-else class="skin-actions">
          <template v-if="draft">
            <SkinButton class="ghost" :disabled="picking" @click="pickPhoto()">{{ picking ? '正在处理…' : '换一张' }}</SkinButton>
            <SkinButton class="primary" :disabled="picking" @click="analyzeDraft">{{ analyzeFailed ? '重试' : '开始分析' }}</SkinButton>
          </template>
          <template v-else>
            <SkinButton class="primary" :disabled="picking" @click="pickPhoto('camera')">{{ picking ? '正在处理…' : '拍照' }}</SkinButton>
            <SkinButton class="ghost" :disabled="picking" @click="pickPhoto('album')">选照片</SkinButton>
          </template>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import SkinButton from '../../components/H5Button'
import HerlogHeading from '../../components/HerlogHeading.vue'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import { analyze, discardPending, releaseBlobUrl, SKIN_FLOWS, SKIN_SITES } from '../../services/skinService'
import type { SkinAnalysis } from '../../services/types'
import { chooseImage, encodeJpeg } from '../../utils/image'
import type { SkinDraft } from '../../utils/skinDraft'
import SkinResult from './result.vue'
import './skin.css'

defineProps<{ returnLabel?: string }>()
const emit = defineEmits<{ saved: []; close: [] }>()
const step = ref<'site' | 'photo' | 'analyzing' | 'result'>('site')
const site = ref('')
const faceSite = computed(() => ['面部', '额头', '下巴', '脸颊'].includes(site.value))
const guides: Record<string, { tip: string; frames: { x: number; y: number; width: number; height: number }[] }> = {
  面部: { tip: '正对镜头，让整张脸入框。', frames: [{ x: 25, y: 12, width: 70, height: 90 }] },
  额头: { tip: '拨开头发，拍清眉毛上方。', frames: [{ x: 38, y: 26, width: 44, height: 18 }] },
  下巴: { tip: '稍抬下巴，拍到下唇下方和下巴边缘。', frames: [{ x: 43, y: 81, width: 34, height: 20 }] },
  脸颊: { tip: '稍微侧脸，拍清要记录的一侧。', frames: [{ x: 33, y: 60, width: 20, height: 18 }, { x: 67, y: 60, width: 20, height: 18 }] },
  颈部: { tip: '拨开头发或衣领，让目标区域入框。', frames: [{ x: 43, y: 24, width: 34, height: 26 }] },
  背部: { tip: '镜头尽量与背部平行，可请人帮拍。', frames: [{ x: 36, y: 52, width: 48, height: 37 }] },
  胸口: { tip: '只拍需要记录的皮肤，可裁掉无关区域。', frames: [{ x: 45, y: 54, width: 30, height: 21 }] },
  手臂: { tip: '放松手臂，让目标区域和周围皮肤入框。', frames: [{ x: 49, y: 41, width: 29, height: 36 }] },
  其他: { tip: '对准要记录的区域，留一点周围皮肤作对照。', frames: [{ x: 40, y: 40, width: 41, height: 40 }] },
}
const guide = computed(() => guides[site.value] ?? guides['其他'])
const draft = ref<SkinDraft | null>(null)
const analysis = ref<SkinAnalysis | null>(null)
const picking = ref(false)
const error = ref('')
const analyzeFailed = ref(false)
let flowVersion = 0

function releaseDraft() {
  releaseBlobUrl(draft.value?.image.previewUrl ?? null)
  draft.value = null
}

function resetFlow(next: 'site' | 'photo') {
  flowVersion += 1
  releaseDraft()
  analysis.value = null
  error.value = ''
  analyzeFailed.value = false
  picking.value = false
  step.value = next
}

function changeSite() {
  resetFlow('site')
}

function selectSite(item: string) {
  error.value = ''
  site.value = item
  step.value = 'photo'
}

function retake() {
  resetFlow('photo')
}

async function pickPhoto(source?: 'camera' | 'album') {
  if (picking.value) return
  const version = flowVersion
  const epoch = currentEpoch()
  picking.value = true
  error.value = ''
  let path: string | null = null
  try {
    path = await chooseImage(source)
    if (!path || version !== flowVersion || epoch !== currentEpoch()) return
    const capturedAt = new Date().toISOString()
    const image = await encodeJpeg(path)
    if (version !== flowVersion || epoch !== currentEpoch()) {
      releaseBlobUrl(image.previewUrl)
      return
    }
    releaseDraft()
    draft.value = { site: site.value, capturedAt, image }
    analyzeFailed.value = false
  } catch (failure) {
    if (version === flowVersion && epoch === currentEpoch()) {
      error.value = failure instanceof Error ? failure.message : '没有处理完这张照片，请重新选择'
    }
  } finally {
    releaseBlobUrl(path)
    if (version === flowVersion) picking.value = false
  }
}

async function analyzeDraft() {
  const selected = draft.value
  if (!selected || step.value !== 'photo' || picking.value) return
  const version = flowVersion
  const epoch = currentEpoch()
  error.value = ''
  step.value = 'analyzing'
  try {
    const result = await analyze({
      site: selected.site,
      captured_at: selected.capturedAt,
      mime: selected.image.mime,
      image_base64: selected.image.base64
    })
    if (version !== flowVersion || epoch !== currentEpoch()) {
      if (epoch === currentEpoch()) void discardPending(result.analysis_id).catch(() => undefined)
      return
    }
    analysis.value = result
    step.value = 'result'
  } catch (failure) {
    if (version !== flowVersion || epoch !== currentEpoch() || failure instanceof StaleSessionError) return
    step.value = 'photo'
    analyzeFailed.value = true
    error.value = failure instanceof ApiRequestError && failure.status === 422
      ? failure.message
      : '这次分析没有完成，可以重试'
  }
}

onBeforeUnmount(() => resetFlow('site'))
</script>

<style scoped>
.site-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.site-grid .site-selected { border-color: var(--hr-rose); background: var(--hr-rose-soft); color: var(--hr-rose-deep); }
.capture-example {
  display: grid; grid-template-columns: 88px minmax(0, 1fr); align-items: center; gap: 12px;
  padding: 10px; border-radius: 12px; background: var(--hr-peach);
}
.capture-example svg { display: block; width: 88px; height: 88px; }
.capture-example path { fill: none; stroke: var(--hr-ink-2); stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
.capture-frame { fill: #f6b6c57a; stroke: var(--hr-rose-deep); stroke-width: 1.6; stroke-dasharray: 4 3; }
</style>
