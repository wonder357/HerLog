import { API_PREFIX, apiUrl } from '../config/runtime'
import { ApiRequestError, currentEpoch, expireSession, getToken, request, StaleSessionError } from './httpClient'
import type { AssistantAnswer } from './types'

export type AssistantTopic = Extract<AssistantAnswer['domain'], 'weight' | 'period' | 'skin'>
export type AssistantMode = 'general' | 'records'
export type AssistantSource = 'deepseek' | 'fixture' | 'records'
export interface AssistantExchange { question: string; answer: string }
export interface AssistantConversation { id: string; title: string; updated_at: string }
export interface SavedAssistantTurn {
  id: string
  question: string
  mode: AssistantMode
  topic: AssistantTopic | null
  source: AssistantSource | null
  status: 'pending' | 'complete' | 'failed' | 'stopped'
  answer: AssistantAnswer | null
  partial: string | null
  error: string | null
}
interface HistoryPage { items: AssistantConversation[]; next_cursor: string | null }
const assistantPath = '/herlog/assistant'
const conversationPath = assistantPath + '/conversations'
const specificConversation = (id: string) => conversationPath + '/' + encodeURIComponent(id)

export const getHistoryPreference = () => request<{ enabled: boolean | null }>(assistantPath + '/history-preference')
export const setHistoryPreference = (enabled: boolean) => request<{ enabled: boolean }>(assistantPath + '/history-preference', {
  method: 'PUT', data: { enabled }
})
export const listConversations = (q: string, cursor?: string) => q
  ? request<HistoryPage>(conversationPath + '/search', { method: 'POST', data: { q, ...(cursor ? { cursor } : {}) } })
  : request<HistoryPage>(conversationPath, { data: cursor ? { cursor } : undefined })
export const getConversation = (id: string) =>
  request<{ conversation: AssistantConversation; turns: SavedAssistantTurn[] }>(specificConversation(id))
export const renameConversation = (id: string, title: string) =>
  request<AssistantConversation>(specificConversation(id), { method: 'PUT', data: { title } })
export const removeConversation = (id: string) => request<null>(specificConversation(id), { method: 'DELETE' })

interface QuestionOptions {
  mode: AssistantMode
  history?: AssistantExchange[]
  topic?: AssistantTopic
  signal: AbortSignal
  save?: { conversation_id: string; client_turn_id: string; create_conversation: boolean }
  onAccepted?: (conversation: AssistantConversation) => void
  onSource: (source: AssistantSource) => void
  onDelta: (text: string) => void
}

type StreamEvent =
  | { type: 'accepted'; conversation: AssistantConversation }
  | { type: 'source'; source: AssistantSource }
  | { type: 'delta'; text: string }
  | { type: 'complete'; answer: AssistantAnswer }
  | { type: 'error'; message: string }

/** H5 用原生 fetch 消费 POST 事件流，uni.request 会等待完整响应。 */
export async function ask(question: string, options: QuestionOptions): Promise<AssistantAnswer> {
  const epoch = currentEpoch()
  const token = getToken()
  const checkSession = () => {
    if (currentEpoch() !== epoch) throw new StaleSessionError()
  }
  const response = await fetch(apiUrl(API_PREFIX + '/herlog/assistant/stream'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', ...(token ? { token } : {}) },
    signal: options.signal,
    cache: 'no-store',
    body: JSON.stringify({
      question,
      mode: options.mode,
      ...(options.mode === 'records' ? { follow_up_topic: options.topic } : { history: options.save ? undefined : options.history }),
      ...options.save
    })
  })
  checkSession()
  if (response.status === 401) expireSession()
  if (!response.ok || !response.body || !response.headers.get('content-type')?.includes('text/event-stream')) {
    const error = await response.json().catch(() => null)
    checkSession()
    throw new ApiRequestError(response.status, typeof error?.message === 'string' ? error.message : '暂时无法开始对话，请重试。')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      checkSession()
      buffer += decoder.decode(value, { stream: !done })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.startsWith('data:')) continue
        const event = JSON.parse(line.slice(5).trim()) as StreamEvent
        if (event.type === 'accepted') options.onAccepted?.(event.conversation)
        if (event.type === 'source') options.onSource(event.source)
        if (event.type === 'delta') options.onDelta(event.text)
        if (event.type === 'complete') return event.answer
        if (event.type === 'error') throw new ApiRequestError(502, event.message)
      }
      if (done) throw new ApiRequestError(502, '回答连接已断开，请重试。')
    }
  } finally {
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}
