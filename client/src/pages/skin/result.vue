<template>
  <view class="page plain-bottom">
    <SubHeader
      :title="analysis ? '观察结果' : '没有结果'"
      kicker="皮肤 / RESULT"
      :sub="analysis ? `${analysis.site} · ${formatMoment(analysis.captured_at)}` : '请回到皮肤页重新拍照'"
      fallback="/pages/skin/index"
    />

    <view class="main">
      <view v-if="!analysis" class="card empty">
        <view class="empty-title">没有可显示的分析结果</view>
        <view class="muted">请回到皮肤页重新选择部位拍照。</view>
        <button class="btn block" @tap="backToSkin">返回皮肤页</button>
      </view>

      <template v-else>
        <view class="card">
          <view class="photo-wrap">
            <image v-if="skinDraft.previewUrl" :src="skinDraft.previewUrl" class="preview" mode="aspectFill" />
            <view v-else class="preview placeholder">照片预览</view>
            <view class="photo-time">{{ formatMoment(analysis.captured_at) }}</view>
            <view class="photo-site">{{ analysis.site }}</view>
          </view>

          <view v-if="analysis.demo_sample" class="tag demo">演示样例（未接入真实推理服务）</view>
          <view class="quality" :class="analysis.quality.level">
            {{ analysis.quality.message }}
          </view>
        </view>

        <view class="card">
          <view class="obs-block">
            <view class="k">照片中可见</view>
            <view class="v">{{ analysis.visible }}</view>
          </view>
          <view class="obs-block gap">
            <view class="k">看不清的地方</view>
            <view class="v">{{ analysis.unclear }}</view>
          </view>
          <view class="obs-block gap">
            <view class="k">下次可留意</view>
            <view class="v">{{ analysis.attention }}</view>
          </view>
          <view class="note result-note">
            AI 观察 · 模型 {{ analysis.model_id }} · 提示版本 {{ analysis.prompt_version }}。结果不构成诊断，也不提供改善百分比。
          </view>
        </view>

        <text v-if="error" class="error">{{ error }}</text>
        <button class="btn block" :disabled="saving" @tap="save">
          {{ saving ? '保存中…' : '保存到历史' }}
        </button>
        <view class="actions">
          <view class="btn ghost action" @tap="discard">不保存</view>
          <view class="btn ghost action" @tap="retake">重拍</view>
        </view>
      </template>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SubHeader from '../../components/SubHeader.vue'
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
.photo-wrap {
  position: relative;
  border-radius: 10px;
  overflow: hidden;
  background: var(--photo-grad);
}
.preview {
  width: 100%;
  height: 224px;
  display: block;
}
.preview.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(122, 78, 88, 0.6);
  font-size: 12px;
  letter-spacing: 1px;
}
.photo-time {
  position: absolute;
  right: 8px;
  top: 8px;
  font-size: 11px;
  line-height: 16px;
  padding: 2px 7px;
  border-radius: 5px;
  color: #7a4a55;
  background: rgba(255, 255, 255, 0.82);
}
.photo-site {
  position: absolute;
  left: 8px;
  bottom: 6px;
  font-size: 11px;
  line-height: 16px;
  padding: 2px 6px;
  border-radius: 4px;
  color: rgba(84, 52, 44, 0.85);
  background: rgba(255, 255, 255, 0.74);
}
.demo {
  margin-top: 10px;
}
.quality {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 20px;
  background: var(--soft-grad);
  color: #7a4a55;
}
.quality.limited {
  background: linear-gradient(135deg, #fbe2e6, #fff0f2);
  color: var(--error);
}
.obs-block.gap {
  margin-top: 14px;
}
.result-note {
  margin-top: 14px;
}
.actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}
.action {
  flex: 1;
  height: 44px;
  font-size: 14px;
  letter-spacing: 0;
}
.empty {
  text-align: center;
  padding: 34px 16px 24px;
}
.empty-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 4px;
}
.empty .btn {
  margin-top: 16px;
}
</style>
