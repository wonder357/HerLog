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

// 展示用的虚构曲线；空值用于演示缺测日。只用于趋势卡，不生成 WeightRecord。
const TREND_EXAMPLE_KG = [
  58.2, 58.5, 58.2, 58.3, 58.6, null, 58.5,
  58.2, 58.1, 58.3, 58.4, 58.2, null, 58.6,
  58.5, 58.4, 58.6, 58.7, 58.5, null, 58.3, 58.2, 58.4,
  58.5, 58.6, 58.5, 58.3, 58.2, 58.3, 58.4
]

export function trendExample(days: 7 | 30, today: string): { day: string; kg: number }[] {
  return TREND_EXAMPLE_KG.slice(-days).flatMap((kg, offset) =>
    kg === null ? [] : [{ day: addDays(today, offset - days + 1), kg }]
  )
}
