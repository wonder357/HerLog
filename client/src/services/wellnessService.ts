import { request } from './httpClient'

export type Topic = 'exercise' | 'skin'
export type Phase = 'menstrual' | 'follicular' | 'ovulatory' | 'luteal' | 'unknown'
export type Activity = 'walk' | 'mobility' | 'strength' | 'cycle' | 'rest'
export type Feeling = 'bloating' | 'puffy' | 'tired' | 'comfortable'
export type SkinType = 'dry' | 'oily' | 'combination' | 'balanced' | 'unsure'
export type SkinSensation = 'tight' | 'shine' | 'sensitive' | 'rough' | 'redness'
export type SkinRoutine = 'cleanse' | 'moisturize' | 'sunscreen' | 'shade' | 'cover' | 'reapply'

export interface CycleDay {
  day: string
  phase: Phase
  basis: 'recorded' | 'estimated' | 'unknown'
  note?: string | null
}

export interface JournalInput {
  skin_type: SkinType | null
  comfort: number | null
  sensations: SkinSensation[]
  routine: SkinRoutine[]
  note: string | null
}

export interface JournalDay extends JournalInput { day: string }
export interface ExerciseCard { activity_code: Activity; title: string; instructions: string }
export interface CheckinInput {
  activity_code: Activity
  started_at: string
  duration_minutes: number | null
  effort: 'easy' | 'moderate' | 'hard' | null
}
export interface Checkin extends CheckinInput { id: number }

export interface Group { group_key: string; title: string; joined: boolean }
export interface ShareReference { day?: string; checkin_id?: number; activity?: string; duration?: number | null }
export interface Share {
  public_id: string
  group_key: string
  status: 'published' | 'hidden' | 'withdrawn'
  mine: boolean
  display_name: string
  snapshot: { caption: string; activity?: string; duration_bucket?: string }
  replies?: { text: string; count: number }[]
}
interface GroupFeed { items: Share[]; next_cursor: number | null }

export const phaseNames: Record<Phase, string> = {
  menstrual: '月经期', follicular: '卵泡期', ovulatory: '排卵期', luteal: '黄体期', unknown: '阶段待记录'
}

export const activities: Record<Activity, string> = {
  walk: '散步', mobility: '舒缓活动', strength: '基础力量', cycle: '轻松骑行', rest: '休息'
}

export const captions = {
  skin: [
    { code: 'care_routine', label: '今天记下了自己的护理步骤。' },
    { code: 'sun_care', label: '今天记了一次日光防护。' },
    { code: 'reflection', label: '今天给自己的皮肤感受留了个记录。' },
  ],
  exercise: [
    { code: 'checked_in', label: '记下了今天的活动。' },
    { code: 'kept_it_light', label: '今天选了适合自己的节奏。' },
    { code: 'made_time', label: '今天给自己留了一点时间。' },
  ]
}

const root = '/herlog'
export const listJournal = (from: string, to: string) =>
  request<JournalDay[]>(root + '/skin/journal', { data: { from, to } })
export const latestJournal = () => request<JournalDay | null>(root + '/skin/journal/latest')
export const saveJournal = (day: string, payload: JournalInput) =>
  request<JournalDay>(root + '/skin/journal/' + day, { method: 'PUT', data: { ...payload } })
export const deleteJournal = (day: string) =>
  request<null>(root + '/skin/journal/' + day, { method: 'DELETE' })

export const exerciseCards = (includeCycle: boolean) =>
  request<{ phase: CycleDay | null; cards: ExerciseCard[] }>(root + '/exercise/recommendations', {
    data: { include_cycle: includeCycle }
  })
export const exerciseHistory = () => request<Checkin[]>(root + '/exercise/checkins')
export const saveCheckin = (payload: CheckinInput, client_key: string) =>
  request<Checkin>(root + '/exercise/checkins', { method: 'POST', data: { ...payload, client_key } })
export const deleteCheckin = (id: number) =>
  request<null>(root + '/exercise/checkins/' + id, { method: 'DELETE' })

const groupPath = (topic: Topic, key: string) => root + '/' + topic + '/groups/' + key
const sharePath = (topic: Topic) => root + '/' + topic + '/shares'
export const listGroups = (topic: Topic) => request<Group[]>(root + '/' + topic + '/groups')
export const joinGroup = (topic: Topic, key: string, invite_code: string) =>
  request<null>(groupPath(topic, key) + '/membership', { method: 'POST', data: { invite_code, consent: true } })
export const leaveGroup = (topic: Topic, key: string) =>
  request<null>(groupPath(topic, key) + '/membership', { method: 'DELETE' })
export const listShares = (topic: Topic, key: string, cursor?: number) =>
  request<GroupFeed>(groupPath(topic, key) + '/shares', { data: cursor ? { cursor } : {} })
export const ownShares = (topic: Topic) => request<Share[]>(sharePath(topic) + '/mine')
export const postShare = (topic: Topic, group_key: string, reference: ShareReference,
                         caption_code: string, include_duration_bucket: boolean, client_key: string) =>
  request<Share>(sharePath(topic), { method: 'POST', data: {
    group_key, client_key, caption_code, include_duration_bucket,
    ...(reference.checkin_id ? { checkin_id: reference.checkin_id } : { day: reference.day })
  } })
export const withdrawShare = (topic: Topic, id: string) =>
  request<null>(sharePath(topic) + '/' + id, { method: 'DELETE' })
export const reportShare = (topic: Topic, id: string, reason_code: string) =>
  request<null>(sharePath(topic) + '/' + id + '/reports', { method: 'POST', data: { reason_code } })
export const replyToSkinShare = (id: string, reply_code: string) =>
  request<null>(sharePath('skin') + '/' + id + '/replies', { method: 'POST', data: { reply_code } })
