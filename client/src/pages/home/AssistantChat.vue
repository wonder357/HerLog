<template>
  <section class="assistant-home" :class="{ keyboard }" :style="viewportStyle" aria-label="她记助手">
    <header class="assistant-header">
      <H5Button class="icon-button" aria-label="历史对话" aria-haspopup="dialog" @click="historyOpen = true">
        <HerlogIcon name="history" />
      </H5Button>
      <div class="assistant-brand">
        <H5Button v-if="chat" class="thread-title" :aria-label="'管理当前对话标题，' + chat.title"
          aria-haspopup="dialog" :disabled="pending && !chat.confirmed && chat.canSave" @click="manageCurrent">
          <span>{{ chat.title }}</span><i aria-hidden="true" />
        </H5Button>
        <template v-else><h1>她记助手</h1><span>HerLog</span></template>
      </div>
      <H5Button class="icon-button new-button" aria-label="新建对话" @click="newChat"><HerlogIcon name="plus" /></H5Button>
    </header>

    <div ref="workspace" class="assistant-workspace">
      <div v-if="opening" class="chat-alert" role="status">正在打开对话…</div>
      <div v-else-if="openError" class="chat-alert" role="alert">
        <span>{{ openError }}</span>
        <H5Button v-if="lastHistory" class="hr-action" @click="openHistoryChat(lastHistory)">重试</H5Button>
        <H5Button class="hr-action" @click="openError = ''">关闭</H5Button>
      </div>
      <div v-if="!chat" class="welcome">
        <section class="welcome-panel" aria-labelledby="chat-welcome-title">
          <img class="welcome-bloom" src="/static/home-cosmos.png" alt="" />
          <HerlogMascot class="welcome-mascot" pose="hi" :size="72" />
          <div class="welcome-copy">
            <p class="welcome-date">{{ dateLabel }}</p>
            <h2 id="chat-welcome-title">今天，<br />想聊点什么？</h2>
            <p>{{ mode === 'records' ? '查经期、体重和皮肤记录。' : '聊聊日常健康，回看记录。' }}</p>
          </div>
        </section>
        <section v-if="suggestions.length" class="question-panel" aria-labelledby="assistant-starter-title">
          <h2 id="assistant-starter-title">可以这样问</h2>
          <H5Button v-for="question in suggestions" :key="question" class="starter" @click="chooseQuestion(question)">
            <HerlogIcon name="sparkle" /><span>{{ question }}</span><i aria-hidden="true" />
          </H5Button>
        </section>
        <slot name="shortcuts" />
      </div>
      <div v-else class="messages" role="log" aria-label="智能体对话消息" aria-live="off">
        <template v-for="turn in chat.turns" :key="turn.id">
          <div class="message user">
            <p class="bubble">{{ turn.question }}</p>
          </div>
          <div class="message agent">
            <span class="agent-mark"><HerlogIcon name="sparkle" /></span>
            <div class="message-content">
              <div class="speaker">她记助手 <small v-if="turn.source">{{ sources[turn.source] }}</small></div>
              <div v-if="turn.answer" class="bubble">
                <p>{{ turn.answer.answer }}</p>
                <small v-if="turn.answer.range.label !== '未指定范围' && !turn.answer.answer.includes(turn.answer.range.label)"
                  class="scope">{{ turn.answer.range.label }}</small>
                <details v-if="recordRefs(turn.answer).length" class="sources">
                  <summary>记录依据 · {{ recordRefs(turn.answer).length }} 条</summary>
                  <H5Button v-for="item in recordRefs(turn.answer)" :key="item.type + item.id" class="hr-action source"
                    @click="emit('reference', item)">{{ item.label }} ›</H5Button>
                </details>
                <div v-if="actionRefs(turn.answer).length" class="agent-chips">
                  <H5Button v-for="item in actionRefs(turn.answer)" :key="item.type + item.id" class="agent-chip"
                    @click="emit('reference', item)">{{ item.label }} ›</H5Button>
                </div>
              </div>
              <div v-else-if="turn.error" class="bubble">
                <p v-if="turn.partial">{{ turn.partial }}</p>
                <p class="failed">{{ turn.error }}</p>
                <H5Button class="hr-action retry-turn" :disabled="pending || opening" @click="requestAnswer(turn)">重试这条问题</H5Button>
              </div>
              <p v-else-if="turn.partial" class="bubble">{{ turn.partial }}<span class="stream-caret" aria-hidden="true" /></p>
              <p v-else class="bubble waiting">{{ turn.mode === 'records' ? '正在查看你的记录…' : '正在等待回答…' }}</p>
            </div>
          </div>
        </template>
        <div v-if="suggestions.length" class="agent-chips follow-ups">
          <H5Button v-for="question in suggestions" :key="question" class="agent-chip" @click="chooseQuestion(question)">{{ question }}</H5Button>
        </div>
      </div>
    </div>

    <div class="assistant-footer">
      <div class="composer-toolbar">
        <H5Button class="records-mode" :aria-pressed="mode === 'records'" :disabled="pending || opening"
          @click="mode = mode === 'general' ? 'records' : 'general'"><HerlogIcon name="note" />查记录</H5Button>
        <span class="composer-source"><HerlogIcon :name="mode === 'records' ? 'note' : 'sparkle'" />{{ mode === 'records' ? '本人记录' : 'DeepSeek' }}</span>
      </div>
      <H5Form class="composer" @submit.prevent="send">
        <H5Input ref="composerInput" v-model="draft" class="question-input" aria-label="问题"
          :placeholder="mode === 'records' ? '输入想查的记录' : '输入想聊的问题'" :disabled="opening"
          enterkeyhint="send" maxlength="300" autocomplete="off" @keydown.enter="guardComposition" />
        <H5Button v-if="pending" class="send stop" aria-label="停止生成" @click="stopGeneration"><span aria-hidden="true" /></H5Button>
        <H5Button v-else type="submit" class="send" :disabled="!draft.trim() || opening" aria-label="发送问题"><HerlogIcon name="send" /></H5Button>
      </H5Form>
      <p class="composer-note">{{ mode === 'records' ? '仅查询本人记录 · 不写入健康数据' : '对话文字将发给 DeepSeek · AI 回答仅供参考' }}</p>
      <p class="sr-status" role="status" aria-live="polite">{{ status }}</p>
    </div>

    <AssistantHistory v-if="historyOpen" :active-id="chat?.confirmed ? chat.id : undefined"
      @close="historyOpen = false" @new-chat="newChat" @settings="openHistorySettings"
      @open="openHistoryChat" @manage="openHistoryMenu" />

    <HerlogSheet v-if="panel === 'preference'" title="保存对话历史？" :busy="savingPreference" @close="closePanel">
      <p class="sheet-copy">开启后，对话会保存在你的账号，可从历史继续。暂不保存时，本次对话只保留在当前使用期间。</p>
      <p v-if="panelError" class="error" role="alert">{{ panelError }}</p>
      <template #actions>
        <H5Button class="ghost" :disabled="savingPreference" @click="changePreference(false)">暂不保存</H5Button>
        <H5Button class="primary" :disabled="savingPreference" @click="changePreference(true)">保存到历史</H5Button>
      </template>
    </HerlogSheet>

    <HerlogSheet v-if="panel === 'historySettings'" title="对话保存设置" :busy="savingPreference" @close="closePanel">
      <p class="sheet-copy">开启后，新对话可在账号内同步。关闭后已保存的历史可继续查看和删除。</p>
      <p class="sheet-copy">当前设置 · {{ preference === true ? '保存新对话' : preference === false ? '暂不保存' : '尚未选择' }}</p>
      <p v-if="panelError" class="error" role="alert">{{ panelError }}</p>
      <template #actions>
        <H5Button class="ghost" :disabled="savingPreference" @click="changePreference(false)">暂不保存</H5Button>
        <H5Button class="primary" :disabled="savingPreference" @click="changePreference(true)">开启保存</H5Button>
      </template>
    </HerlogSheet>

    <HerlogSheet v-if="panel === 'switch'" title="正在生成回答" @close="closePanel">
      <p class="sheet-copy">停止后可切换对话，已经收到的文字会保留在这条对话中。</p>
      <template #actions>
        <H5Button class="ghost" @click="closePanel">继续等待</H5Button>
        <H5Button class="primary" @click="confirmSwitch">停止后切换</H5Button>
      </template>
    </HerlogSheet>

    <HerlogSheet v-if="panel === 'manage' && target" title="管理对话" :context="target.title" @close="closePanel">
      <div class="chat-menu">
        <H5Button class="ghost" @click="editTitle">编辑标题</H5Button>
        <H5Button class="ghost" @click="panel = 'delete'">删除对话</H5Button>
      </div>
    </HerlogSheet>

    <HerlogSheet v-if="panel === 'rename'" title="编辑对话标题" :busy="mutating" @close="closePanel">
      <H5Form id="assistant-title-form" @submit.prevent="saveTitle">
        <H5Label for="assistant-title-input" class="hr-field-label">对话标题</H5Label>
        <H5Input id="assistant-title-input" v-model="titleDraft" class="field" maxlength="24" :disabled="mutating" />
        <p class="title-note">可以用主题命名，避免填写个人信息。{{ titleDraft.length }} / 24</p>
        <p v-if="panelError" class="error" role="alert">{{ panelError }}</p>
      </H5Form>
      <template #actions>
        <H5Button class="ghost" :disabled="mutating" @click="closePanel">取消</H5Button>
        <H5Button form="assistant-title-form" type="submit" class="primary" :disabled="mutating">保存标题</H5Button>
      </template>
    </HerlogSheet>

    <HerlogSheet v-if="panel === 'delete' && target" title="删除这条对话？" :busy="mutating" @close="closePanel">
      <p class="sheet-copy">这会删除「{{ target.title }}」及其中的消息。已保存的健康记录会保留。</p>
      <p v-if="panelError" class="error" role="alert">{{ panelError }}</p>
      <template #actions>
        <H5Button class="ghost" :disabled="mutating" @click="closePanel">取消</H5Button>
        <H5Button class="primary" :disabled="mutating" @click="deleteChat">确认删除</H5Button>
      </template>
    </HerlogSheet>
  </section>
