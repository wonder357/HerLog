<template>
  <view class="page">
    <view class="card">
      <view class="section-title">最近一次已保存观察</view>
      <view v-if="latest">
        <view class="latest-site">{{ latest.site }} · {{ formatMoment(latest.captured_at) }}</view>
        <view class="muted">{{ latest.visible }}</view>
      </view>
      <view v-else class="muted">还没有保存过观察。选好部位拍一张，确认结果后才会进入历史。</view>
      <button class="primary analyze-button" :disabled="analyzing" @tap="siteVisible = true">
        {{ analyzing ? '正在分析…' : '拍照分析' }}
      </button>
      <view class="link" @tap="openHistory">历史记录 ›</view>
    </view>

    <view class="card tips">
      <view class="section-title">说明</view>
      <view class="muted">· 照片只用于本次可见外观描述，不给病名、严重程度评分或改善百分比。</view>
      <view class="muted">· 点「保存」才会写入历史；不保存或重拍不会新增记录。</view>
      <view class="muted">· 判断不舒服或变化明显时，请线下就医。</view>
    </view>

    <view v-if="siteVisible">
      <view class="sheet-mask" @tap="siteVisible = false" />
      <view class="sheet">
        <view class="sheet-title">选择部位</view>
        <view class="sites">
          <view v-for="item in SKIN_SITES" :key="item" class="site" @tap="startAnalyze(item)">
            {{ item }}
          </view>
        </view>
        <view class="ghost cancel" @tap="siteVisible = false">取消</view>
      </view>
    </view>

    <TabBar current="/pages/skin/index" />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import TabBar from '../../components/TabBar.vue'
import { formatMoment } from '../../shared/dates'
import { chooseImage, encodeJpeg } from '../../utils/image'
import { setSkinDraft } from '../../utils/skinDraft'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import { SKIN_SITES, analyze, listObservations } from '../../services/skinService'
import type { SkinSummaryItem } from '../../services/types'

const latest = ref<SkinSummaryItem | null>(null)
const siteVisible = ref(false)
const analyzing = ref(false)

async function load() {
  try {
    const rows = await listObservations()
    latest.value = rows[0] ?? null
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    latest.value = null
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
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 12px 16px 76px;
  box-sizing: border-box;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
}
.latest-site {
  font-size: 14px;
  margin-bottom: 4px;
}
.analyze-button {
  margin-top: 14px;
}
.link {
  margin-top: 12px;
  text-align: center;
  color: #b4544a;
  font-size: 13px;
}
.tips {
  line-height: 1.8;
}
.sheet-title {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 14px;
}
.sites {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.site {
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid #e4d8d3;
  font-size: 14px;
  color: #4b413d;
}
.cancel {
  margin-top: 16px;
}
</style>
