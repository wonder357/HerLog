import { request } from './httpClient'
import type { WeightItem, WeightList, WeightSummary } from './types'

export interface WeightPayload {
  client_key: string
  kg: string
  measured_at: string
  tag?: string | null
  note?: string | null
}

export interface WeightQuery {
  from?: string
  to?: string
  tag?: string
  page?: number
  pageSize?: number
}

export function listWeights(query: WeightQuery = {}): Promise<WeightList> {
  const data: Record<string, unknown> = {}
  if (query.from) data.from = query.from
  if (query.to) data.to = query.to
  if (query.tag) data.tag = query.tag
  if (query.page) data.page = query.page
  if (query.pageSize) data.page_size = query.pageSize
  return request<WeightList>('/herlog/weights', { data })
}

export function getSummary(days: 7 | 30): Promise<WeightSummary> {
  return request<WeightSummary>('/herlog/weights/summary', { data: { days } })
}

export function createWeight(payload: WeightPayload): Promise<WeightItem> {
  return request<WeightItem>('/herlog/weights', {
    method: 'POST',
    data: payload as unknown as Record<string, unknown>
  })
}

export function updateWeight(id: number, payload: WeightPayload): Promise<WeightItem> {
  return request<WeightItem>(`/herlog/weights/${id}`, {
    method: 'PUT',
    data: payload as unknown as Record<string, unknown>
  })
}

export function deleteWeight(id: number): Promise<null> {
  return request<null>(`/herlog/weights/${id}`, { method: 'DELETE' })
}

/** 一次保存重试沿用同一个请求键。 */
export function newClientKey(): string {
  const random = Math.random().toString(36).slice(2, 10)
  return `w-${Date.now().toString(36)}-${random}`
}
