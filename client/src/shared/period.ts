/**
 * 经期预测：与后端 `app/logic/period.py` 同一套规则，日历与预测都在前端算，
 * 不请求旧方案服务，也不依赖大模型。
 */

import { addDays, diffDays, startOfMonth } from './dates.ts'

export const MAX_STARTS = 4
export const MIN_STARTS = 3
export const MAX_SPREAD_DAYS = 7

/** 日历高亮用：预测经期长度、排卵日与易孕期，与后端 `app/logic/period.py` 同一套规则。 */
export const DEFAULT_DURATION_DAYS = 5
export const MIN_DURATION_DAYS = 2
export const MAX_DURATION_DAYS = 10
export const LUTEAL_DAYS = 14
export const FERTILE_BEFORE_OVULATION = 5
export const FERTILE_AFTER_OVULATION = 1

export type PredictionStatus = 'insufficient' | 'irregular' | 'upcoming' | 'overdue'

export interface Prediction {
  status: PredictionStatus
  expectedStart: string | null
  estimateDays: number | null
  cycleCount: number
  startsUsed: number
  message: string
}

export interface HistoryRow {
  id: number
  startDay: string
  endDay: string | null
  durationDays: number | null
  cycleDays: number | null
}

interface CycleRecord {
  start_day: string
  end_day: string | null
}

export function periodOnDay<T extends CycleRecord>(rows: T[], day: string): T | null {
  return rows.find(row => row.start_day <= day && day <= (row.end_day ?? row.start_day)) ?? null
}

export function openPeriodOnDay<T extends CycleRecord>(rows: T[], day: string): T | null {
  const latest = rows.find(row => row.start_day <= day)
  return latest && !latest.end_day ? latest : null
}

export function selectedDayInMonth(month: string, today: string): string {
  return month === startOfMonth(today) ? today : month
}

export type FeelingFilter = { kind: 'mood' | 'symptom'; label: string }

interface DiaryEntry {
  day: string
  mood?: string | null
  symptoms: string[]
}

export function matchesFeeling(entry: DiaryEntry, filter: FeelingFilter): boolean {
  return filter.kind === 'mood' ? entry.mood === filter.label : entry.symptoms.includes(filter.label)
}

export function summarizeDiary(rows: DiaryEntry[]) {
  const counts = (labels: (row: DiaryEntry) => string[]) => {
    const daysByLabel = new Map<string, Set<string>>()
    for (const row of rows) {
      for (const label of labels(row)) {
        const days = daysByLabel.get(label) ?? new Set<string>()
        days.add(row.day)
        daysByLabel.set(label, days)
      }
    }
    return Array.from(daysByLabel, ([label, days]) => ({ label, days: days.size }))
      .sort((a, b) => b.days - a.days || a.label.localeCompare(b.label, 'zh-CN'))
  }
  return {
    days: new Set(rows.map(row => row.day)).size,
    moods: counts(row => row.mood ? [row.mood] : []),
    symptoms: counts(row => row.symptoms)
  }
}

export function recentCycleStats(rows: { cycle_days: number | null; duration_days: number | null }[]) {
  const range = (key: 'cycle_days' | 'duration_days') => {
    const values = rows.map(row => row[key]).filter((value): value is number => value !== null).slice(0, 6)
    return values.length ? { count: values.length, min: Math.min(...values), max: Math.max(...values) } : null
  }
  return { interval: range('cycle_days'), duration: range('duration_days') }
}

export function reminderDay(expectedStart: string, leadDays: number, now: string): string | null {
  const day = addDays(expectedStart, -leadDays)
  return `${day}T01:00:00.000Z` > now ? day : null
}

/** 导出的日历文件只包含 09:00（上海时间）的通用提醒。 */
export function createReminderCalendar(day: string, uid: string, now: string): string {
  const stamp = now.replace(/[-:]|\.\d+/g, '')
  const compactDay = day.replace(/-/g, '')
  return [
    'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//HerLog//Private Reminder//ZH',
    'BEGIN:VEVENT', `UID:${uid}@herlog.local`, `DTSTAMP:${stamp}`,
    `DTSTART:${compactDay}T010000Z`, `DTEND:${compactDay}T010500Z`,
    'SUMMARY:个人日程提醒', 'CLASS:PRIVATE', 'TRANSP:TRANSPARENT',
    'BEGIN:VALARM', 'TRIGGER:PT0S', 'ACTION:DISPLAY', 'DESCRIPTION:个人日程提醒', 'END:VALARM',
    'END:VEVENT', 'END:VCALENDAR', ''
  ].join('\r\n')
}

