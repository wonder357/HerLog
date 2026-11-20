/**
 * 经期预测：与后端 `app/logic/period.py` 同一套规则，日历与预测都在前端算，
 * 不请求旧方案服务，也不依赖大模型。
 */

import { addDays, diffDays, formatDayLabel, startOfMonth } from './dates.ts'

export const MAX_STARTS = 4
export const MIN_STARTS = 3
export const MAX_SPREAD_DAYS = 7

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

export function periodRange(item: CycleRecord): string {
  const year = item.start_day.slice(0, 4)
  const start = year + ' 年 ' + formatDayLabel(item.start_day)
  if (!item.end_day || item.end_day === item.start_day) return start
  const endYear = item.end_day.slice(0, 4)
  return start + ' – ' + (year === endYear ? '' : endYear + ' 年 ') + formatDayLabel(item.end_day)
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

export type FeelingFilter = { kind: 'flow' | 'mood' | 'symptom' | 'impact'; label: string }

interface DiaryEntry {
  day: string
  flow?: string | null
  mood?: string | null
  symptoms: string[]
  impact?: string | null
}

export function matchesFeeling(entry: DiaryEntry, filter: FeelingFilter): boolean {
  return filter.kind === 'symptom' ? entry.symptoms.includes(filter.label) : entry[filter.kind] === filter.label
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
    flows: counts(row => row.flow ? [row.flow] : []),
    moods: counts(row => row.mood ? [row.mood] : []),
    symptoms: counts(row => row.symptoms),
    impacts: counts(row => row.impact ? [row.impact] : [])
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
  const candidate = addDays(ordered[0], estimate)
  const status: PredictionStatus = today > candidate ? 'overdue' : 'upcoming'
  const expectedStart = status === 'upcoming' ? candidate : null
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
