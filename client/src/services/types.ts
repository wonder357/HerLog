import type { CycleDay, Feeling } from './wellnessService'

export interface MemberInfo {
  customer_id: string
  username: string
  name: string
  phone: string | null
  avatar?: string | null
  org_id?: string | null
  org_ids?: string[]
}

export interface LoginResult extends MemberInfo {
  session_id: string
  token: string
  expires_at: string
}

export interface ProfileInfo {
  username: string
  birthday: string | null
  height_cm: string | null
  contact_phone: string | null
}

export interface PeriodItem {
  id: number
  start_day: string
  end_day: string | null
  duration_days: number | null
  cycle_days: number | null
}

export interface PeriodPrediction {
  status: 'insufficient' | 'irregular' | 'upcoming' | 'overdue'
  expected_start: string | null
  estimate_days: number | null
  cycle_count: number
  starts_used: number
  message: string
}

export interface PeriodStatus {
  in_period: boolean
  day_index: number | null
  message: string
  start_day: string | null
  end_day: string | null
}

export interface PeriodOverview {
  items: PeriodItem[]
  prediction: PeriodPrediction
  status: PeriodStatus
}

export interface FeelingItem {
  day: string
  flow: string | null
  mood?: string | null
  symptoms: string[]
  impact: string | null
  note: string | null
}

export interface WeightItem {
  feeling_tags?: Feeling[]
  source?: 'manual' | 'scale'
  device_id?: number | null
  id: number
  client_key: string
  grams: number
  kg: number
  measured_at: string
  tag: string | null
  note: string | null
}

export interface WeightPointItem {
  day: string
  grams: number
  kg: number
  weight_id: number
  measured_at: string
}

export interface WeightSummary {
  record_days?: number
  latest_record_id?: number | null
  cycle_context?: CycleDay[] | null
  metrics?: Record<string, {
    value: number | null
    unit: string
    status: string
    source: string | null
    measured_at: string | null
  }>
  days: number
  latest_grams: number | null
  latest_kg: number | null
  latest_measured_at: string | null
  count: number
  points: WeightPointItem[]
  delta_grams: number | null
  delta_kg: number | null
  suggestion: string | null
}

export interface WeightList {
  items: WeightItem[]
  total: number
  page: number
  page_size: number
}

export interface SkinQuality {
  level: 'good' | 'limited'
  message: string
}

export interface SkinAnalysis {
  analysis_id: string
  expires_at: string
  site: string
  captured_at: string
  quality: SkinQuality
  visible: string
  unclear: string
  attention: string
  model_id: string
  prompt_version: string
  demo_sample: boolean
  inference_ms?: number | null
}

export interface SkinObservation {
  id: number
  site: string
  captured_at: string
  mime: string
  visible: string
  unclear: string
  attention: string
  model_id: string
  prompt_version: string
  has_image: boolean
  quality?: SkinQuality | null
  demo_sample?: boolean
}

export interface SkinSummaryItem {
  id: number
  site: string
  captured_at: string
  visible: string
  demo_sample?: boolean
}

export interface RecordRef {
  type: 'weight' | 'period' | 'feeling' | 'skin' | 'profile'
  id: string
  label: string
  route: string
}

export interface AssistantAnswer {
  answer: string
  domain: 'weight' | 'period' | 'skin' | 'record_help' | 'unsupported'
  range: { label: string; date_from: string | null; date_to: string | null; days: number | null }
  record_refs: RecordRef[]
  model_id: string | null
}
