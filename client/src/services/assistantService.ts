import { API_PREFIX, apiUrl } from '../config/runtime'
import { ApiRequestError, currentEpoch, expireSession, getToken, request, StaleSessionError } from './httpClient'
import type { AssistantAnswer } from './types'

export type AssistantTopic = Extract<AssistantAnswer['domain'], 'weight' | 'period' | 'skin'>
export type AssistantMode = 'general' | 'records'
export type AssistantSource = 'deepseek' | 'fixture' | 'records'
export interface AssistantExchange { question: string; answer: string }

export interface AssistantChatSummary {
  id: number
  title: string
  message_count: number
  updated_at: string
}

export interface AssistantChatMessage {
  role: 'user' | 'assistant'
  content: string
  source: AssistantSource | null
}

export interface AssistantChatDetail {
  id: number
  title: string
  updated_at: string
  messages: AssistantChatMessage[]
}

export interface AssistantReply {
  answer: AssistantAnswer
  chatId: number | null
}

interface QuestionOptions {
  mode: AssistantMode
  history?: AssistantExchange[]
  topic?: AssistantTopic
  chatId?: number | null
  signal: AbortSignal
  onSource: (source: AssistantSource) => void
  onDelta: (text: string) => void
}

type StreamEvent =
  | { type: 'source'; source: AssistantSource }
  | { type: 'delta'; text: string }
  | { type: 'complete'; answer: AssistantAnswer; chat_id: number | null }
  | { type: 'error'; message: string }

/** 对话历史：列表、详情、改名、删除。 */
export function listChats(): Promise<AssistantChatSummary[]> {
  return request<AssistantChatSummary[]>('/herlog/assistant/chats')
}

export function getChat(id: number): Promise<AssistantChatDetail> {
  return request<AssistantChatDetail>(`/herlog/assistant/chats/${id}`)
}

export function renameChat(id: number, title: string): Promise<AssistantChatSummary> {
  return request<AssistantChatSummary>(`/herlog/assistant/chats/${id}`, { method: 'PATCH', data: { title } })
}

export function deleteChat(id: number): Promise<null> {
  return request<null>(`/herlog/assistant/chats/${id}`, { method: 'DELETE' })
}

/** H5 用原生 fetch 消费 POST 事件流，uni.request 会等待完整响应。 */
export async function ask(question: string, options: QuestionOptions): Promise<AssistantReply> {
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
      ...(options.chatId ? { chat_id: options.chatId } : {}),
      ...(options.mode === 'records' ? { follow_up_topic: options.topic } : { history: options.history })
    })
  })
  checkSession()
  if (response.status === 401) expireSession()
  if (!response.ok || !response.body || !response.headers.get('content-type')?.includes('text/event-stream')) {
    throw new ApiRequestError(response.status, '暂时无法开始对话，请重试。')
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
        if (event.type === 'source') options.onSource(event.source)
        if (event.type === 'delta') options.onDelta(event.text)
        if (event.type === 'complete') return { answer: event.answer, chatId: event.chat_id ?? null }
        if (event.type === 'error') throw new ApiRequestError(502, event.message)
      }
      if (done) throw new ApiRequestError(502, '回答连接已断开，请重试。')
    }
  } finally {
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}