export function recentStarts(starts: string[], limit = MAX_STARTS): string[] {
  return Array.from(new Set(starts))
    .sort((a, b) => (a < b ? 1 : a > b ? -1 : 0))
    .slice(0, limit)
}

export function cycleIntervals(starts: string[]): number[] {
  const ordered = [...starts]
  const intervals: number[] = []
  for (let index = 0; index < ordered.length - 1; index += 1) {
    intervals.push(diffDays(ordered[index], ordered[index + 1]))
  }
  return intervals
}

export function estimateCycleDays(starts: string[]): { estimate: number | null; intervals: number[] } {
  const ordered = recentStarts(starts)
  if (ordered.length < MIN_STARTS) {
    return { estimate: null, intervals: [] }
  }
  const intervals = cycleIntervals(ordered)
  if (Math.max(...intervals) - Math.min(...intervals) > MAX_SPREAD_DAYS) {
    return { estimate: null, intervals }
  }
  if (intervals.length === 3) {
    return { estimate: [...intervals].sort((a, b) => a - b)[1], intervals }
  }
  const average = intervals.reduce((sum, value) => sum + value, 0) / intervals.length
  return { estimate: Math.round(average), intervals }
}

export interface DayRange {
  start_day: string
  end_day: string
}

export type CycleDayRole = 'actual' | 'predicted' | 'ovulation' | 'fertile' | ''

export function clampDuration(days: number): number {
  return Math.min(MAX_DURATION_DAYS, Math.max(MIN_DURATION_DAYS, days))
}

/** 最近至多 4 段完整经期的平均持续天数，四舍五入后夹在 2–10 天。 */
export function estimateDurationDays(rows: { startDay: string; endDay: string | null }[]): number {
  const ordered = [...rows].sort((a, b) => (a.startDay < b.startDay ? 1 : a.startDay > b.startDay ? -1 : 0))
  const values = ordered
    .filter(row => row.endDay !== null)
    .slice(0, MAX_STARTS)
    .map(row => diffDays(row.endDay as string, row.startDay) + 1)
    .filter(value => value > 0)
  if (!values.length) {
    return DEFAULT_DURATION_DAYS
  }
  return clampDuration(Math.round(values.reduce((sum, value) => sum + value, 0) / values.length))
}

/** 预测经期区间：开始日到开始日 + 持续天数 - 1。 */
export function predictedRange(expectedStart: string, duration = DEFAULT_DURATION_DAYS): DayRange {
  return { start_day: expectedStart, end_day: addDays(expectedStart, clampDuration(duration) - 1) }
}

/** 排卵日：按黄体期 14 天从下次经期开始日回推。 */
export function ovulationDay(expectedStart: string): string {
  return addDays(expectedStart, -LUTEAL_DAYS)
}

/**
 * 日历上真正高亮的预测经期区间。
 * 已过预计开始日却还没记录新的经期时，区间从今天起算并逐日顺延，
 * 不能把高亮留在过去。返回顺延天数，供文案提示「推迟 N 天」。
 */
export function scheduleRange(
  expectedStart: string,
  today: string,
  duration = DEFAULT_DURATION_DAYS
): DayRange & { overdue_days: number } {
  const overdueDays = Math.max(0, diffDays(today, expectedStart))
  const start = addDays(expectedStart, overdueDays)
  return {
    start_day: start,
    end_day: addDays(start, clampDuration(duration) - 1),
    overdue_days: overdueDays
  }
}

/** 易孕期：排卵日前 5 天到排卵日后 1 天。 */
export function fertileWindow(expectedStart: string): DayRange {
  const day = ovulationDay(expectedStart)
  return {
    start_day: addDays(day, -FERTILE_BEFORE_OVULATION),
    end_day: addDays(day, FERTILE_AFTER_OVULATION)
  }
}

export function inRange(day: string, range: DayRange | null | undefined): boolean {
  return Boolean(range && day >= range.start_day && day <= range.end_day)
}

