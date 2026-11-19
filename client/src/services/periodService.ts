import { request } from './httpClient'
import type { FeelingItem, PeriodItem, PeriodOverview } from './types'

export function getOverview(): Promise<PeriodOverview> {
  return request<PeriodOverview>('/herlog/periods')
}

export function createPeriod(startDay: string, endDay: string | null): Promise<PeriodItem> {
  return request<PeriodItem>('/herlog/periods', {
    method: 'POST',
    data: { start_day: startDay, end_day: endDay }
  })
}

export function updatePeriod(
  id: number,
  startDay: string,
  endDay: string | null
): Promise<PeriodItem> {
  return request<PeriodItem>(`/herlog/periods/${id}`, {
    method: 'PUT',
    data: { start_day: startDay, end_day: endDay }
  })
}

export function deletePeriod(id: number): Promise<null> {
  return request<null>(`/herlog/periods/${id}`, { method: 'DELETE' })
}

export function listFeelings(from: string, to: string): Promise<FeelingItem[]> {
  return request<FeelingItem[]>('/herlog/feelings', { data: { from, to } })
}

export interface FeelingPayload {
  flow?: string | null
  symptoms?: string[]
  impact?: string | null
  note?: string | null
}

export function saveFeeling(day: string, payload: FeelingPayload): Promise<FeelingItem | null> {
  return request<FeelingItem | null>(`/herlog/feelings/${day}`, {
    method: 'PUT',
    data: payload as Record<string, unknown>
  })
}

export function deleteFeeling(day: string): Promise<null> {
  return request<null>(`/herlog/feelings/${day}`, { method: 'DELETE' })
}
