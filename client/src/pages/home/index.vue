<template>
  <view class="page">
    <view class="hero">
      <view class="h-date">{{ dateLine }}</view>
      <view class="h-title">今天</view>
      <view class="h-sub">{{ statusLine }}</view>

      <view class="quick">
        <view class="quick-item" @tap="openPeriodForm">
          <image class="qi-ic" src="/static/icons/period-berry.svg" mode="aspectFit" />
          <text class="qi-label">记经期</text>
        </view>
        <view class="quick-item" @tap="weightFormVisible = true">
          <image class="qi-ic" src="/static/icons/weight-berry.svg" mode="aspectFit" />
          <text class="qi-label">记体重</text>
        </view>
        <view class="quick-item" @tap="openSkinFlow">
          <image class="qi-ic" src="/static/icons/skin-berry.svg" mode="aspectFit" />
          <text class="qi-label">拍照分析</text>
        </view>
      </view>
    </view>

    <view class="main">
      <view class="chat">
        <view class="msg">
          <view class="bubble-wrap">
            <view class="bubble ai">
              我是她记。可以问我最近体重有什么变化、上次经期什么时候开始，回答只使用你已保存的记录。
            </view>
            <view v-if="messages.length === 0" class="example">
              <view class="chip" @tap="askExample('最近体重有什么变化？')">最近体重有什么变化？</view>
              <view class="chip" @tap="askExample('上次经期什么时候开始？')">上次经期什么时候开始？</view>
            </view>
          </view>
        </view>

        <view v-for="(message, index) in messages" :key="index" class="msg" :class="message.role">
          <view class="bubble-wrap">
            <view class="bubble" :class="message.role === 'user' ? 'me' : 'ai'">{{ message.text }}</view>
            <view v-if="message.rangeLabel" class="bubble-meta">{{ message.rangeLabel }}</view>
            <view v-if="message.refs && message.refs.length" class="refs">
              <view
                v-for="ref in message.refs"
                :key="`${ref.type}-${ref.id}`"
                class="ref"
                @tap="openRef(ref)"
              >
                {{ ref.label }} ›
              </view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <view class="composer">
      <input
        v-model="draft"
        class="composer-input"
        placeholder="问问她记：这周体重有什么变化？"
        placeholder-class="ph"
        confirm-type="send"
        @confirm="send"
      />
      <view class="send" :class="{ busy: sending }" @tap="send">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 14.5V4" />
          <path d="M4.6 8.2 9 3.8l4.4 4.4" />
        </svg>
      </view>
    </view>

    <WeightForm :visible="weightFormVisible" @close="weightFormVisible = false" @saved="onWeightSaved" />
    <PeriodForm
      :visible="periodFormVisible"
      :day="periodFormDay"
      :open-period="null"
      @close="periodFormVisible = false"
      @saved="onPeriodSaved"
    />
    <TabBar current="/pages/home/index" />
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import TabBar from '../../components/TabBar.vue'
import WeightForm from '../../components/WeightForm.vue'
import PeriodForm from '../../components/PeriodForm.vue'
import { formatDayLabel, todayString } from '../../shared/dates'
import { formatKg } from '../../shared/weight'
import { useAuthStore } from '../../stores/auth'
import { ask } from '../../services/assistantService'
import { getSummary } from '../../services/weightService'
import { getOverview } from '../../services/periodService'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import type { PeriodOverview, RecordRef, WeightSummary } from '../../services/types'

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  rangeLabel?: string
  refs?: RecordRef[]
}

const auth = useAuthStore()
const today = todayString()
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const sending = ref(false)
const weightFormVisible = ref(false)
const periodFormVisible = ref(false)
const periodFormDay = ref(today)
const overview = ref<PeriodOverview | null>(null)
const weight = ref<WeightSummary | null>(null)

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

const dateLine = computed(() => {
  const [year, month, date] = today.split('-').map(Number)
  const weekday = new Date(Date.UTC(year, month - 1, date)).getUTCDay()
  return `${year} 年 ${month} 月 ${date} 日 · 星期${WEEKDAYS[weekday]}`
})

// 页首副标题只描述已保存的事实，没有数据时给出去记录的方向。
const statusLine = computed(() => {
  const parts: string[] = []
  const status = overview.value?.status
  if (status?.in_period && status.message) {
    parts.push(status.message)
  }
  if (weight.value?.latest_grams !== null && weight.value?.latest_grams !== undefined) {
    parts.push(`最近体重 ${formatKg(weight.value.latest_grams)} kg`)
  }
  if (parts.length) {
    return parts.join(' · ')
  }
  return auth.username ? `${auth.username}，今天还没有记录` : '今天还没有记录，从记一笔开始'
})

onShow(() => {
  if (!auth.isLoggedIn) {
    uni.reLaunch({ url: '/pages/login/index' })
    return
  }
  loadContext()
})

