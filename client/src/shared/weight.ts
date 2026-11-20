/**
 * 体重统计：与后端 `app/logic/weight.py` 同一口径。
 * 同一自然日只取最后一次进入图表，记录次数统计全部测量，首尾变化按图上两个点求差。
 */

import { addDays, shanghaiDayKey } from './dates.ts'

export interface WeightRecord {
  id: number
  grams: number
  measuredAt: string
  tag?: string | null
  note?: string | null
}

export interface WeightPoint {
  day: string
  grams: number
  weightId: number
  measuredAt: string
}

export interface WeightSummary {
  days: number
  count: number
  points: WeightPoint[]
  deltaGrams: number | null
  latestGrams: number | null
  latestMeasuredAt: string | null
}

const KG_PATTERN = /^\d{1,3}(\.\d{1,3})?$/

export const weightMetrics = {
  weight_kg: { label: '体重', unit: 'kg', changeUnit: 'kg', digits: 2 },
  bmi: { label: 'BMI', unit: 'kg/m²', changeUnit: 'kg/m²', digits: 1 },
  body_fat_pct: { label: '体脂率', unit: '%', changeUnit: '个百分点', digits: 2 }
} as const
export type WeightMetric = keyof typeof weightMetrics

export function parseBodyFat(input: string): string | null {
  const text = input.trim()
  if (!text) return null
  if (!/^\d{1,2}(\.\d{1,2})?$/.test(text) || Number(text) <= 0 || Number(text) >= 100) {
    throw new Error('体脂率需大于 0 且小于 100，最多两位小数')
  }
  return text
}

export function measureValue(value: number, metric: WeightMetric): string {
  return String(Number(value.toFixed(metric === 'weight_kg' ? 3 : weightMetrics[metric].digits)))
}

export function measureChange(value: number, metric: WeightMetric): string {
  const digits = metric === 'weight_kg' ? 3 : weightMetrics[metric].digits
  const rounded = Number(value.toFixed(digits))
  return (rounded > 0 ? '+' : rounded < 0 ? '−' : '') + Math.abs(rounded) + ' ' + weightMetrics[metric].changeUnit
}

type PhaseFilter = 'menstrual' | 'follicular' | 'ovulatory' | 'luteal' | 'unknown'
interface CycleMeasurement {
  cycle_day: number
  phase: PhaseFilter
  weight_kg: number
  bmi: number | null
  body_fat_pct: number | null
}

export function pairCycleMeasurements<T extends CycleMeasurement>(
  current: T[], previous: T[], metric: WeightMetric, phase: PhaseFilter | 'all' = 'all'
) {
  const eligible = (row: T) => row[metric] !== null && (phase === 'all' || row.phase === phase)
  const currentPoints = current.filter(eligible)
  const previousPoints = previous.filter(eligible)
  const reference = new Map(previousPoints.map(row => [row.cycle_day, row]))
  const pairs = currentPoints.flatMap(row => {
    const match = reference.get(row.cycle_day)
    return match ? [{ current: row, previous: match }] : []
  })
  const averages = pairs.length < 2 ? null : {
    current: pairs.reduce((sum, pair) => sum + (pair.current[metric] ?? 0), 0) / pairs.length,
    previous: pairs.reduce((sum, pair) => sum + (pair.previous[metric] ?? 0), 0) / pairs.length
  }
  return { currentPoints, previousPoints, pairs, averages }
}

/** 输入 kg（最多三位小数）→ 正整数克；不合法时抛出可直接展示的中文文案。 */
export function parseKgToGrams(input: string): number {
  const text = String(input ?? '').trim()
  if (!text) {
    throw new Error('请填写体重')
  }
  if (!KG_PATTERN.test(text)) {
    throw new Error('体重需为数字，最多三位小数')
  }
  const grams = Math.round(Number(text) * 1000)
  if (grams <= 0) {
    throw new Error('体重需为正数')
  }
  return grams
}

export function formatKg(grams: number | null): string {
  if (grams === null || Number.isNaN(grams)) {
    return '—'
  }
  return String(Number((grams / 1000).toFixed(3)))
}

export function formatDelta(grams: number | null): string {
  if (grams === null) {
    return ''
  }
  const sign = grams > 0 ? '+' : ''
  return `${sign}${Number((grams / 1000).toFixed(3))} kg`
}

export function dailyPoints(records: WeightRecord[]): WeightPoint[] {
  const latest = new Map<string, WeightPoint>()
  for (const record of records) {
    const day = shanghaiDayKey(record.measuredAt)
    const candidate: WeightPoint = {
      day,
      grams: record.grams,
      weightId: record.id,
      measuredAt: record.measuredAt
    }
    const current = latest.get(day)
    if (!current || new Date(candidate.measuredAt) >= new Date(current.measuredAt)) {
      latest.set(day, candidate)
    }
  }
  return Array.from(latest.values()).sort((a, b) => (a.day < b.day ? -1 : a.day > b.day ? 1 : 0))
}

export function summarize(records: WeightRecord[], days: number, today: string): WeightSummary {
  if (days !== 7 && days !== 30) {
    throw new Error('只支持 7 天或 30 天')
  }
  const startDay = addDays(today, -(days - 1))
  const inRange = records.filter((record) => {
    const day = shanghaiDayKey(record.measuredAt)
    return day >= startDay && day <= today
  })
  const points = dailyPoints(inRange)
  const deltaGrams = points.length >= 2 ? points[points.length - 1].grams - points[0].grams : null
  const latestRecord = [...records].sort(
    (a, b) => new Date(b.measuredAt).getTime() - new Date(a.measuredAt).getTime() || b.id - a.id
  )[0]
  return {
    days,
    count: inRange.length,
    points,
    deltaGrams,
    latestGrams: latestRecord ? latestRecord.grams : null,
    latestMeasuredAt: latestRecord ? latestRecord.measuredAt : null
  }
}

/** 一条与当前记录情况相关的建议；没有合适建议时返回 null（页面收起该区域）。 */
export function suggestion(summary: WeightSummary): string | null {
  if (summary.count === 0) {
    return null
  }
  if (summary.points.length <= 1) {
    return '先继续记录几天，再来看看变化趋势。'
  }
  if (summary.count > summary.points.length) {
    return '如果想比较长期变化，尽量在相近的时间和条件下称重。'
  }
  if (summary.deltaGrams !== null && Math.abs(summary.deltaGrams) < 200) {
    return '这段时间体重变化很小，继续按自己的节奏记录即可。'
  }
  return '想看得更准，可以固定早晨空腹、同一台秤称重。'
}

export function rangeStart(days: number, today: string): string {
  return addDays(today, -(days - 1))
}
