<template>
  <view class="hr-page hr-tab-page home-page">
    <view class="greeting-banner">
      <HerlogHeading class="home-greeting" :title="auth.username ? `你好，${auth.username}` : '你好'" description="今天也留一点时间给自己。" />
      <image class="greeting-art" src="/static/home-cosmos.png" mode="aspectFit" aria-hidden="true" />
    </view>

    <RecordCalendar :key="auth.member?.customer_id" :today="today" :periods="overview?.items ?? null" :revision="calendarRevision" />

    <view class="shortcuts" aria-label="快捷记录">
      <H5Button class="shortcut" @click="openPeriodForm">
        <span class="shortcut-symbol"><HerlogIcon name="period" /></span><span>记经期</span>
      </H5Button>
      <H5Button class="shortcut weight" @click="weightFormVisible = true">
        <span class="shortcut-symbol"><HerlogIcon name="weight" /></span><span>记体重</span>
      </H5Button>
      <H5Button class="shortcut skin" @click="openSkinFlow">
        <span class="shortcut-symbol"><HerlogIcon name="skin" /></span><span>拍皮肤</span>
      </H5Button>
    </view>

    <section class="card snapshot" aria-label="记录摘要">
      <view><strong>{{ weightSummary?.latest_kg == null ? '—' : `${weightSummary.latest_kg} kg` }}</strong><text>最近体重</text></view>
      <view><strong>{{ weightSummary?.count ?? '—' }}</strong><text>近 7 天体重</text></view>
      <view><strong>{{ skinCount ?? '—' }}</strong><text>近 7 天皮肤</text></view>
    </section>
    <view v-if="overviewError" class="muted" role="status">部分记录暂未加载</view>

    <view class="chat">
      <view class="chat-heading">
        <h2 class="hr-section-title"><HerlogIcon name="message" />问问她记</h2>
        <text class="chat-scope">已保存的记录</text>
      </view>
      <view v-if="messages.length === 0" class="chat-intro">
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
    <PeriodForm :visible="periodFormVisible" :day="periodFormDay" :open-period="openPeriod" selectable-day
      @close="periodFormVisible = false" @saved="onPeriodSaved">
      <template #extra-action="{ day, disabled }">
        <H5Button class="ghost" :disabled="disabled || feelingLoading || !day || day > today" @click="openFeelingForm(day)">记感受</H5Button>
      </template>
    </PeriodForm>
    <FeelingForm :visible="feelingVisible" :day="feelingDay" :existing="existingFeeling" @close="feelingVisible = false" @saved="onFeelingSaved" />
    <TabBar current="/pages/home/index" />
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import H5Button from '../../components/H5Button'
import H5Form from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogIcon from '../../components/HerlogIcon.vue'
import TabBar from '../../components/TabBar.vue'
import WeightForm from '../../components/WeightForm.vue'
import PeriodForm from '../../components/PeriodForm.vue'
import FeelingForm from '../../components/FeelingForm.vue'
import RecordCalendar from './RecordCalendar.vue'
import { addDays, todayString } from '../../shared/dates'
import { useAuthStore } from '../../stores/auth'
import { ask } from '../../services/assistantService'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import { getOverview, listFeelings } from '../../services/periodService'
import { getSummary } from '../../services/weightService'
import { listObservations } from '../../services/skinService'
import type { FeelingItem, PeriodOverview, RecordRef, WeightSummary } from '../../services/types'

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  rangeLabel?: string
  refs?: RecordRef[]
}

const auth = useAuthStore()
const today = ref(todayString())
const calendarRevision = ref(0)
const overview = ref<PeriodOverview | null>(null)
const openPeriod = computed(() => {
  const item = overview.value?.items.find(item => !item.end_day)
  return item ? { id: item.id, startDay: item.start_day } : null
})
const weightSummary = ref<WeightSummary | null>(null)
const skinCount = ref<number | null>(null)
const overviewError = ref(false)
const feelingVisible = ref(false)
const feelingDay = ref(today.value)
const existingFeeling = ref<FeelingItem | null>(null)
const feelingLoading = ref(false)
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const sending = ref(false)
const chatEnd = ref<HTMLDivElement | null>(null)
const examples = ['最近体重有什么变化？', '下次经期大概是什么时候？']
const weightFormVisible = ref(false)
const periodFormVisible = ref(false)
const periodFormDay = ref(today.value)

onShow(() => {
  if (!auth.isLoggedIn) {
    uni.reLaunch({ url: '/pages/login/index' })
    return
  }
  today.value = todayString()
  calendarRevision.value++
  void loadOverview()
})

// 切换账号时清掉本次会话内容，A 的问答不能留在 B 的页面上。
watch(
  () => auth.member?.customer_id,
  () => {
    messages.value = []
    draft.value = ''
    overview.value = null
    weightSummary.value = null
    skinCount.value = null
    existingFeeling.value = null
    feelingVisible.value = false
    overviewError.value = false
  }
)

async function loadOverview() {
  const epoch = currentEpoch()
  const end = today.value
  const [period, weight, skin] = await Promise.allSettled([
    getOverview(), getSummary(7), listObservations({ from: addDays(end, -6), to: end })
  ])
  if (epoch !== currentEpoch()) return
  if (period.status === 'fulfilled') overview.value = period.value
  if (weight.status === 'fulfilled') weightSummary.value = weight.value
  if (skin.status === 'fulfilled') skinCount.value = skin.value.length
  overviewError.value = [period, weight, skin].some(result => result.status === 'rejected')
}

