import { request } from './httpClient'
import type { AssistantAnswer } from './types'

export type AssistantTopic = Extract<AssistantAnswer['domain'], 'weight' | 'period' | 'skin'>

/** 只读问答。追问只附上一轮的主题，用户记录由服务端读取。 */
export function ask(question: string, topic?: AssistantTopic): Promise<AssistantAnswer> {
  return request<AssistantAnswer>('/herlog/assistant/query', {
    method: 'POST',
    timeout: 12000,
    data: { question, ...(topic ? { follow_up_topic: topic } : {}) }
  })
}
