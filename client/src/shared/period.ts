/**
 * 经期预测：与后端 `app/logic/period.py` 同一套规则，日历与预测都在前端算，
 * 不请求旧方案服务，也不依赖大模型。
 */

import { addDays, diffDays } from './dates.ts'

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
  for (const row of ordered) {
    if (row.startDay <= today && (row.endDay === null || row.endDay >= today)) {
      const dayIndex = diffDays(today, row.startDay) + 1
      return { inPeriod: true, dayIndex, message: `经期第 ${dayIndex} 天` }
    }
  }
  if (ordered.length === 0) {
    return { inPeriod: false, dayIndex: null, message: '还没有经期记录' }
  }
  const latest = ordered[0]
  return {
    inPeriod: false,
    dayIndex: null,
    message: latest.endDay
      ? `最近一次经期开始 ${latest.startDay}`
      : `最近一次经期开始 ${latest.startDay}，未记录结束`
  }
}