async function openFeelingForm(day: string) {
  if (feelingLoading.value) return
  const epoch = currentEpoch()
  feelingLoading.value = true
  try {
    const records = await listFeelings(day, day)
    if (epoch !== currentEpoch() || !periodFormVisible.value) return
    feelingDay.value = day
    existingFeeling.value = records.find(item => item.day === day) ?? null
    periodFormVisible.value = false
    feelingVisible.value = true
  } catch (failure) {
    if (epoch === currentEpoch()) uni.showToast({ title: failure instanceof ApiRequestError ? failure.message : '感受读取失败', icon: 'none' })
  } finally {
    feelingLoading.value = false
  }
}

function onFeelingSaved() {
  feelingVisible.value = false
  calendarRevision.value++
  uni.showToast({ title: '已保存', icon: 'none' })
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
  calendarRevision.value++
  void loadOverview()
  uni.showToast({ title: '已保存，可在体重页查看', icon: 'none' })
}

function onPeriodSaved() {
  periodFormVisible.value = false
  void loadOverview()
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
.home-greeting :deep(.hr-heading-copy) { grid-column: 1 / -1; text-align: left; }
.greeting-banner { position: relative; min-height: 58px; margin-bottom: 10px; padding: 12px min(30%, 116px) 10px 0; }
.home-greeting { margin-bottom: 0; }
.greeting-art { position: absolute; right: 0; top: 0; width: min(33%, 120px); height: 58px; pointer-events: none; }
@media (prefers-reduced-motion: no-preference) {
  .greeting-art { animation: greeting-in .7s ease-out both; }
}
@keyframes greeting-in {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
.snapshot { display: grid; text-align: center; }
.snapshot { grid-template-columns: repeat(3, minmax(0, 1fr)); box-sizing: border-box; min-height: 72px; align-items: center; padding: 8px 5px; }
.snapshot > * + * { border-left: 1px solid var(--hr-line); }
.snapshot strong { display: block; font: 19px var(--hr-font); }
.snapshot text, .snapshot uni-text { color: var(--hr-ink-2); font-size: 13px; font-weight: 600; }
.shortcuts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; margin: 0 0 12px; }
.shortcut {
  display: grid; justify-items: center; align-items: center; min-height: 72px; gap: 4px; padding: 7px 2px;
  border: 1px solid var(--hr-line); border-radius: var(--hr-radius); background: var(--hr-glass-fill);
  color: var(--hr-ink); box-shadow: var(--hr-glass-shadow); font-size: 13px; font-weight: 600;
}
.shortcut-symbol {
  display: grid; place-items: center; width: 42px; height: 37px; border-radius: 12px;
  background: var(--hr-rose-soft); color: var(--hr-rose-deep);
}
.shortcut.weight .shortcut-symbol { background: var(--hr-peach); color: var(--hr-peach-ink); }
.shortcut.skin .shortcut-symbol { background: var(--hr-plum-soft); color: var(--hr-plum); }
.shortcut-symbol svg { width: 22px; height: 22px; }
.chat-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 0 0 12px; }
.chat-heading h2 { display: flex; align-items: center; gap: 6px; margin: 0; }
.chat-heading h2 svg { width: 19px; height: 19px; color: var(--hr-rose-deep); }
.chat-scope { background: var(--hr-paper-deep); border-radius: 99px; color: var(--hr-ink-2); font-size: 12px; padding: 4px 9px; }
.chat-intro { padding: 14px; border-radius: var(--hr-radius); border: 1px solid var(--hr-line); background: var(--hr-surface); }
.examples, .refs { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.examples { margin-top: 0; }
.question, .ref {
  text-align: start; min-height: 44px; padding: 5px 10px; border: 1px solid var(--hr-line);
  box-sizing: border-box; min-width: 0; max-width: 100%; white-space: normal; overflow-wrap: anywhere;
  border-radius: 999px; background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-size: 13px;
}
.row { display: flex; flex-direction: column; margin-bottom: 12px; align-items: flex-start; }
.row.user { align-items: flex-end; }
.bubble {
  box-sizing: border-box; max-width: min(90%, 480px); padding: 10px 12px; white-space: pre-wrap; overflow-wrap: anywhere;
  border: 1px solid var(--hr-line); border-radius: 14px 14px 14px 4px; background: var(--hr-surface); font-size: 15px;
}
.row.user .bubble { color: var(--hr-rose-deep); background: var(--hr-rose-soft); border-radius: 14px 14px 4px 14px; }
.meta { max-width: 100%; margin-top: 5px; font-size: 12px; color: var(--hr-ink-2); overflow-wrap: anywhere; }
.chat-end { scroll-margin-bottom: calc(var(--hr-tab-height) + 86px + env(safe-area-inset-bottom)); }
.composer {
  display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 8px;
  position: fixed; z-index: 9; left: 50%; transform: translateX(-50%);
  bottom: calc(var(--hr-tab-height) + 8px + env(safe-area-inset-bottom)); width: min(calc(100% - 24px), var(--hr-shell-width));
  box-sizing: border-box; padding: 5px; border: 1px solid var(--hr-line); border-radius: 999px;
  background: var(--hr-surface); box-shadow: var(--hr-shadow);
}
.composer-input {
  box-sizing: border-box; width: 100%; min-height: 46px; min-width: 0; padding: 10px 13px;
  border: 0; border-radius: 999px; background: var(--hr-surface-strong);
  font: 16px var(--hr-font); color: var(--hr-ink);
}
.composer-input::placeholder { color: var(--hr-ink-3); }
.send {
  display: grid; place-items: center; width: 46px; height: 46px; padding: 0;
  border: 0; border-radius: 50%; background: var(--hr-action-fill); color: #fff;
}
.send svg { width: 22px; height: 22px; }
</style>