/**
 * 某一天在月历上的角色，优先级：已记录经期 > 预测经期 > 排卵日 > 易孕期。
 * 已记录只认今天及以前的日期，避免把未来日期显示成实际记录。
 */
export function cycleDayRole(
  day: string,
  ctx: {
    today: string
    periods: { start_day: string; end_day: string | null }[]
    predictedRange?: DayRange | null
    ovulationDay?: string | null
    fertileWindow?: DayRange | null
  }
): CycleDayRole {
  if (day <= ctx.today && periodOnDay(ctx.periods, day)) return 'actual'
  if (inRange(day, ctx.predictedRange)) return 'predicted'
  if (ctx.ovulationDay === day) return 'ovulation'
  if (inRange(day, ctx.fertileWindow)) return 'fertile'
  return ''
}

export function messageFor(status: PredictionStatus, expectedStart: string | null): string {
  if (status === 'insufficient') {
    return '再记录几次经期开始日期，就能估算下次日期'
  }
  if (status === 'irregular') {
    return '近期周期变化较大，暂不显示预计日期'
  }
  if (status === 'overdue') {
    return '已过预计日期，尚未记录新的经期开始'
  }
  if (!expectedStart) {
    return ''
  }
  const [, month, date] = expectedStart.split('-').map(Number)
  return `预计下次开始：${month} 月 ${date} 日`
}

export function predictNextStart(starts: string[], today: string): Prediction {
  const ordered = recentStarts(starts)
  if (ordered.length < MIN_STARTS) {
    return {
      status: 'insufficient',
      expectedStart: null,
      estimateDays: null,
      cycleCount: 0,
      startsUsed: ordered.length,
      message: messageFor('insufficient', null)
    }
  }
  const { estimate, intervals } = estimateCycleDays(ordered)
  if (estimate === null) {
    return {
      status: 'irregular',
      expectedStart: null,
      estimateDays: null,
      cycleCount: intervals.length,
      startsUsed: ordered.length,
      message: messageFor('irregular', null)
    }
  }
  const expectedStart = addDays(ordered[0], estimate)
  const status: PredictionStatus = today > expectedStart ? 'overdue' : 'upcoming'
  return {
    status,
    expectedStart,
    estimateDays: estimate,
    cycleCount: intervals.length,
    startsUsed: ordered.length,
    message: messageFor(status, expectedStart)
  }
}

/** 持续天数包含开始日和最后一天。 */
export function durationDays(startDay: string, endDay: string | null): number | null {
  if (!endDay) {
    return null
  }
  return diffDays(endDay, startDay) + 1
}

export function buildHistory(
  rows: { id: number; startDay: string; endDay: string | null }[]
): HistoryRow[] {
  const ordered = [...rows].sort((a, b) =>
    a.startDay < b.startDay ? 1 : a.startDay > b.startDay ? -1 : 0
  )
  return ordered.map((row, index) => ({
    id: row.id,
    startDay: row.startDay,
    endDay: row.endDay,
    durationDays: durationDays(row.startDay, row.endDay),
    cycleDays: index + 1 < ordered.length ? diffDays(row.startDay, ordered[index + 1].startDay) : null
  }))
}

/** 当前经期状态：只认已确认的实际区间，预计日期不算。 */
export function currentStatus(
  rows: { startDay: string; endDay: string | null }[],
  today: string
): { inPeriod: boolean; dayIndex: number | null; message: string } {
  const ordered = [...rows].sort((a, b) =>
    a.startDay < b.startDay ? 1 : a.startDay > b.startDay ? -1 : 0
  )
  const latest = ordered.find(row => row.startDay <= today)
  if (!latest) {
    return { inPeriod: false, dayIndex: null, message: '还没有经期记录' }
  }
  if (latest.endDay ? latest.endDay >= today : predictNextStart(ordered
    .filter(row => row.startDay <= today).map(row => row.startDay), today).status !== 'overdue') {
    const dayIndex = diffDays(today, latest.startDay) + 1
    return { inPeriod: true, dayIndex, message: `经期第 ${dayIndex} 天` }
  }
  return {
    inPeriod: false,
    dayIndex: null,
    message: latest.endDay
      ? `最近一次经期开始 ${latest.startDay}`
      : `最近一次经期开始 ${latest.startDay}，未记录结束`
  }
}
