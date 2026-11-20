<template>
  <section class="card agent-entry" aria-labelledby="agent-title">
    <header class="entry-header">
      <span class="agent-mark"><HerlogMascot pose="hi" :size="46" /></span>
      <div class="entry-copy">
        <h2 id="agent-title">她记小助手-小胭</h2>
        <p>聊日常健康，也能查个人记录</p>
      </div>
    </header>
    <H5Button class="entry-action" aria-label="开始对话 ›" aria-haspopup="dialog" @click="open()">
      <span>问问她记…</span><span class="entry-arrow"><HerlogIcon name="send" /></span>
    </H5Button>
    <div v-if="showQuestions" class="agent-chips home-chips" aria-label="查询个人记录">
      <H5Button v-for="question in examples" :key="question" class="agent-chip" @click="open(question)">
        {{ question }}
      </H5Button>
    </div>
  </section>

  <div v-if="opened" class="agent-workspace" :style="viewportStyle">
    <HerlogSheet :title="view === 'history' ? '历史对话' : '她记小助手-小胭'"
      :context="view === 'chat' && chatTitle ? chatTitle : undefined" @close="close">
      <div class="chat-toolbar">
        <template v-if="view === 'history'">
          <view class="chat-view-title">共 {{ chats.length }} 段对话</view>
          <H5Button class="hr-action" @click="view = 'chat'">返回对话</H5Button>
        </template>
        <template v-else>
          <div class="mode-switch" role="group" aria-label="提问方式">
            <H5Button v-for="item in modes" :key="item.value" class="mode-option"
              :aria-pressed="mode === item.value" :disabled="pending" @click="mode = item.value">{{ item.label }}</H5Button>
          </div>
          <div class="toolbar-actions">
            <H5Button class="hr-action" @click="openHistory">历史对话</H5Button>
            <H5Button class="hr-action" :disabled="pending || (!turns.length && !draft)" @click="newChat">新建对话</H5Button>
          </div>
        </template>
      </div>

      <template v-if="view === 'history'">
        <section class="chat-history" aria-label="历史对话列表">
          <view v-if="historyError" class="chat-alert" role="alert">{{ historyError }}
            <H5Button class="hr-action" @click="loadChats">重试</H5Button>
          </view>
          <view v-else-if="historyLoading" class="chat-muted" role="status">正在读取历史对话…</view>
          <view v-else-if="!chats.length" class="chat-muted">
            还没有保存的对话。问过第一个问题后，这段对话会自动出现在这里。
          </view>
          <ul v-else class="chat-list">
            <li v-for="item in chats" :key="item.id" class="chat-row">
              <view class="chat-row-main">
                <H5Button class="chat-open" :class="{ current: item.id === chatId }" @click="openChat(item.id)">
                  <strong>{{ item.title }}</strong>
                  <small>{{ formatMoment(item.updated_at) }} · {{ Math.ceil(item.message_count / 2) }} 轮对话</small>
                </H5Button>
                <H5Button class="hr-action" @click="startRename(item)">改名</H5Button>
                <H5Button class="hr-action danger" :disabled="removing" @click="removeChat(item)">删除</H5Button>
              </view>
              <view v-if="renamingId === item.id" class="chat-rename">
                <H5Input v-model="renameDraft" aria-label="对话标题" maxlength="60" placeholder="给这段对话起个名字" />
                <H5Button class="hr-action" :disabled="!renameDraft.trim() || renaming" @click="submitRename">保存</H5Button>
                <H5Button class="hr-action" @click="cancelRename">取消</H5Button>
              </view>
            </li>
          </ul>
        </section>
      </template>

      <template v-else>
      <section v-if="!turns.length" class="chat-welcome" aria-labelledby="chat-welcome-title">
        <HerlogMascot class="chat-art" pose="idle" :size="96" />
        <h3 id="chat-welcome-title">想聊些什么？</h3>
        <p>{{ mode === 'general' ? '可以聊日常护理，或问问怎样记录自己的健康变化。' : '可以查看已保存的经期、体重和皮肤记录。' }}</p>
      </section>

      <div class="messages" role="log" aria-label="智能体对话消息" aria-live="off">

        <template v-for="turn in turns" :key="turn.id">
          <div class="message user">
            <div class="message-content"><span class="speaker">你</span><p class="bubble">{{ turn.question }}</p></div>
          </div>
          <div class="message agent">
            <span class="agent-mark small"><HerlogIcon name="chat" /></span>
            <div class="message-content">
              <span class="speaker">{{ turn.source === 'deepseek' ? 'DeepSeek · AI 回答' : turn.source === 'fixture'
                ? '演示样例' : turn.source === 'records' ? '她记 · 记录摘要' : '她记' }}</span>
              <div v-if="turn.answer" class="bubble">
                <p>{{ turn.answer.answer }}</p>
                <small v-if="turn.answer.range.label !== '未指定范围' && !turn.answer.answer.includes(turn.answer.range.label)"
                  class="scope">{{ turn.answer.range.label }}</small>
                <details v-if="recordRefs(turn.answer).length" class="sources">
                  <summary>记录依据 · {{ recordRefs(turn.answer).length }} 条</summary>
                  <H5Button v-for="item in recordRefs(turn.answer)" :key="item.type + item.id" class="hr-action source"
                    @click="openReference(item)">{{ item.label }} ›</H5Button>
                </details>
                <div v-if="actionRefs(turn.answer).length" class="agent-chips">
                  <H5Button v-for="item in actionRefs(turn.answer)" :key="item.type + item.id" class="agent-chip"
                    @click="openReference(item)">{{ item.label }} ›</H5Button>
                </div>
              </div>
              <div v-else-if="turn.error" class="bubble">
                <p v-if="turn.partial">{{ turn.partial }}</p>
                <p class="failed" role="status">{{ turn.error }}</p>
                <H5Button class="hr-action" :disabled="pending" @click="requestAnswer(turn)">重试这条问题</H5Button>
              </div>
              <p v-else-if="turn.partial" class="bubble">{{ turn.partial }}<span class="stream-caret" aria-hidden="true" /></p>
              <p v-else class="bubble waiting" role="status">{{ turn.mode === 'records' ? '正在查看你的记录…' : '正在等待回答…' }}</p>
            </div>
          </div>
        </template>
      </div>

      <div v-if="suggestions.length" class="follow-up-block" :class="{ starters: !turns.length }">
        <span v-if="turns.length" class="follow-up-title">猜你想问</span>
        <div class="agent-chips follow-ups" aria-label="猜你想问的问题">
          <H5Button v-for="question in suggestions" :key="question" class="agent-chip" @click="chooseQuestion(question)">
            {{ question }}
          </H5Button>
        </div>
      </div>
      <div ref="tail" class="chat-tail" aria-hidden="true" />
      </template>
      <template #actions>
        <div v-if="view === 'chat'" class="composer-area">
          <H5Form class="composer" @submit.prevent="send">
            <H5Input ref="composerInput" v-model="draft" class="field" aria-label="问题"
              :placeholder="mode === 'records' ? '查一查已保存的记录…' : '输入想聊的问题…'"
              enterkeyhint="send" maxlength="300" autocomplete="off" @keydown.enter="guardComposition" />
            <H5Button v-if="pending" class="send stop" aria-label="停止生成" @click="stopGeneration"><span aria-hidden="true" /></H5Button>
            <H5Button v-else type="submit" class="send" :disabled="!draft.trim()" aria-label="发送问题"><HerlogIcon name="send" /></H5Button>
          </H5Form>
          <p class="composer-note">{{ mode === 'records'
            ? '仅查询本账号已保存的记录。'
            : '对话文字会发送给 DeepSeek，不读取账号记录。AI 回答仅供参考。' }}</p>
        </div>
      </template>
    </HerlogSheet>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import H5Form from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogIcon from '../../components/HerlogIcon.vue'
