<template>
  <section class="card agent-entry" aria-labelledby="agent-title">
    <header class="entry-header">
      <span class="agent-mark"><HerlogIcon name="chat" /></span>
      <div class="entry-copy">
        <h2 id="agent-title">她记智能体</h2>
        <p>查经期、体重和皮肤记录</p>
      </div>
      <H5Button class="hr-action entry-action" aria-haspopup="dialog" @click="open()">开始对话 ›</H5Button>
    </header>
    <div v-if="showQuestions" class="agent-chips home-chips" aria-label="建议问题">
      <H5Button v-for="question in examples" :key="question" class="agent-chip" @click="open(question)">
        {{ question }}
      </H5Button>
    </div>
  </section>

  <div v-if="opened" class="agent-workspace" :style="viewportStyle">
    <HerlogSheet title="她记智能体" context="读取已保存的记录" @close="close">
      <div class="chat-toolbar">
        <span>本次对话</span>
        <H5Button v-if="turns.length || draft" class="hr-action" @click="newChat">新建对话</H5Button>
      </div>

      <div class="messages" role="log" aria-label="智能体对话消息" aria-live="polite" aria-relevant="additions text">
        <div class="message agent">
          <span class="agent-mark small"><HerlogIcon name="chat" /></span>
          <div class="message-content">
            <span class="speaker">她记</span>
            <p class="bubble">你好，可以问我最近的经期、体重或皮肤记录，也可以接着追问。</p>
          </div>
        </div>

        <template v-for="turn in turns" :key="turn.id">
          <div class="message user">
            <div class="message-content"><span class="speaker">你</span><p class="bubble">{{ turn.question }}</p></div>
          </div>
          <div class="message agent">
            <span class="agent-mark small"><HerlogIcon name="chat" /></span>
            <div class="message-content">
              <span class="speaker">她记</span>
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
              <div v-else-if="turn.error" class="bubble failed">
                <p role="status">{{ turn.error }}</p>
                <H5Button class="hr-action" :disabled="pending" @click="requestAnswer(turn)">重试这条问题</H5Button>
              </div>
              <p v-else class="bubble waiting" role="status">正在查看你的记录…</p>
            </div>
          </div>
        </template>
      </div>

      <div v-if="suggestions.length" class="agent-chips follow-ups" aria-label="建议追问">
        <H5Button v-for="question in suggestions" :key="question" class="agent-chip" @click="chooseQuestion(question)">
          {{ question }}
        </H5Button>
      </div>
      <div ref="tail" class="chat-tail" aria-hidden="true" />
      <template #actions>
        <div class="composer-area">
          <H5Form class="composer" @submit.prevent="send">
            <H5Input ref="composerInput" v-model="draft" class="field" aria-label="问题" placeholder="输入你想问的问题"
              enterkeyhint="send" maxlength="300" autocomplete="off" @keydown.enter="guardComposition" />
            <H5Button type="submit" class="send" :disabled="pending || !draft.trim()" aria-label="发送问题"><HerlogIcon name="send" /></H5Button>
          </H5Form>
          <p class="composer-note">仅本次会话 · 健康记录查询</p>
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
import HerlogSheet from '../../components/HerlogSheet.vue'
import { ask } from '../../services/assistantService'
import type { AssistantTopic } from '../../services/assistantService'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'
import type { AssistantAnswer, RecordRef } from '../../services/types'

const props = defineProps<{ examples: string[]; showQuestions: boolean }>()
const emit = defineEmits<{ reference: [item: RecordRef] }>()
interface Turn {
  id: number
  question: string
  topic?: AssistantTopic
  answer?: AssistantAnswer
  error?: string
}

const opened = ref(false)
const draft = ref('')
const turns = ref<Turn[]>([])
const tail = ref<HTMLElement | null>(null)
const composerInput = ref<{ focus(): void } | null>(null)
const keyboardGap = ref(0)
const viewportHeight = ref(0)
let generation = 0
let nextId = 0
let viewport: VisualViewport | null = null

