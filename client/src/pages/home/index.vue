<template>
  <view class="hr-page hr-tab-page home-page">
    <HerlogHeading title="今天" :eyebrow="dateLabel" :description="auth.username ? '你好，' + auth.username : undefined" />

    <view class="shortcuts" aria-label="快捷记录">
      <H5Button class="shortcut" @click="openPeriodForm">
        <span class="shortcut-symbol"><HerlogIcon name="period" /></span><span>记经期</span>
      </H5Button>
      <H5Button class="shortcut weight" @click="weightFormVisible = true">
        <span class="shortcut-symbol"><HerlogIcon name="weight" /></span><span>记体重</span>
      </H5Button>
      <H5Button class="shortcut skin" @click="openSkinFlow">
        <span class="shortcut-symbol"><HerlogIcon name="skin" /></span><span>拍照分析</span>
      </H5Button>
    </view>

    <view class="chat">
      <view class="chat-heading">
        <h2 class="hr-section-title">问问她记</h2>
        <text class="chat-scope">已保存的记录</text>
      </view>
      <view v-if="messages.length === 0" class="chat-intro">
        <view class="intro-copy">想回看最近的体重、经期或皮肤记录？可以从一个问题开始。</view>
        <view class="muted">对话只读，保存记录请使用上方的快捷入口。</view>
        <view class="examples">
          <H5Button v-for="question in examples" :key="question" class="question" @click="draft = question">
            {{ question }}
          </H5Button>
        </view>
      </view>
      <view class="chat-feed" aria-live="polite">
        <view v-for="(message, index) in messages" :key="index" class="row" :class="message.role">
          <view class="bubble">{{ message.text }}</view>
          <view v-if="message.rangeLabel" class="meta">{{ message.rangeLabel }}</view>
          <view v-if="message.refs?.length" class="refs">
            <H5Button v-for="ref in message.refs" :key="`${ref.type}-${ref.id}`" class="ref" @click="openRef(ref)">
              {{ ref.label }} ›
            </H5Button>
          </view>
        </view>
        <view v-if="sending" class="muted" role="status">正在读取记录…</view>
        <div ref="chatEnd" class="chat-end" />
      </view>
    </view>

    <H5Form class="composer" @submit.prevent="send">
      <H5Input v-model="draft" class="composer-input" aria-label="问题" placeholder="问问我的健康记录…" @keydown.enter="onComposerEnter" />
      <H5Button type="submit" class="send" :disabled="sending || !draft.trim()" aria-label="发送问题">
        <HerlogIcon name="send" />
      </H5Button>
    </H5Form>

    <WeightForm :visible="weightFormVisible" @close="weightFormVisible = false" @saved="onWeightSaved" />
    <PeriodForm :visible="periodFormVisible" :day="periodFormDay" :open-period="null"
      @close="periodFormVisible = false" @saved="onPeriodSaved" />
    <TabBar current="/pages/home/index" />
  </view>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import H5Button from '../../components/H5Button'
import H5Form from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogIcon from '../../components/HerlogIcon.vue'
import TabBar from '../../components/TabBar.vue'
import WeightForm from '../../components/WeightForm.vue'
import PeriodForm from '../../components/PeriodForm.vue'
import { todayString } from '../../shared/dates'
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
const chatEnd = ref<HTMLDivElement | null>(null)
const dateLabel = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai', year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
}).format(new Date(today + 'T00:00:00+08:00'))
const examples = ['最近体重有什么变化？', '下次经期大概是什么时候？']
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

function onComposerEnter(event: KeyboardEvent) {
  if (event.isComposing || event.keyCode === 229) event.preventDefault()
}

async function scrollToEnd() {
  await nextTick()
  chatEnd.value?.scrollIntoView({ block: 'nearest' })
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
.home-page { padding-bottom: calc(var(--hr-tab-height) + 92px + env(safe-area-inset-bottom)); }
.shortcuts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 0 0 24px; }
.shortcut {
  display: grid; justify-items: center; align-items: center; min-height: 82px; gap: 4px; padding: 9px 4px;
  border: 1px solid var(--hr-line); border-radius: 16px; background: var(--hr-surface);
  color: var(--hr-ink); box-shadow: var(--hr-shadow); font-size: 14px; font-weight: 600;
}
.shortcut-symbol {
  display: grid; place-items: center; width: 42px; height: 37px; border-radius: 12px;
  background: var(--hr-rose-soft); color: var(--hr-rose-deep);
}
.shortcut.weight .shortcut-symbol { background: var(--hr-peach); color: var(--hr-peach-ink); }
.shortcut.skin .shortcut-symbol { background: var(--hr-plum-soft); color: var(--hr-plum); }
.shortcut-symbol svg { width: 22px; height: 22px; }
.chat-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 0 0 12px; }
.chat-heading h2 { margin: 0; }
.chat-scope { background: var(--hr-paper-deep); border-radius: 99px; color: var(--hr-ink-2); font-size: 12px; padding: 4px 9px; }
.chat-intro { padding: 14px; border-radius: var(--hr-radius); border: 1px solid var(--hr-line); background: var(--hr-surface); }
.intro-copy { font-size: 15px; margin-bottom: 5px; }
.examples, .refs { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.question, .ref {
  text-align: start; min-height: 44px; padding: 5px 10px; border: 1px solid var(--hr-line);
  border-radius: 11px; background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-size: 13px;
}
.row { display: flex; flex-direction: column; margin-bottom: 12px; align-items: flex-start; }
.row.user { align-items: flex-end; }
.bubble {
  box-sizing: border-box; max-width: min(90%, 480px); padding: 10px 12px; white-space: pre-wrap; overflow-wrap: anywhere;
  border: 1px solid var(--hr-line); border-radius: 14px 14px 14px 4px; background: var(--hr-surface); font-size: 15px;
}
.row.user .bubble { color: var(--hr-rose-deep); background: var(--hr-rose-soft); border-radius: 14px 14px 4px 14px; }
.meta { margin-top: 5px; font-size: 12px; color: var(--hr-ink-2); }
.chat-end { scroll-margin-bottom: calc(var(--hr-tab-height) + 86px + env(safe-area-inset-bottom)); }
.composer {
  display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 8px;
  position: fixed; z-index: 9; left: 50%; transform: translateX(-50%);
  bottom: calc(var(--hr-tab-height) + env(safe-area-inset-bottom)); width: min(100%, calc(var(--hr-shell-width) + 32px));
  box-sizing: border-box; padding: 10px 12px; border-top: 1px solid var(--hr-line); background: var(--hr-surface);
}
.composer-input {
  box-sizing: border-box; width: 100%; min-height: 46px; min-width: 0; padding: 10px 13px;
  border: 1px solid var(--hr-line-strong); border-radius: 999px; background: var(--hr-surface-strong);
  font: 16px var(--hr-font); color: var(--hr-ink);
}
.composer-input::placeholder { color: var(--hr-ink-3); }
.send {
  display: grid; place-items: center; width: 46px; height: 46px; padding: 0;
  border: 0; border-radius: 50%; background: var(--hr-rose); color: #fff;
}
.send svg { width: 22px; height: 22px; }
</style>