import HerlogMascot from '../../components/HerlogMascot.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { ask, deleteChat, getChat, listChats, renameChat } from '../../services/assistantService'
import type {
  AssistantChatSummary,
  AssistantMode,
  AssistantSource,
  AssistantTopic
} from '../../services/assistantService'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'
import { formatMoment } from '../../shared/dates'
import { suggestFollowUps } from '../../shared/followUps'
import type { AssistantAnswer, RecordRef } from '../../services/types'

const props = defineProps<{ examples: string[]; showQuestions: boolean }>()
const emit = defineEmits<{ reference: [item: RecordRef] }>()
interface Turn {
  id: number
  question: string
  mode: AssistantMode
  topic?: AssistantTopic
  source?: AssistantSource
  partial?: string
  answer?: AssistantAnswer
  error?: string
}

const opened = ref(false)
const view = ref<'chat' | 'history'>('chat')
const mode = ref<AssistantMode>('general')
const modes = [
  { value: 'general', label: '问助手' },
  { value: 'records', label: '查记录' }
] as const
const generalQuestions = ['怎么开始记录经期？', '怎样记录体重变化？', '肤质观察可以记哪些内容？']
const draft = ref('')
const turns = ref<Turn[]>([])
const chatId = ref<number | null>(null)
const chatTitle = ref('')
const chats = ref<AssistantChatSummary[]>([])
const historyLoading = ref(false)
const historyError = ref('')
const renamingId = ref<number | null>(null)
const renameDraft = ref('')
const renaming = ref(false)
const removing = ref(false)
const tail = ref<HTMLElement | null>(null)
const composerInput = ref<{ focus(): void } | null>(null)
const keyboardGap = ref(0)
const viewportHeight = ref(0)
let generation = 0
let nextId = 0
let viewport: VisualViewport | null = null
let running: { id: number; controller: AbortController } | null = null

