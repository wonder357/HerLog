import { request } from './httpClient'
import type { CycleMode, DailyValues, DateRange, FertilityDay } from '../shared/fertility'

export interface CyclePreference {
  active_mode: CycleMode
  configured: boolean
  seen_fertility: boolean
  trying_started_on: string | null
}

export function getCyclePreference(): Promise<CyclePreference> {
  return request('/herlog/cycle-preference')
}

export function updateCycleMode(mode: CycleMode): Promise<CyclePreference> {
  return request('/herlog/cycle-preference', { method: 'PUT', data: { active_mode: mode } })
}

export function updateTryingStart(day: string | null): Promise<CyclePreference> {
  return request('/herlog/cycle-preference/start-date', { method: 'PUT', data: { trying_started_on: day } })
}

export function listFertilityDays(range: DateRange): Promise<FertilityDay[]> {
  return request('/herlog/fertility-daily', { data: { ...range } })
}

export function getFertilityDay(day: string): Promise<FertilityDay> {
  return request('/herlog/fertility-daily/' + day)
}

export function saveFertilityDay(day: string, values: DailyValues, revision: string | null): Promise<FertilityDay> {
  return request('/herlog/fertility-daily/' + day, { method: 'PUT', data: { ...values, expected_revision: revision } })
}

export function deleteFertilityDay(day: string, revision: string): Promise<null> {
  return request('/herlog/fertility-daily/' + day + '?expected_revision=' + encodeURIComponent(revision), { method: 'DELETE' })
}