const viewportStyle = computed(() => viewportHeight.value > 0 ? {
  '--chat-viewport': viewportHeight.value + 'px',
  '--chat-keyboard': keyboardGap.value + 'px'
} : undefined)
const pending = computed(() => turns.value.some(turn => !turn.error && !turn.answer))
const latestAnswer = computed(() => {
  for (let index = turns.value.length - 1; index >= 0; index -= 1) {
    const answer = turns.value[index].answer
    if (answer) return answer
  }
  return undefined
})
const topic = computed<AssistantTopic | undefined>(() => {
  const domain = latestAnswer.value?.domain
  return domain === 'weight' || domain === 'period' || domain === 'skin' ? domain : undefined
})
const suggestions = computed(() => {
  if (pending.value || !props.showQuestions) return []
  if (!turns.value.length) return [...new Set([...props.examples, '最近的皮肤观察是什么？'])].slice(0, 3)
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
  if (question) draft.value = question
  opened.value = true
}

function close() { opened.value = false }

function newChat() {
  generation += 1
  turns.value = []
  draft.value = ''
  void nextTick(() => composerInput.value?.focus())
}

function chooseQuestion(question: string) {
  draft.value = question
  composerInput.value?.focus()
}

function patchTurn(id: number, patch: Partial<Turn>) {
  turns.value = turns.value.map(turn => turn.id === id ? { ...turn, ...patch } : turn)
}

async function requestAnswer(turn: Turn) {
  if (pending.value && turn.error) return
  const session = currentEpoch()
  const sequence = generation
  const active = () => session === currentEpoch() && sequence === generation
  patchTurn(turn.id, { error: undefined })
  scrollToTail()
  try {
    const answer = await ask(turn.question, turn.topic)
    if (active()) patchTurn(turn.id, { answer })
  } catch (failure) {
    if (active()) patchTurn(turn.id, { error: failure instanceof ApiRequestError && failure.status === 422
      ? failure.message : '暂时没有收到回答，可以重试。' })
  } finally {
    if (active()) scrollToTail()
  }
}

function send() {
  const question = draft.value.trim()
  if (!question || pending.value) return
  const turn = { id: ++nextId, question, topic: topic.value }
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

onBeforeUnmount(() => { generation += 1; stopViewport() })
defineExpose({ close })
</script>

<style scoped>
.agent-entry { padding:10px 12px; background:linear-gradient(115deg,var(--hr-surface),var(--hr-rose-soft)); }
.entry-header { display:flex; align-items:center; gap:9px; min-width:0; }
.entry-copy { flex:1; min-width:0; }
.entry-copy h2 { margin:0; font-size:16px; line-height:1.35; }
.entry-copy p { margin:3px 0 0; color:var(--hr-ink-2); font-size:12px; }
.agent-mark { display:grid; place-items:center; width:40px; height:40px; flex:none; border:1px solid var(--hr-line); border-radius:13px; color:var(--hr-rose-deep); background:var(--hr-rose-soft); }
.agent-mark svg { width:22px; height:22px; }
.agent-mark.small { width:32px; height:32px; border-radius:10px; }
.agent-mark.small svg { width:18px; height:18px; }
.entry-action { flex:none; padding-inline:0; white-space:nowrap; font-size:13px; }
.agent-chips { display:flex; flex-wrap:wrap; gap:6px; margin-top:7px; }
.agent-chip { min-height:44px; padding:5px 10px; max-width:100%; text-align:left; white-space:normal; overflow-wrap:anywhere; border:1px solid var(--hr-line-strong); border-radius:13px; color:var(--hr-rose-deep); background:var(--hr-surface); font-size:13px; }
.home-chips { padding-top:4px; border-top:1px solid var(--hr-line); }
.agent-workspace :deep(.dialog-panel) { bottom:var(--chat-keyboard,0px); height:min(700px,calc(var(--chat-viewport,100dvh) - 12px)); max-height:none; }
.agent-workspace :deep(.dialog-content) { flex:1; background:var(--hr-paper); padding-top:2px; }
.agent-workspace :deep(.dialog-actions) { flex:none; }
.chat-toolbar { position:sticky; top:0; z-index:1; display:flex; justify-content:space-between; align-items:center; gap:8px; min-height:44px; color:var(--hr-ink-2); background:var(--hr-paper); border-bottom:1px solid var(--hr-line); margin-bottom:8px; font-size:12px; }
.chat-toolbar .hr-action { padding-inline:0; font-size:13px; }
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
.failed .hr-action { padding-inline:0; }
.sources { margin-top:6px; border-top:1px solid var(--hr-line); font-size:13px; }
.sources summary { color:var(--hr-rose-deep); min-height:44px; padding-top:10px; cursor:pointer; box-sizing:border-box; }
.source { display:flex; width:100%; justify-content:space-between; padding-inline:0; text-align:left; white-space:normal; font-size:13px; border-top:1px solid var(--hr-line); border-radius:0; }
.follow-ups { margin:10px 0 0 39px; }
.chat-tail { min-height:1px; }
.composer-area { width:100%; min-width:0; }
.composer { display:grid; grid-template-columns:minmax(0,1fr) 44px; align-items:center; gap:8px; }
.composer .field { margin:0; min-width:0; }
.send { display:grid; place-items:center; min-height:44px; background:var(--hr-action-fill); color:white; border:0; border-radius:50%; }
.send svg { width:20px; height:20px; }
.composer-note { margin:4px 0 0; color:var(--hr-ink-2); font-size:12px; }
</style>