const viewportStyle = computed(() => viewportHeight.value > 0 ? {
  '--chat-viewport': viewportHeight.value + 'px',
  '--chat-keyboard': keyboardGap.value + 'px'
} : undefined)
const pending = computed(() => turns.value.some(turn => !turn.error && !turn.answer))
const latestAnswer = computed(() => {
  for (let index = turns.value.length - 1; index >= 0; index -= 1) {
    const answer = turns.value[index].answer
    if (answer && turns.value[index].mode === 'records') return answer
  }
  return undefined
})
const topic = computed<AssistantTopic | undefined>(() => {
  const domain = latestAnswer.value?.domain
  return domain === 'weight' || domain === 'period' || domain === 'skin' ? domain : undefined
})
const suggestions = computed(() => {
  if (pending.value || !props.showQuestions) return []
  if (mode.value === 'general') {
    if (!turns.value.length) return generalQuestions
    const latest = [...turns.value].reverse().find(turn => turn.mode === 'general' && turn.answer)
    if (!latest?.answer) return []
    return suggestFollowUps({
      question: latest.question,
      answer: latest.answer.answer,
      asked: turns.value.map(turn => turn.question)
    })
  }
  if (!latestAnswer.value) return [...new Set([...props.examples, '最近的皮肤观察是什么？'])].slice(0, 3)
  if (topic.value === 'weight') return [latestAnswer.value?.range.days === 30 ? '那近 7 天呢？' : '那近 30 天呢？']
  if (topic.value === 'period') return [latestAnswer.value?.range.label === '最近一次实际经期' ? '那下次呢？' : '那上次呢？']
  return []
})

function scrollToTail() {
  void nextTick(() => {
    if (!opened.value) return
    const content = tail.value?.closest('.dialog-content')
    if (content) content.scrollTop = content.scrollHeight
  })
}

function updateViewport() {
  if (!viewport) return
  viewportHeight.value = Math.round(viewport.height)
  keyboardGap.value = Math.max(0, Math.round(window.innerHeight - viewport.height - viewport.offsetTop))
}

function stopViewport() {
  viewport?.removeEventListener('resize', updateViewport)
  viewport?.removeEventListener('scroll', updateViewport)
  viewport = null
  keyboardGap.value = viewportHeight.value = 0
}

watch(opened, visible => {
  if (!visible) {
    stopViewport()
    return
  }
  viewport = window.visualViewport
  viewport?.addEventListener('resize', updateViewport)
  viewport?.addEventListener('scroll', updateViewport)
  updateViewport()
  scrollToTail()
})

function open(question?: string) {
  if (question) {
    stopGeneration()
    mode.value = 'records'
    draft.value = question
  }
  view.value = 'chat'
  opened.value = true
}

function close() {
  stopGeneration()
  opened.value = false
  view.value = 'chat'
}

function newChat() {
  generation += 1
  running?.controller.abort()
  running = null
  turns.value = []
  draft.value = ''
  chatId.value = null
  chatTitle.value = ''
  view.value = 'chat'
  renamingId.value = null
  void nextTick(() => composerInput.value?.focus())
}

async function loadChats() {
  historyLoading.value = true
  historyError.value = ''
  try {
    chats.value = await listChats()
  } catch (failure) {
    historyError.value = failure instanceof ApiRequestError ? failure.message : '历史对话没有读取成功。'
  } finally {
    historyLoading.value = false
  }
}

