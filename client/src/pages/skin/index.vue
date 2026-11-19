<template>
  <view class="page">
    <view class="hero skin-hero">
      <view class="h-title">皮肤</view>
      <view class="h-sub">拍照观察，记录同一部位的变化</view>
      <view class="skin-actions">
        <view class="btn sk-btn" :class="{ busy: analyzing }" @tap="siteVisible = true">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 8.5h3l1.6-2.2h6.8L17 8.5h3a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1z" />
            <circle cx="12" cy="13.6" r="3.4" />
          </svg>
          <text>{{ analyzing ? '正在分析…' : '拍照分析' }}</text>
        </view>
        <view class="btn ghost sk-btn" @tap="openHistory">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#C0566B" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="8.4" />
            <path d="M12 7.6V12l3.2 2" />
          </svg>
          <text>历史记录</text>
        </view>
      </view>
    </view>

    <view class="main">
      <view class="section-head skin-head">
        <view class="h2">最近一次观察</view>
        <view class="link" @tap="openHistory">共 {{ total }} 次</view>
      </view>

      <view v-if="latest" class="card">
        <view class="mock">
          <image v-if="latestPhoto" class="mock-img" :src="latestPhoto" mode="aspectFill" />
          <view v-else class="mock-glyph">
            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="rgba(122,74,85,.55)" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 8.5h3l1.6-2.2h6.8L17 8.5h3a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1z" />
              <circle cx="12" cy="13.6" r="3.4" />
            </svg>
          </view>
          <view class="mock-time">{{ formatMoment(latest.captured_at) }}</view>
          <view class="mock-site">{{ latest.site }}</view>
        </view>

        <view class="latest-tags">
          <view class="tag">AI 观察</view>
          <view class="tag plain">已保存</view>
          <view class="latest-privacy">照片仅本人可见</view>
        </view>

        <view class="obs-block">
          <view class="k">照片中可见</view>
          <view class="v">{{ latest.visible }}</view>
        </view>

        <view class="link more" @tap="openHistory">查看完整结果 ›</view>
        <view class="note obs-note">
          以上为模型生成的观察文字，不构成诊断；某次未提及一种现象，不代表它不存在。
        </view>
      </view>

      <view v-else class="card">
        <view class="empty-title">还没有保存过观察</view>
        <view class="muted">选好部位拍一张，确认结果后才会进入历史。</view>
        <view class="empty-glyph">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="rgba(192,86,107,.4)" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 8.5h3l1.6-2.2h6.8L17 8.5h3a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1z" />
            <circle cx="12" cy="13.6" r="3.4" />
          </svg>
        </view>
      </view>

      <view class="note page-note">
        照片会在你确认后发送至模型服务，仅用于本次观察；不保存或重拍不会新增记录。
      </view>

      <view class="hintbox tips">
        <view class="tip-line">· 只描述可见外观，不给病名、严重程度评分或改善百分比。</view>
        <view class="tip-line">· 点「保存」才会写入历史；不保存或重拍不会新增记录。</view>
        <view class="tip-line">· 判断不舒服或变化明显时，请线下就医。</view>
      </view>
    </view>

    <view v-if="siteVisible" class="sheet-mask" @tap="siteVisible = false" />
    <view v-if="siteVisible" class="sheet">
      <view class="grab" />
      <view class="sheet-head">
        <view>
          <view class="sheet-title">选择部位</view>
          <view class="sheet-sub">同一部位再次拍摄，变化更容易对照</view>
        </view>
        <view class="sheet-x" @tap="siteVisible = false">×</view>
      </view>
      <view class="sheet-body">
        <view class="chips">
          <view v-for="item in SKIN_SITES" :key="item" class="chip site" @tap="startAnalyze(item)">
            {{ item }}
          </view>
        </view>
        <view class="btn ghost cancel" @tap="siteVisible = false">取消</view>
      </view>
    </view>

    <TabBar current="/pages/skin/index" />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow, onUnload } from '@dcloudio/uni-app'
import TabBar from '../../components/TabBar.vue'
import { formatMoment } from '../../shared/dates'
import { chooseImage, encodeJpeg } from '../../utils/image'
import { setSkinDraft } from '../../utils/skinDraft'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import {
  SKIN_SITES,
  analyze,
  listObservations,
  observationImageUrl,
  releaseBlobUrl
} from '../../services/skinService'
import type { SkinSummaryItem } from '../../services/types'

const latest = ref<SkinSummaryItem | null>(null)
const latestPhoto = ref<string | null>(null)
const total = ref(0)
const siteVisible = ref(false)
const analyzing = ref(false)

async function load() {
  try {
    const rows = await listObservations()
    total.value = rows.length
    latest.value = rows[0] ?? null
    releaseBlobUrl(latestPhoto.value)
    latestPhoto.value = null
    if (latest.value) {
      try {
        latestPhoto.value = await observationImageUrl(latest.value.id)
      } catch {
        // 取不到照片时留在占位图，不影响文字观察。
      }
    }
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    latest.value = null
    latestPhoto.value = null
    total.value = 0
  }
}

function openHistory() {
  uni.navigateTo({ url: '/pages/skin/history' })
}

async function startAnalyze(site: string) {
  siteVisible.value = false
  analyzing.value = true
  try {
    const path = await chooseImage()
    const encoded = await encodeJpeg(path)
    const analysis = await analyze({
      site,
      captured_at: new Date().toISOString(),
      mime: encoded.mime,
      image_base64: encoded.base64
    })
    setSkinDraft(analysis, site, encoded.previewUrl)
    uni.navigateTo({ url: '/pages/skin/result' })
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    const message =
      failure instanceof ApiRequestError ? failure.message : (failure as Error).message || '分析失败'
    uni.showModal({ title: '没有完成分析', content: message, showCancel: false })
  } finally {
    analyzing.value = false
  }
}

onShow(load)
onUnload(() => {
  releaseBlobUrl(latestPhoto.value)
  latestPhoto.value = null
})
</script>

<style scoped>
.skin-hero {
  padding-bottom: 18px;
}
.skin-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}
.sk-btn {
  flex: 1;
  height: 44px;
  font-size: 14px;
  letter-spacing: 0;
  gap: 6px;
  padding: 0 12px;
}
.sk-btn.busy {
  opacity: 0.6;
}
.skin-head {
  margin-top: 20px;
}
.mock {
  position: relative;
  height: 214px;
  border-radius: 10px;
  overflow: hidden;
  background: var(--photo-grad);
  display: flex;
  align-items: center;
  justify-content: center;
}
.mock-img {
  width: 100%;
  height: 100%;
  display: block;
}
.mock-time {
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
.mock-site {
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
.latest-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}
.latest-privacy {
  margin-left: auto;
  font-size: 12px;
  color: var(--ink-2);
}
.obs-block {
  margin-top: 12px;
}
.more {
  margin-top: 12px;
}
.obs-note {
  margin-top: 8px;
}
.empty-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 4px;
}
.empty-glyph {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 120px;
  margin-top: 8px;
  border-radius: 10px;
  border: 1.5px dashed #e7cdd6;
  background: linear-gradient(160deg, #fff8f4, #fff1ee);
}
.page-note {
  margin-top: 10px;
}
.tips {
  line-height: 1.8;
}
.tip-line {
  font-size: 12px;
  line-height: 19px;
  color: #7a4a55;
}
.site {
  height: 34px;
}
.cancel {
  margin-top: 16px;
  height: 44px;
  font-size: 14px;
}
</style>
