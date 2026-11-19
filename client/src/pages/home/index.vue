<template>
  <view class="page">
    <view class="header">
      <view class="hello">你好，{{ auth.username || '她' }}</view>
      <view class="muted">今天 {{ formatDayLabel(today) }} · 记录一点点就够</view>
    </view>

    <view class="shortcuts">
      <view class="shortcut" @tap="openPeriodForm">
        <text class="circle">经</text>
        <text class="text">记经期</text>
      </view>
      <view class="shortcut" @tap="weightFormVisible = true">
        <text class="circle">重</text>
        <text class="text">记体重</text>
      </view>
      <view class="shortcut" @tap="openSkinFlow">
        <text class="circle">肤</text>
        <text class="text">拍照分析</text>
      </view>
    </view>

    <scroll-view class="chat" scroll-y :scroll-into-view="anchor">
      <view v-if="messages.length === 0" class="empty">
        <view class="empty-title">问我已保存的记录</view>
        <view class="muted">例如「这周体重有变化吗」「下次经期大概什么时候」</view>
        <view class="muted">对话只读，不会新增或修改记录。</view>
      </view>
      <view v-for="(message, index) in messages" :id="`m${index}`" :key="index" class="row" :class="message.role">
        <view class="bubble">{{ message.text }}</view>
        <view v-if="message.rangeLabel" class="meta">{{ message.rangeLabel }}</view>
        <view v-if="message.refs && message.refs.length" class="refs">
          <view v-for="ref in message.refs" :key="`${ref.type}-${ref.id}`" class="ref" @tap="openRef(ref)">
            {{ ref.label }} ›
          </view>
        </view>
      </view>
      <view id="anchor-end" />
    </scroll-view>

    <view class="composer">
      <input
        v-model="draft"
        class="composer-input"
        placeholder="问问体重、经期或皮肤记录…"
        confirm-type="send"
        @confirm="send"
      />
      <button class="send" :disabled="sending" @tap="send">{{ sending ? '…' : '发送' }}</button>
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
import { nextTick, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import TabBar from '../../components/TabBar.vue'
import WeightForm from '../../components/WeightForm.vue'
import PeriodForm from '../../components/PeriodForm.vue'
import { formatDayLabel, todayString } from '../../shared/dates'
import { useAuthStore } from '../../stores/auth'
import { ask } from '../../services/assistantService'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import type { RecordRef } from '../../services/types'

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
const anchor = ref('anchor-end')
const weightFormVisible = ref(false)
const periodFormVisible = ref(false)
const periodFormDay = ref(today)

onShow(() => {
  if (!auth.isLoggedIn) {
    uni.reLaunch({ url: '/pages/login/index' })
  }
})

// 切换账号时清掉本次会话内容，A 的问答不能留在 B 的页面上。
watch(
  () => auth.member?.customer_id,
  () => {
    messages.value = []
    draft.value = ''
  }
)

function openPeriodForm() {
  periodFormDay.value = todayString()
  periodFormVisible.value = true
}

function openSkinFlow() {
  uni.switchTab({ url: '/pages/skin/index' })
}

function onWeightSaved() {
  weightFormVisible.value = false
  uni.showToast({ title: '已保存，可在体重页查看', icon: 'none' })
}

function onPeriodSaved() {
  periodFormVisible.value = false
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

async function scrollToEnd() {
  anchor.value = ''
  await nextTick()
  anchor.value = 'anchor-end'
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
.page {
  min-height: 100vh;
  padding: 16px 16px 76px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}
.header {
  margin-bottom: 12px;
}
.hello {
  font-size: 20px;
  font-weight: 600;
}
.shortcuts {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.shortcut {
  flex: 1;
  background: #ffffff;
  border-radius: 16px;
  padding: 14px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.circle {
  width: 38px;
  height: 38px;
  line-height: 38px;
  text-align: center;
  border-radius: 50%;
  background: #fdf2ef;
  color: #b4544a;
  font-size: 15px;
}
.text {
  font-size: 13px;
  color: #4b413d;
}
.chat {
  flex: 1;
  min-height: 240px;
  padding-bottom: 8px;
}
.empty {
  padding: 26px 8px;
  text-align: center;
  line-height: 1.8;
}
.empty-title {
  font-size: 15px;
  margin-bottom: 6px;
}
.row {
  display: flex;
  flex-direction: column;
  margin-bottom: 12px;
}
.row.user {
  align-items: flex-end;
}
.row.assistant {
  align-items: flex-start;
}
.bubble {
  max-width: 84%;
  padding: 10px 12px;
  border-radius: 14px;
  line-height: 1.6;
  font-size: 14px;
  background: #ffffff;
}
.row.user .bubble {
  background: #b4544a;
  color: #ffffff;
}
.meta {
  margin-top: 4px;
  font-size: 11px;
  color: #a89d98;
}
.refs {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ref {
  font-size: 12px;
  color: #b4544a;
  background: #fdf2ef;
  border-radius: 999px;
  padding: 4px 10px;
}
.composer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 58px;
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: #fdf8f6;
  border-top: 1px solid #f0e6e2;
}
.composer-input {
  flex: 1;
  height: 38px;
  background: #ffffff;
  border-radius: 999px;
  padding: 0 14px;
  font-size: 14px;
}
.send {
  width: 66px;
  height: 38px;
  line-height: 38px;
  font-size: 14px;
  border-radius: 999px;
  background: #b4544a;
  color: #ffffff;
  padding: 0;
}
.send[disabled] {
  opacity: 0.6;
}
</style>
