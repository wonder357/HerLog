import { request } from './httpClient'
import type { AssistantAnswer } from './types'

/** 只读问答：客户端只发问题，不提交用户 ID、历史统计或整份健康档案。 */
export function ask(question: string): Promise<AssistantAnswer> {
  return request<AssistantAnswer>('/herlog/assistant/query', {
    method: 'POST',
    data: { question }
  })
}