</template>


<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import H5Button from '../../components/H5Button'
import H5Form, { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogIcon from '../../components/HerlogIcon.vue'
import HerlogMascot from '../../components/HerlogMascot.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import AssistantHistory from './AssistantHistory.vue'
import { ask, getConversation, getHistoryPreference, removeConversation, renameConversation, setHistoryPreference } from '../../services/assistantService'
import type { AssistantConversation, AssistantMode, AssistantSource, AssistantTopic, SavedAssistantTurn } from '../../services/assistantService'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'
import type { AssistantAnswer, RecordRef } from '../../services/types'
import { assistantTitle } from '../../shared/home'
import { suggestFollowUps } from '../../shared/followUps'

const props = defineProps<{ dateLabel: string; starters: string[]; recordQuestions: string[]; showQuestions: boolean; visible: boolean }>()
const emit = defineEmits<{ reference: [item: RecordRef]; keyboard: [open: boolean] }>()
interface Turn {
  id: string
  question: string
  mode: AssistantMode
  topic?: AssistantTopic
  source?: AssistantSource
  partial?: string
  answer?: AssistantAnswer
  error?: string
}
type Drafts = Record<AssistantMode, string>
interface Chat { id: string; title: string; canSave: boolean; confirmed: boolean; turns: Turn[]; drafts: Drafts }
type Panel = 'preference' | 'historySettings' | 'switch' | 'manage' | 'rename' | 'delete'
const sources: Record<AssistantSource, string> = { deepseek: 'DeepSeek', records: '记录摘要', fixture: '演示样例' }
const workspace = ref<HTMLElement | null>(null)
const composerInput = ref<{ focus(): void } | null>(null)
const chat = ref<Chat | null>(null)
const mode = ref<AssistantMode>('general')
const emptyDrafts = (): Drafts => ({ general: '', records: '' })
const welcomeDrafts = ref(emptyDrafts())
const resume = new Map<string, { drafts: Drafts; mode: AssistantMode; scroll: number }>()
const preference = ref<boolean | null>(null)
const historyOpen = ref(false)
const panel = ref<Panel | null>(null)
const panelError = ref('')
const savingPreference = ref(false)
const mutating = ref(false)
const target = ref<{ id: string; title: string; saved: boolean } | null>(null)
const titleDraft = ref('')
const opening = ref(false)
const openError = ref('')
const lastHistory = ref<AssistantConversation | null>(null)
const status = ref('')
const keyboard = ref(false)
const keyboardHeight = ref(0)
const running = shallowRef<{ turnId: string; controller: AbortController } | null>(null)
let viewport: VisualViewport | null = null
let beforeSwitch: (() => void) | null = null
let reopenDrawer = false
let historyRequest = 0
let preferenceRequest = 0
let alive = true
const epoch = currentEpoch()
const inSession = () => alive && currentEpoch() === epoch
const pending = computed(() => Boolean(running.value))
const viewportStyle = computed(() => keyboard.value && keyboardHeight.value ? { height: keyboardHeight.value + 'px' } : undefined)
const drafts = computed(() => chat.value?.drafts ?? welcomeDrafts.value)
const draft = computed({ get: () => drafts.value[mode.value], set: value => { drafts.value[mode.value] = value } })
const latestRecordAnswer = computed(() => chat.value?.turns.filter(turn => turn.mode === 'records' && turn.answer).at(-1)?.answer)
const topic = computed<AssistantTopic | undefined>(() => {
  const domain = latestRecordAnswer.value?.domain
  return domain === 'weight' || domain === 'period' || domain === 'skin' ? domain : undefined
})
const suggestions = computed(() => {
  if (pending.value || !props.showQuestions) return []
  if (mode.value === 'general') {
    const general = chat.value?.turns.filter(turn => turn.mode === 'general') ?? []
    const latest = general.at(-1)
    if (!latest) return props.starters.slice(0, 2)
    return latest.answer ? suggestFollowUps({
      question: latest.question,
      answer: latest.answer.answer,
      asked: general.map(turn => turn.question)
    }, 2) : []
  }
  if (!latestRecordAnswer.value) return [...new Set([...props.recordQuestions, '最近的皮肤观察是什么？'])].slice(0, 2)
  if (topic.value === 'weight') return [latestRecordAnswer.value.range.days === 30 ? '那近 7 天呢？' : '那近 30 天呢？']
  if (topic.value === 'period') return [latestRecordAnswer.value.range.label === '最近一次实际经期' ? '那下次呢？' : '那上次呢？']
  return []
})

function id() {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('')
}

function scrollTo(y: number | 'tail') {
  void nextTick(() => {
    if (!props.visible || !workspace.value) return
    workspace.value.scrollTop = y === 'tail' ? workspace.value.scrollHeight : y
  })
}

function updateViewport() {
  const gap = viewport ? window.innerHeight - viewport.height : 0
  const open = Boolean(props.visible && viewport && viewport.scale === 1 && gap > 110)
  keyboard.value = open
  keyboardHeight.value = open && viewport ? Math.round(viewport.height) : 0
  emit('keyboard', open)
}

onMounted(() => {
  viewport = window.visualViewport
  viewport?.addEventListener('resize', updateViewport)
  viewport?.addEventListener('scroll', updateViewport)
  const request = ++preferenceRequest
  void getHistoryPreference().then(value => {
    if (inSession() && request === preferenceRequest) preference.value = value.enabled
  }).catch(() => undefined)
})
watch(() => props.visible, visible => {
  updateViewport()
  if (!visible) suspend()
})
onBeforeUnmount(() => {
  alive = false
  viewport?.removeEventListener('resize', updateViewport)
  viewport?.removeEventListener('scroll', updateViewport)
  running.value?.controller.abort()
  resume.clear()
})

function closePanel() {
  panel.value = null
  panelError.value = ''
  target.value = null
  beforeSwitch = null
  if (reopenDrawer && props.visible) historyOpen.value = true
  reopenDrawer = false
}

function suspend() {
  reopenDrawer = false
  historyOpen.value = false
  closePanel()
}
defineExpose({ suspend })

function openHistorySettings() {
  historyOpen.value = false
  reopenDrawer = true
  panelError.value = ''
  panel.value = 'historySettings'
}

async function changePreference(enabled: boolean) {
  if (savingPreference.value) return
  const firstSend = panel.value === 'preference'
  const panelBefore = panel.value
  preferenceRequest += 1
  savingPreference.value = true
  panelError.value = ''
  try {
    const result = await setHistoryPreference(enabled)
    if (!inSession()) return
    preference.value = result.enabled
    if (!enabled && chat.value) chat.value.canSave = false
    if (panel.value === panelBefore) {
      closePanel()
      if (firstSend && props.visible) send()
    }
  } catch {
    if (!inSession() || panel.value !== panelBefore) return
    if (!enabled && firstSend) {
      closePanel()
      startTurn(false)
    } else {
      panelError.value = '设置暂未保存，请重试。'
    }
  } finally {
    if (inSession()) savingPreference.value = false
  }
}

function chooseQuestion(question: string) {
  if (draft.value.trim() && draft.value !== question) {
    uni.showToast({ title: '已保留当前草稿', icon: 'none' })
  } else {
    draft.value = question
  }
  void nextTick(() => composerInput.value?.focus())
}

function guardComposition(event: KeyboardEvent) {
  if (event.isComposing || event.keyCode === 229) event.preventDefault()
}

function send() {
  if (!draft.value.trim() || pending.value || opening.value || !inSession()) return
  if (!chat.value && preference.value === null) {
    panelError.value = ''
    panel.value = 'preference'
    return
  }
  startTurn(preference.value === true)
}

function startTurn(canSave: boolean) {
  const question = draft.value.trim()
  if (!question || pending.value) return
  if (!chat.value) {
    chat.value = { id: id(), title: assistantTitle(question, mode.value), canSave, confirmed: false, turns: [], drafts: welcomeDrafts.value }
    welcomeDrafts.value = emptyDrafts()
  }
  const turn: Turn = { id: id(), question, mode: mode.value, topic: mode.value === 'records' ? topic.value : undefined }
  chat.value.turns.push(turn)
  draft.value = ''
  void requestAnswer(turn)
}

async function requestAnswer(turn: Turn) {
  const owner = chat.value
  if (pending.value || !owner || opening.value) return
  const item = owner.turns.find(entry => entry.id === turn.id)
  if (!item) return
  const attempt = { turnId: turn.id, controller: new AbortController() }
  running.value = attempt
  const active = () => inSession() && chat.value?.id === owner.id && running.value === attempt
  const index = owner.turns.indexOf(item)
  const history = turn.mode === 'general' ? owner.turns.slice(0, index)
    .filter(entry => entry.mode === 'general' && entry.answer)
    .slice(-3).map(entry => ({ question: entry.question, answer: entry.answer!.answer.slice(0, 4000) })) : undefined
  const save = owner.canSave && preference.value === true ? {
    conversation_id: owner.id, client_turn_id: item.id, create_conversation: !owner.confirmed,
  } : undefined
  item.error = item.partial = item.source = undefined
  status.value = '正在等待回答'
  scrollTo('tail')
  try {
    const answer = await ask(item.question, {
      mode: item.mode, topic: item.topic, history, save, signal: attempt.controller.signal,
      onAccepted(conversation) {
        if (!active()) return
        if (!owner.confirmed) owner.title = conversation.title
        owner.confirmed = true
      },
      onSource(source) { if (active()) item.source = source },
      onDelta(text) {
        if (!active()) return
        const area = workspace.value
        const nearEnd = !area || area.scrollHeight - area.scrollTop - area.clientHeight < 84
        item.partial = (item.partial ?? '') + text
        if (nearEnd) scrollTo('tail')
      }
    })
    if (active()) {
      item.answer = answer
      item.partial = undefined
      status.value = '回答已完成'
    }
  } catch (failure) {
    if (!active()) return
    item.error = failure instanceof ApiRequestError ? failure.message : '暂时没有收到回答，可以重试。'
    status.value = item.error
    if (failure instanceof ApiRequestError && failure.status === 409 && failure.message.includes('关闭保存历史')) {
      owner.canSave = false
      preference.value = false
    }
  } finally {
    if (running.value === attempt) running.value = null
  }
}

function stopGeneration() {
  const attempt = running.value
  if (!attempt) return
  const item = chat.value?.turns.find(turn => turn.id === attempt.turnId)
  running.value = null
  attempt.controller.abort()
  if (item) item.error = '已停止生成。'
  status.value = '已停止生成'
}

function remember() {
  if (!chat.value?.confirmed) return
  resume.set(chat.value.id, { drafts: chat.value.drafts, mode: mode.value, scroll: workspace.value?.scrollTop ?? 0 })
}

function switchWhenReady(action: () => void) {
  const fromHistory = historyOpen.value
  historyOpen.value = false
  if (!pending.value) {
    action()
    return
  }
  reopenDrawer = fromHistory
  beforeSwitch = action
  panel.value = 'switch'
}

function confirmSwitch() {
  const action = beforeSwitch
  reopenDrawer = false
  closePanel()
  stopGeneration()
  action?.()
}

function resetChat() {
  historyRequest += 1
  opening.value = false
  openError.value = ''
  lastHistory.value = null
  chat.value = null
  mode.value = 'general'
  welcomeDrafts.value = emptyDrafts()
  scrollTo(0)
}

function newChat() {
  switchWhenReady(() => {
    if (chat.value || opening.value) {
      remember()
      resetChat()
    }
    void nextTick(() => composerInput.value?.focus())
  })
}

function fromSaved(turn: SavedAssistantTurn): Turn {
  return {
    id: turn.id, question: turn.question, mode: turn.mode, topic: turn.topic ?? undefined,
    source: turn.source ?? undefined, answer: turn.answer ?? undefined, partial: turn.partial ?? undefined,
    error: turn.answer ? undefined : turn.error ?? '上次回答未完成，可以重试。'
  }
}

function openHistoryChat(row: AssistantConversation) {
  if (row.id === chat.value?.id && chat.value.confirmed && !opening.value) {
    historyOpen.value = false
    return
  }
  switchWhenReady(() => { void loadChat(row) })
}

async function loadChat(row: AssistantConversation) {
  const sequence = ++historyRequest
  const active = () => inSession() && sequence === historyRequest
  opening.value = true
  openError.value = ''
  lastHistory.value = row
  try {
    const result = await getConversation(row.id)
    if (!active()) return
    remember()
    const previous = resume.get(row.id)
    chat.value = {
      id: row.id, title: result.conversation.title, canSave: preference.value === true, confirmed: true,
      turns: result.turns.map(fromSaved), drafts: previous?.drafts ?? emptyDrafts(),
    }
    mode.value = previous?.mode ?? chat.value.turns.at(-1)?.mode ?? 'general'
    scrollTo(previous?.scroll ?? 'tail')
  } catch (failure) {
    if (active()) openError.value = failure instanceof ApiRequestError ? failure.message : '暂时无法打开这条对话。'
  } finally {
    if (active()) opening.value = false
  }
}

function manageCurrent() {
  const active = chat.value
  if (!active) return
  target.value = { id: active.id, title: active.title, saved: active.confirmed }
  reopenDrawer = false
  panelError.value = ''
  panel.value = 'manage'
}

function openHistoryMenu(row: AssistantConversation) {
  historyOpen.value = false
  reopenDrawer = true
  target.value = { id: row.id, title: row.title, saved: true }
  panelError.value = ''
  panel.value = 'manage'
}

function editTitle() {
  titleDraft.value = target.value?.title ?? ''
  panel.value = 'rename'
}

async function saveTitle() {
  const row = target.value
  const title = titleDraft.value.trim()
  if (!row || mutating.value) return
  if (!title || title.length > 24) {
    panelError.value = '请输入 1–24 个字符的对话标题。'
    return
  }
  mutating.value = true
  panelError.value = ''
  try {
    const savedTitle = row.saved ? (await renameConversation(row.id, title)).title : title
    if (!inSession()) return
    if (chat.value?.id === row.id) chat.value.title = savedTitle
    closePanel()
    uni.showToast({ title: '标题已更新', icon: 'none' })
  } catch (failure) {
    if (inSession()) panelError.value = failure instanceof ApiRequestError ? failure.message : '标题暂未保存，请重试。'
  } finally {
    if (inSession()) mutating.value = false
  }
}

async function deleteChat() {
  const row = target.value
  if (!row || mutating.value) return
  mutating.value = true
  panelError.value = ''
  try {
    if (row.saved) await removeConversation(row.id)
    if (!inSession()) return
    if (chat.value?.id === row.id) {
      stopGeneration()
      resetChat()
    }
    resume.delete(row.id)
    closePanel()
    uni.showToast({ title: '对话已删除', icon: 'none' })
  } catch (failure) {
    if (inSession()) panelError.value = failure instanceof ApiRequestError ? failure.message : '对话暂未删除，请重试。'
  } finally {
    if (inSession()) mutating.value = false
  }
}

const recordRefs = (answer: AssistantAnswer) => answer.record_refs.filter(ref => ref.id !== 'entry' && ref.id !== 'module')
const actionRefs = (answer: AssistantAnswer) => answer.record_refs.filter(ref => ref.id === 'entry' || ref.id === 'module')
</script>


<style scoped>
.assistant-home { display:grid; grid-template-rows:auto minmax(0,1fr) auto; width:min(100%, var(--hr-shell-width)); height:100vh; height:100dvh; min-width:0; margin:0 auto; padding-bottom:calc(var(--hr-tab-height) + 6px + env(safe-area-inset-bottom)); box-sizing:border-box; }
.assistant-home.keyboard { padding-bottom:env(safe-area-inset-bottom); }
.assistant-header { display:grid; grid-template-columns:44px minmax(0,1fr) 44px; gap:8px; align-items:center; min-height:72px; padding:max(9px, env(safe-area-inset-top)) 17px 9px; border-bottom:1px solid var(--hr-line); background:#fff9f5d9; }
.icon-button { display:grid; place-items:center; width:44px; height:44px; padding:0; border:1px solid var(--hr-line); border-radius:14px; background:var(--hr-surface); color:var(--hr-rose-deep); }
.icon-button svg { width:21px; height:21px; }
.new-button { background:var(--hr-rose-soft); }
.assistant-brand { min-width:0; text-align:center; }
.assistant-brand h1 { margin:0; font:750 18px/1.25 var(--hr-font); letter-spacing:.035em; }
.assistant-brand > span { display:block; color:var(--hr-ink-2); font:12px/1.4 Georgia,serif; letter-spacing:.09em; }
.thread-title { display:flex; justify-content:center; align-items:center; gap:7px; margin:auto; max-width:100%; min-height:44px; border:0; border-radius:9px; background:transparent; color:var(--hr-ink); font:700 16px var(--hr-font); }
.thread-title span { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.thread-title i { flex:0 0 5px; height:5px; border:solid var(--hr-ink-2); border-width:0 1.5px 1.5px 0; transform:rotate(45deg); margin-top:-3px; }
.assistant-workspace { min-height:0; overflow:auto; overscroll-behavior:contain; scrollbar-width:thin; scroll-padding-block:10px; }
.welcome { display:grid; gap:14px; padding:12px 17px 15px; }
.welcome-panel { position:relative; isolation:isolate; min-height:207px; overflow:hidden; border:1px solid var(--hr-line-strong); border-radius:22px; background:radial-gradient(ellipse at 93% 23%, var(--hr-rose-soft), transparent 68%), linear-gradient(115deg, var(--hr-peach), var(--hr-rose-soft)); }
.welcome-panel::after { position:absolute; z-index:-1; inset:0; content:''; background:linear-gradient(90deg, var(--hr-peach), transparent 72%); }
.welcome-bloom { position:absolute; z-index:-2; right:-77px; bottom:-18px; width:317px; opacity:.95; pointer-events:none; }
.welcome-mascot { position:absolute; right:12px; top:8px; }
.welcome-copy { padding:19px 0 15px 16px; max-width:59%; }
.welcome-copy h2 { margin:7px 0; font:750 clamp(27px, 8vw, 34px)/1.22 "Songti SC","SimSun",serif; letter-spacing:-.055em; }
.welcome-copy p { margin:0; color:var(--hr-ink-2); font-size:13px; line-height:1.55; }
.welcome-copy p:last-child { max-width:165px; }
.welcome-copy .welcome-date { color:var(--hr-rose-deep); font-size:12px; font-weight:650; }
.question-panel { display:grid; gap:6px; }
.question-panel h2 { margin:0 0 2px; font:700 15px var(--hr-font); }
.starter { display:grid; grid-template-columns:16px minmax(0,1fr) 8px; align-items:center; gap:7px; width:100%; min-height:44px; padding:5px 10px; text-align:left; border:1px solid var(--hr-line); border-radius:12px; background:var(--hr-surface); color:var(--hr-ink); font:13px/1.4 var(--hr-font); }
.starter svg { width:15px; height:15px; color:var(--hr-plum); }
.starter i { width:5px; height:5px; border:solid var(--hr-ink-2); border-width:1px 1px 0 0; transform:rotate(45deg); }
.assistant-footer { padding:1px 17px 6px; background:#fff9f6; border-top:1px solid var(--hr-line); }
.composer-toolbar { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.records-mode { min-height:44px; padding:0 7px 0 3px; display:inline-flex; align-items:center; gap:5px; border:0; border-radius:9px; background:transparent; color:var(--hr-ink-2); font:650 13px var(--hr-font); }
.records-mode[aria-pressed='true'] { color:var(--hr-plum); background:var(--hr-plum-soft); }
.records-mode svg { width:16px; height:16px; color:var(--hr-rose-deep); }
.composer-source { display:inline-flex; align-items:center; gap:4px; padding:3px 8px; border-radius:99px; background:var(--hr-plum-soft); color:var(--hr-plum); font-size:11px; }
.composer-source svg { width:13px; height:13px; }
.composer { display:flex; align-items:center; min-height:53px; padding:3px 4px 3px 10px; border:1px solid var(--hr-line-strong); border-radius:23px; background:var(--hr-surface); box-shadow:var(--hr-shadow); gap:5px; }
.composer:focus-within { border-color:var(--hr-rose); box-shadow:0 0 0 2px var(--hr-rose-soft); }
.question-input { flex:1; width:0; min-width:0; min-height:44px; border:0; padding:6px 3px; outline:0; background:transparent; color:var(--hr-ink); font:16px var(--hr-font); }
.question-input::placeholder { color:var(--hr-ink-2); }
.send { display:grid; place-items:center; width:44px; height:44px; padding:0; border:0; border-radius:16px; background:var(--hr-rose); color:var(--hr-surface); }
.send svg { width:20px; height:20px; }
.send:disabled { background:var(--hr-paper-deep); color:var(--hr-ink-2); }
.send.stop { background:var(--hr-plum); }
.send.stop span { width:11px; height:11px; border-radius:2px; background:currentColor; }
.composer-note { margin:5px 0 0; text-align:center; color:var(--hr-ink-2); font:11px/1.5 var(--hr-font); }
.sr-status { position:absolute; width:1px; height:1px; margin:0; clip-path:inset(50%); overflow:hidden; white-space:nowrap; }
.messages { display:grid; gap:13px; padding:13px 17px 15px; }
.message { min-width:0; }
.message.user { display:flex; justify-content:flex-end; }
.message.agent { display:grid; grid-template-columns:28px minmax(0,1fr); align-items:start; gap:7px; margin-bottom:4px; }
.agent-mark { display:grid; place-items:center; width:28px; height:28px; border-radius:9px; background:var(--hr-plum-soft); color:var(--hr-plum); }
.agent-mark svg { width:15px; height:15px; }
.message-content { min-width:0; }
.speaker { display:flex; flex-wrap:wrap; align-items:center; gap:5px; min-height:26px; margin-bottom:5px; font:650 12px var(--hr-font); }
.speaker small { padding:2px 5px; border-radius:6px; color:var(--hr-plum); background:var(--hr-plum-soft); font:650 11px var(--hr-font); }
.bubble { min-width:0; margin:0; padding:10px 11px; overflow-wrap:anywhere; white-space:pre-wrap; border:1px solid var(--hr-line); border-radius:5px 14px 14px 14px; background:var(--hr-surface); color:var(--hr-ink); font:14px/1.65 var(--hr-font); }
.bubble p { margin:0; }
.user .bubble { max-width:88%; border:0; border-radius:14px 14px 5px 14px; background:var(--hr-rose-soft); }
.waiting,.scope,.sources { color:var(--hr-ink-2); font-size:13px; }
.scope { display:block; margin-top:5px; }
.sources { margin-top:5px; }
.sources summary { cursor:pointer; min-height:44px; padding-block:9px; }
.source { display:flex; justify-content:flex-start; text-align:start; width:100%; }
.agent-chips { display:flex; flex-wrap:wrap; gap:5px; margin-top:5px; }
.agent-chip { min-height:44px; padding:5px 8px; border:1px solid var(--hr-line-strong); border-radius:10px; background:var(--hr-surface); color:var(--hr-plum); font:13px var(--hr-font); }
.failed { color:var(--hr-danger); }
.retry-turn { padding-inline:0; }
.stream-caret { display:inline-block; width:4px; height:12px; border-radius:2px; margin-left:3px; background:var(--hr-rose); animation:pulse 1s ease-in-out infinite alternate; }
@keyframes pulse { to { opacity:.35; } }
@media (prefers-reduced-motion: reduce) { .stream-caret { animation:none; } }
.chat-alert { display:flex; flex-wrap:wrap; align-items:center; gap:5px; margin:8px 17px 0; padding:5px 8px; background:var(--hr-peach); border-radius:10px; color:var(--hr-ink-2); font-size:13px; }
.sheet-copy,.title-note { margin:5px 0; color:var(--hr-ink-2); font-size:14px; line-height:1.55; }
.title-note { font-size:12px; }
.chat-menu { display:grid; gap:7px; }
@media (max-width:375px) {
  .welcome,.messages { padding-inline:13px; }
  .assistant-header,.assistant-footer { padding-inline:13px; }
  .welcome-panel { min-height:183px; }
  .welcome-bloom { width:278px; right:-71px; }
}
</style>
