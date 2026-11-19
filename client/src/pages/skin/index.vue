<template>
  <view class="hr-page herlog-skin" :class="{ 'hr-tab-page': step === 'home' }">
    <SkinResult
      v-if="step === 'result' && analysis"
      :analysis="analysis"
      :preview-url="draft?.image.previewUrl"
      @saved="saved"
      @expired="releaseDraft"
      @discarded="closeFlow"
      @retake="retake"
    />
    <template v-else-if="step === 'home'">
      <SkinStudio v-if="auth.token" :key="auth.token" :latest="latest" :photo-loading="loading" :photo-error="loadError"
        @capture="openCapture" @history="openHistory" @refresh-photo="loadLatest" />
      <TabBar current="/pages/skin/index" />
    </template>
    <template v-else>
      <HerlogHeading :title="step === 'site' ? '选择部位' : '拍照分析'">
        <template #actions><SkinButton class="hr-action" @click="closeFlow">取消</SkinButton></template>
      </HerlogHeading>
      <view v-if="step === 'site'" class="site-grid">
        <SkinButton v-for="item in SKIN_SITES" :key="item" class="skin-button" @click="selectSite(item)">{{ item }}</SkinButton>
      </view>
      <view v-else class="skin-panel">
        <view class="skin-block skin-meta">
          <text>{{ site }}</text>
          <SkinButton v-if="step !== 'analyzing'" class="skin-button skin-link" :disabled="picking" @click="changeSite">更换部位</SkinButton>
        </view>
        <view class="skin-alert">{{ SKIN_FLOWS.notice }}</view>
        <view v-if="error" class="skin-alert skin-alert-error" role="alert">{{ error }}</view>
        <image v-if="draft" class="skin-photo skin-block" :src="draft.image.previewUrl" mode="aspectFit" aria-label="所选照片" />
        <view v-else class="preview-empty skin-block">
          <HerlogIcon name="camera" />
          <text class="skin-muted">选取后可先预览照片</text>
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
            <SkinButton class="ghost" :disabled="picking" @click="pickPhoto('album')">从相册选图</SkinButton>
          </template>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import SkinButton from '../../components/H5Button'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogIcon from '../../components/HerlogIcon.vue'
import { ref, watch } from 'vue'
import { onHide, onShow, onUnload } from '@dcloudio/uni-app'
import TabBar from '../../components/TabBar.vue'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import { analyze, discardPending, listObservations, releaseBlobUrl, SKIN_FLOWS, SKIN_SITES } from '../../services/skinService'
import type { SkinAnalysis, SkinSummaryItem } from '../../services/types'
import { useAuthStore } from '../../stores/auth'
import { chooseImage, encodeJpeg } from '../../utils/image'
import type { SkinDraft } from '../../utils/skinDraft'
import SkinStudio from './SkinStudio.vue'
import SkinResult from './result.vue'
import './skin.css'

const auth = useAuthStore()
const step = ref<'home' | 'site' | 'photo' | 'analyzing' | 'result'>('home')
const latest = ref<SkinSummaryItem | null>(null)
const loading = ref(true)
const loadError = ref(false)
const site = ref('')
const draft = ref<SkinDraft | null>(null)
const analysis = ref<SkinAnalysis | null>(null)
const picking = ref(false)
const error = ref('')
const analyzeFailed = ref(false)
let loadVersion = 0
let flowVersion = 0
let pageVisible = false

async function loadLatest() {
  const version = ++loadVersion
  const epoch = currentEpoch()
  loading.value = true
  loadError.value = false
  try {
    const rows = await listObservations({ limit: 1 })
    if (version === loadVersion && epoch === currentEpoch()) latest.value = rows[0] ?? null
  } catch {
    if (version === loadVersion && epoch === currentEpoch()) loadError.value = true
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

function openHistory(compare: boolean, day?: string) {
  const query = compare ? '?compare=1' : day ? '?day=' + encodeURIComponent(day) : ''
  uni.navigateTo({ url: '/pages/skin/history' + query })
}

function releaseDraft() {
  releaseBlobUrl(draft.value?.image.previewUrl ?? null)
  draft.value = null
}

function resetFlow(next: 'home' | 'site' | 'photo') {
  flowVersion += 1
  releaseDraft()
  analysis.value = null
  error.value = ''
  analyzeFailed.value = false
  picking.value = false
  step.value = next
}

function closeFlow() {
  resetFlow('home')
}

function openCapture() {
  site.value = ''
  resetFlow('site')
}

function changeSite() {
  resetFlow('site')
}

function selectSite(item: string) {
  site.value = item
  step.value = 'photo'
}

function retake() {
  resetFlow('photo')
}

function saved() {
  closeFlow()
  uni.showToast({ title: '皮肤观察已保存', icon: 'none' })
  void loadLatest()
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

watch(() => auth.token, () => {
  closeFlow()
  loadVersion += 1
  latest.value = null
  if (pageVisible && auth.token) void loadLatest()
})
onShow(() => {
  pageVisible = true
  if (auth.token) void loadLatest()
})
onHide(() => {
  pageVisible = false
  loadVersion += 1
  latest.value = null
  closeFlow()
})
onUnload(() => {
  pageVisible = false
  loadVersion += 1
  closeFlow()
})
</script>

<style scoped>
.site-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.preview-empty {
  display: grid; align-content: center; justify-items: center; gap: 8px; min-height: 140px;
  border: 1px dashed var(--hr-line-strong); border-radius: 15px; color: var(--hr-rose-deep); background: var(--hr-peach);
}
.preview-empty svg { width: 30px; height: 30px; }
</style>
