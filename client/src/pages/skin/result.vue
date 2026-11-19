<template>
  <view class="page">
    <view v-if="!analysis" class="card empty">
      <view>没有可显示的分析结果。</view>
      <view class="muted">请回到皮肤页重新选择部位拍照。</view>
      <view class="ghost back" @tap="backToSkin">返回皮肤页</view>
    </view>

    <block v-else>
      <view class="card">
        <image v-if="skinDraft.previewUrl" :src="skinDraft.previewUrl" class="preview" mode="aspectFill" />
        <view class="meta">
          <text>{{ analysis.site }}</text>
          <text class="muted">{{ formatMoment(analysis.captured_at) }}</text>
        </view>
        <view v-if="analysis.demo_sample" class="demo">演示样例（未接入真实推理服务）</view>
        <view class="quality" :class="analysis.quality.level">
          {{ analysis.quality.message }}
        </view>
      </view>

      <view class="card section">
        <view class="section-title">可见外观</view>
        <view class="section-text">{{ analysis.visible }}</view>
      </view>
      <view class="card section">
        <view class="section-title">看不清之处</view>
        <view class="section-text">{{ analysis.unclear }}</view>
      </view>
      <view class="card section">
        <view class="section-title">值得留意</view>
        <view class="section-text">{{ analysis.attention }}</view>
      </view>

      <view class="card footnote">
        <view class="muted">AI 观察 · 模型 {{ analysis.model_id }} · 提示版本 {{ analysis.prompt_version }}</view>
        <view class="muted">结果不构成诊断，也不提供改善百分比。</view>
      </view>

      <text v-if="error" class="error">{{ error }}</text>
      <button class="primary" :disabled="saving" @tap="save">
        {{ saving ? '保存中…' : '保存到历史' }}
      </button>
      <view class="actions">
        <view class="ghost action" @tap="discard">不保存</view>
        <view class="ghost action" @tap="retake">重拍</view>
      </view>
    </block>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { formatMoment } from '../../shared/dates'
import { clearSkinDraft, skinDraft } from '../../utils/skinDraft'
import { ApiRequestError } from '../../services/httpClient'
import { discardPending, saveObservation } from '../../services/skinService'

const analysis = skinDraft.analysis
const error = ref('')
const saving = ref(false)

function backToSkin() {
  uni.switchTab({ url: '/pages/skin/index' })
}

async function save() {
  if (!skinDraft.analysis || saving.value) {
    return
  }
  error.value = ''
  saving.value = true
  try {
    await saveObservation(skinDraft.analysis.analysis_id)
    clearSkinDraft()
    uni.showToast({ title: '已保存', icon: 'none' })
    backToSkin()
  } catch (failure) {
    // 失败保留当前页面与所选图片，允许重试。
    error.value =
      failure instanceof ApiRequestError ? failure.message : '保存失败，请重试'
  } finally {
    saving.value = false
  }
}

async function release() {
  if (!skinDraft.analysis) {
    return
  }
  const analysisId = skinDraft.analysis.analysis_id
  try {
    await discardPending(analysisId)
  } catch {
    // 暂存释放失败不阻塞返回，过期后服务端也会自动释放。
  }
  clearSkinDraft()
}

function discard() {
  void release().then(() => uni.navigateBack())
}

function retake() {
  void release().then(() => {
    uni.navigateBack()
    setTimeout(() => uni.switchTab({ url: '/pages/skin/index' }), 120)
  })
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 12px 16px 32px;
  box-sizing: border-box;
}
.preview {
  width: 100%;
  height: 220px;
  border-radius: 14px;
  background: #f2ece9;
}
.meta {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 14px;
}
.demo {
  margin-top: 8px;
  font-size: 12px;
  color: #b4544a;
  background: #fdf2ef;
  border-radius: 8px;
  padding: 6px 10px;
}
.quality {
  margin-top: 8px;
  font-size: 13px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f5f1ef;
  color: #6f635e;
}
.quality.limited {
  background: #fdf2ef;
  color: #a3543f;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
}
.section-text {
  font-size: 14px;
  line-height: 1.7;
}
.footnote {
  line-height: 1.7;
}
.actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}
.action {
  flex: 1;
  font-size: 14px;
}
.back {
  margin-top: 14px;
}
.empty {
  text-align: center;
  padding: 40px 16px;
  line-height: 1.8;
}
</style>
