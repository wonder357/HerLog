import { request } from './httpClient'
import type { CycleMode } from '../shared/fertility'
import type { CycleDay } from './wellnessService'

export interface CalendarDay {
  day: string
  weight_kg: string | null
  skin_observation_count: number
  feeling_tags: string[]
}
export interface HomeOverview {
  month: string
  today: string
  active_mode: CycleMode
  cycle_context: CycleDay
  period_prediction: { status: string; expected_start: string | null }
  period_intervals: { start_day: string; end_day: string | null }[]
  open_period: { id: number; start_day: string } | null
  days: CalendarDay[]
  week: { from: string; to: string; recorded_days: number; days: string[]; has_weight: boolean; has_skin: boolean }
  today_recorded: Record<'period' | 'weight' | 'feeling' | 'skin', boolean>
  has_period_history: boolean
  focus: { message_key: 'review_today' | 'review_periods' | 'review_month' | 'record_period' | 'record_feeling_simple' | 'record_feeling'
    action: 'review_today' | 'open_period' | 'open_calendar' | 'record_period' | 'record_feeling' }
}
export interface HealthSummary {
  bmi: { value: string | null; status: 'available' | 'missing_height' | 'missing_weight' | 'missing_both'; height_cm: string | null; weight_day: string | null }
  latest_period_start: string | null
  latest_weight_day: string | null
  latest_skin_observation_day: string | null
}
export interface ReminderSettings {
  period_reminder_enabled: boolean
  record_reminder_enabled: boolean
  delivery_status: 'preference_only'
}
export interface RecordingPreferences {
  weekly_record_days_target: number | null
  show_focus: boolean
  show_summary: boolean
  show_questions: boolean
}

export const recordingDefaults: RecordingPreferences = {
  weekly_record_days_target: null, show_focus: true, show_summary: true, show_questions: true
}

export const fetchHome = (month: string) => request<HomeOverview>('/herlog/overview', { data: { month } })
export const fetchCycleContext = (day: string) => request<CycleDay>('/herlog/cycle-context', { data: { day } })
export const fetchHealthSummary = () => request<HealthSummary>('/herlog/health-summary')
export const fetchReminders = () => request<ReminderSettings>('/herlog/reminder-settings')
export const saveReminders = (data: Partial<Omit<ReminderSettings, 'delivery_status'>>) =>
  request<ReminderSettings>('/herlog/reminder-settings', { method: 'PUT', data })
export const fetchRecordingPreferences = () => request<RecordingPreferences>('/herlog/recording-preferences')
export const saveRecordingPreferences = (data: Partial<RecordingPreferences>) =>
  request<RecordingPreferences>('/herlog/recording-preferences', { method: 'PUT', data })
export const changePassword = (current_password: string, new_password: string) =>
  request<{ reauth_required: boolean }>('/herlog/account/password', { method: 'PUT', timeout: 10000, data: { current_password, new_password } })