function openHistory() {
  view.value = 'history'
  renamingId.value = null
  void loadChats()
}

async function syncChatTitle(id: number) {
  try {
    chats.value = await listChats()
  } catch {
    return
  }
  const current = chats.value.find(item => item.id === id)
  if (current && chatId.value === id) chatTitle.value = current.title
}

function toTurns(rows: { role: 'user' | 'assistant'; content: string; source: AssistantSource | null }[]): Turn[] {
  const result: Turn[] = []
  for (const row of rows) {
    if (row.role === 'user') {
      result.push({ id: ++nextId, question: row.content, mode: 'general' })
      continue
    }
    const last = result[result.length - 1]
    if (!last) continue
    last.source = row.source ?? 'deepseek'
    last.answer = {
      answer: row.content,
      domain: 'general',
      range: { label: '未指定范围', date_from: null, date_to: null, days: null },
      record_refs: [],
      model_id: null
    }
  }
  return result
}

async function openChat(id: number) {
  generation += 1
  running?.controller.abort()
  running = null
  historyError.value = ''
  try {
    const detail = await getChat(id)
    chatId.value = detail.id
    chatTitle.value = detail.title
    turns.value = toTurns(detail.messages)
    view.value = 'chat'
    renamingId.value = null
    scrollToTail()
  } catch (failure) {
    historyError.value = failure instanceof ApiRequestError ? failure.message : '这段对话没有读取成功。'
  }
}

function startRename(item: AssistantChatSummary) {
  renamingId.value = item.id
  renameDraft.value = item.title
}

function cancelRename() {
  renamingId.value = null
  renameDraft.value = ''
}

async function submitRename() {
  const id = renamingId.value
  const title = renameDraft.value.trim()
  if (id === null || !title || renaming.value) return
  renaming.value = true
  try {
    const updated = await renameChat(id, title)
    chats.value = chats.value.map(item => item.id === updated.id ? updated : item)
    if (chatId.value === updated.id) chatTitle.value = updated.title
    cancelRename()
  } catch (failure) {
    historyError.value = failure instanceof ApiRequestError ? failure.message : '标题没有保存成功。'
  } finally {
    renaming.value = false
  }
}

function removeChat(item: AssistantChatSummary) {
  uni.showModal({
    title: '删除对话',
    content: `删除「${item.title}」后不能恢复。`,
    confirmText: '删除',
    cancelText: '保留',
    success: (result) => {
      if (result.confirm) void doRemove(item)
    }
  })
}

async function doRemove(item: AssistantChatSummary) {
  removing.value = true
  try {
    await deleteChat(item.id)
    chats.value = chats.value.filter(chat => chat.id !== item.id)
    if (chatId.value === item.id) newChat()
  } catch (failure) {
    historyError.value = failure instanceof ApiRequestError ? failure.message : '删除没有成功，请重试。'
  } finally {
    removing.value = false
  }
}

function chooseQuestion(question: string) {
  draft.value = question
  composerInput.value?.focus()
}

function patchTurn(id: number, patch: Partial<Turn>) {
  turns.value = turns.value.map(turn => turn.id === id ? { ...turn, ...patch } : turn)
}

async function requestAnswer(turn: Turn) {
  if (running) return
  const session = currentEpoch()
  const sequence = generation
  const controller = new AbortController()
  running = { id: turn.id, controller }
  const active = () => session === currentEpoch() && sequence === generation && !controller.signal.aborted
  const history = turn.mode === 'general' ? turns.value
    .filter(item => item.id < turn.id && item.mode === 'general' && item.answer)
    .slice(-3)
    .map(item => ({ question: item.question, answer: item.answer!.answer.slice(0, 4000) })) : undefined
  patchTurn(turn.id, { error: undefined, partial: undefined, source: undefined })
  scrollToTail()
  let partial = ''
  try {
    const reply = await ask(turn.question, {
      mode: turn.mode, topic: turn.topic, chatId: chatId.value, history, signal: controller.signal,
      onSource(source) { if (active()) patchTurn(turn.id, { source }) },
      onDelta(text) {
        if (!active()) return
        partial += text
        patchTurn(turn.id, { partial })
        scrollToTail()
      }
    })
    if (active()) {
      patchTurn(turn.id, { answer: reply.answer, partial: undefined })
      if (reply.chatId !== null && reply.chatId !== chatId.value) {
        chatId.value = reply.chatId
        void syncChatTitle(reply.chatId)
      }
    }
  } catch (failure) {
    if (active()) patchTurn(turn.id, { error: failure instanceof ApiRequestError
      ? failure.message : '暂时没有收到回答，可以重试。' })
  } finally {
    if (running?.controller === controller) running = null
    if (active()) scrollToTail()
  }
}