// 切换账号时清掉本次会话内容，A 的问答不能留在 B 的页面上。
watch(
  () => auth.member?.customer_id,
  () => {
    messages.value = []
    draft.value = ''
    overview.value = null
    weight.value = null
  }
)

async function loadContext() {
  try {
    const results = await Promise.allSettled([getOverview(), getSummary(30)])
    const [periodResult, weightResult] = results
    if (periodResult.status === 'fulfilled') {
      overview.value = periodResult.value
    }
    if (weightResult.status === 'fulfilled') {
      weight.value = weightResult.value
    }
  } catch {
    // 页首摘要失败不影响对话，静默跳过。
  }
}

function openPeriodForm() {
  periodFormDay.value = todayString()
  periodFormVisible.value = true
}

function openSkinFlow() {
  uni.switchTab({ url: '/pages/skin/index' })
}

function onWeightSaved() {
  weightFormVisible.value = false
  loadContext()
  uni.showToast({ title: '已保存，可在体重页查看', icon: 'none' })
}

function onPeriodSaved() {
  periodFormVisible.value = false
  loadContext()
  uni.showToast({ title: '已保存，可在经期页查看', icon: 'none' })
}

function openRef(ref: RecordRef) {
  const path = ref.route
  if (path.startsWith('/pages/weight')) {
    uni.switchTab({ url: '/pages/weight/index' })
    return
  }
  if (path.startsWith('/pages/period')) {
    uni.switchTab({ url: '/pages/period/index' })
    return
  }
  if (path.startsWith('/pages/skin')) {
    uni.switchTab({ url: '/pages/skin/index' })
  }
}

function askExample(question: string) {
  draft.value = question
  send()
}

async function scrollToEnd() {
  await nextTick()
  uni.pageScrollTo({ scrollTop: 100000, duration: 200, fail: () => undefined })
}

async function send() {
  const question = draft.value.trim()
  if (!question || sending.value) {
    return
  }
  messages.value.push({ role: 'user', text: question })
  draft.value = ''
  sending.value = true
  await scrollToEnd()
  try {
    const answer = await ask(question)
    messages.value.push({
      role: 'assistant',
      text: answer.answer,
      rangeLabel: answer.range.label,
      refs: answer.record_refs
    })
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    messages.value.push({
      role: 'assistant',
      text: failure instanceof ApiRequestError ? failure.message : '回答失败，请稍后重试'
    })
  } finally {
    sending.value = false
    await scrollToEnd()
  }
}
</script>

<style scoped>
.quick {
  margin-top: 18px;
  display: flex;
  gap: 8px;
}
.quick-item {
  flex: 1;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 8px 12px;
  border-radius: 12px;
  background: var(--card-grad);
  border: 1px solid var(--card-line);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9), var(--card-shadow);
}
.qi-ic {
  width: 27px;
  height: 27px;
  display: block;
}
.qi-label {
  font-size: 13px;
  line-height: 18px;
  color: var(--ink);
  letter-spacing: 0.3px;
}
.chat {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 24px;
}
.msg {
  display: flex;
}
.msg.user {
  justify-content: flex-end;
}
.bubble-wrap {
  max-width: 306px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.msg.user .bubble-wrap {
  align-items: flex-end;
}
.bubble {
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 23px;
  box-sizing: border-box;
  word-break: break-word;
}
.bubble.ai {
  background: var(--surface);
  border: 1px solid var(--line);
  border-top-left-radius: 4px;
  color: var(--ink);
}
.bubble.me {
  background: var(--berry-soft);
  border-top-right-radius: 4px;
  color: #4a1b31;
}
.example {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.bubble-meta {
  margin-top: 6px;
  font-size: 12px;
  line-height: 18px;
  color: var(--ink-2);
}
.refs {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ref {
  font-size: 12px;
  line-height: 18px;
  color: var(--berry);
  background: var(--soft-grad);
  border-radius: 999px;
  padding: 3px 10px;
}
.composer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: calc(88px + env(safe-area-inset-bottom));
  z-index: 9;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px 12px;
  background: linear-gradient(180deg, rgba(253, 246, 241, 0) 0%, rgba(253, 246, 241, 0.92) 34%, #fdf6f1 100%);
}
.composer-input {
  flex: 1;
  height: 44px;
  min-height: 44px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--surface);
  padding: 0 16px;
  font-size: 14px;
  color: var(--ink);
  box-sizing: border-box;
  box-shadow: 0 8px 20px -16px rgba(156, 59, 80, 0.5);
}
.send {
  width: 44px;
  height: 44px;
  min-width: 44px;
  border-radius: 50%;
  background: var(--btn-grad);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 22px -10px var(--btn-shadow);
}
.send.busy {
  opacity: 0.6;
}
</style>