function stopGeneration() {
  if (!running) return
  const { id, controller } = running
  running = null
  controller.abort()
  patchTurn(id, { error: '已停止生成。' })
}

function send() {
  const question = draft.value.trim()
  if (!question || pending.value) return
  const turn = { id: ++nextId, question, mode: mode.value, topic: mode.value === 'records' ? topic.value : undefined }
  turns.value = [...turns.value, turn]
  draft.value = ''
  void requestAnswer(turn)
}

function guardComposition(event: KeyboardEvent) {
  if (event.isComposing || event.keyCode === 229) event.preventDefault()
}

function actionRefs(answer: AssistantAnswer) {
  return answer.record_refs.filter(item => item.id === 'entry' || item.id === 'module')
}

function recordRefs(answer: AssistantAnswer) {
  return answer.record_refs.filter(item => item.id !== 'entry' && item.id !== 'module')
}

async function openReference(item: RecordRef) {
  close()
  await nextTick()
  emit('reference', item)
}

onBeforeUnmount(() => { generation += 1; running?.controller.abort(); stopViewport() })
defineExpose({ close })
</script>

<style scoped>
.agent-entry { padding:13px; background:linear-gradient(115deg,var(--hr-surface),var(--hr-rose-soft)); }
.entry-header { display:flex; align-items:center; gap:9px; min-width:0; }
.entry-copy { flex:1; min-width:0; }
.entry-copy h2 { margin:0; font-size:16px; line-height:1.35; }
.entry-copy p { margin:3px 0 0; color:var(--hr-ink-2); font-size:12px; }
.agent-mark { display:grid; place-items:center; width:46px; height:46px; flex:none; }
.agent-mark.small { width:32px; height:32px; border:1px solid var(--hr-line); border-radius:10px; color:var(--hr-rose-deep); background:var(--hr-rose-soft); }
.agent-mark.small svg { width:18px; height:18px; }
.entry-action { display:flex; align-items:center; justify-content:space-between; min-height:48px; width:100%; margin-top:10px; padding:5px 6px 5px 13px; border:1px solid var(--hr-line-strong); border-radius:24px; background:var(--hr-surface); color:var(--hr-ink-2); font-size:14px; }
.entry-arrow { display:grid; place-items:center; width:34px; height:34px; border-radius:50%; background:var(--hr-action-fill); color:white; }
.entry-arrow svg { width:18px; height:18px; }
.agent-chips { display:flex; flex-wrap:wrap; gap:6px; margin-top:7px; }
.agent-chip { min-height:44px; padding:5px 10px; max-width:100%; text-align:left; white-space:normal; overflow-wrap:anywhere; border:1px solid var(--hr-line-strong); border-radius:13px; color:var(--hr-rose-deep); background:var(--hr-surface); font-size:13px; }
.home-chips { margin-top:8px; }
.agent-workspace :deep(.dialog-panel) { bottom:var(--chat-keyboard,0px); height:var(--chat-viewport,100dvh); max-height:none; border-radius:0; }
.agent-workspace :deep(.dialog-grip) { display:none; }
.agent-workspace :deep(.dialog-header) { padding-top:max(10px,env(safe-area-inset-top)); }
.agent-workspace :deep(.dialog-content) { flex:1; background:var(--hr-paper); padding-top:0; }
.agent-workspace :deep(.dialog-actions) { flex:none; }
.chat-toolbar { position:sticky; top:0; z-index:1; display:flex; justify-content:space-between; align-items:center; gap:8px; min-height:48px; background:var(--hr-paper); border-bottom:1px solid var(--hr-line); margin-bottom:12px; }
.chat-toolbar .hr-action { padding-inline:0; font-size:13px; }
.toolbar-actions { display:flex; align-items:center; gap:10px; flex:none; }
.chat-view-title { color:var(--hr-ink-2); font-size:13px; }
.chat-history { display:grid; gap:8px; }
.chat-muted { color:var(--hr-ink-2); font-size:13px; line-height:1.55; }
.chat-alert { display:flex; align-items:center; gap:8px; padding:10px 12px; border-radius:13px; background:var(--hr-danger-soft); color:var(--hr-danger); font-size:13px; }
.chat-list { display:grid; gap:8px; margin:0; padding:0; list-style:none; }
.chat-row { display:grid; gap:6px; padding:10px 12px; border:1px solid var(--hr-line); border-radius:15px; background:var(--hr-surface); }
.chat-row-main { display:flex; align-items:center; gap:8px; min-width:0; }
.chat-open { flex:1; min-width:0; display:grid; gap:2px; padding:0; border:0; background:transparent; text-align:start; color:var(--hr-ink); }
.chat-open strong { font-size:14px; font-weight:600; overflow-wrap:anywhere; }
.chat-open small { color:var(--hr-ink-2); font-size:12px; }
.chat-open.current strong { color:var(--hr-rose-deep); }
.chat-rename { display:flex; align-items:center; gap:8px; }
.chat-rename :deep(.field) { flex:1; min-width:0; margin:0; }
.hr-action.danger { color:var(--hr-danger); }
.mode-switch { display:flex; gap:3px; padding:2px; border-radius:20px; background:var(--hr-paper-deep); }
.mode-option { min-height:44px; border:0; border-radius:18px; padding:5px 12px; color:var(--hr-ink-2); background:transparent; font-size:13px; }
.mode-option[aria-pressed='true'] { color:var(--hr-rose-deep); background:var(--hr-surface); font-weight:650; }
.chat-welcome { padding:16px 14px; border-radius:var(--hr-radius-lg); background:linear-gradient(135deg,var(--hr-rose-soft),var(--hr-peach)); }
.chat-welcome h3 { margin:2px 0 5px; font:650 26px/1.3 var(--hr-serif); color:var(--hr-ink); }
.chat-welcome p { max-width:24em; margin:0; color:var(--hr-ink-2); font-size:14px; }
.chat-art { margin-bottom:2px; }
.messages { display:grid; gap:12px; }
.message { display:flex; gap:7px; align-items:flex-start; }
.message.user { justify-content:flex-end; }
.message-content { min-width:0; max-width:min(90%,460px); }
.message.agent .message-content { max-width:calc(100% - 39px); }
.speaker { display:block; margin:0 0 3px 4px; color:var(--hr-ink-2); font-size:12px; }
.user .speaker { margin-right:5px; text-align:right; }
.bubble { margin:0; padding:9px 11px; border:1px solid var(--hr-line); border-radius:15px 15px 15px 5px; background:var(--hr-surface); font-size:14px; line-height:1.65; overflow-wrap:anywhere; white-space:pre-wrap; }
.bubble p { margin:0; }
.user .bubble { border-radius:15px 15px 5px 15px; color:var(--hr-ink); background:var(--hr-rose-soft); }
.waiting,.scope { color:var(--hr-ink-2); }
.scope { display:block; margin-top:7px; font-size:12px; }
.failed { color:var(--hr-danger); }
.stream-caret { display:inline-block; width:5px; height:1em; margin-inline-start:3px; vertical-align:text-bottom; border-radius:3px; background:var(--hr-rose); }
.sources { margin-top:6px; border-top:1px solid var(--hr-line); font-size:13px; }
.sources summary { color:var(--hr-rose-deep); min-height:44px; padding-top:10px; cursor:pointer; box-sizing:border-box; }
.source { display:flex; width:100%; justify-content:space-between; padding-inline:0; text-align:left; white-space:normal; font-size:13px; border-top:1px solid var(--hr-line); border-radius:0; }
.follow-up-block { display:grid; gap:6px; margin:10px 0 0 39px; }
.follow-up-block.starters { margin-left:0; }
.follow-up-title { color:var(--hr-rose-deep); font-size:12px; font-weight:600; }
.follow-ups { margin:0; }
.follow-ups.starters { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,142px),1fr)); }
.chat-tail { min-height:1px; }
.composer-area { width:100%; min-width:0; }
.composer { display:grid; grid-template-columns:minmax(0,1fr) 44px; align-items:center; gap:8px; }
.composer .field { margin:0; min-width:0; }
.send { display:grid; place-items:center; min-height:44px; background:var(--hr-action-fill); color:white; border:0; border-radius:50%; }
.send svg { width:20px; height:20px; }
.stop span { width:12px; height:12px; border-radius:3px; background:var(--hr-surface); }
.composer-note { margin:4px 0 0; color:var(--hr-ink-2); font-size:12px; }
</style>
