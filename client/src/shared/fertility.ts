import { addDays, diffDays, TIME_ZONE } from './dates.ts'

export const fertilityNotice = '仅记录，不构成医疗建议'

export const lhLabels = {
  negative: '阴性',
  weak_positive: '弱阳',
  strong_positive: '强阳'
} as const
export const mucusLabels = {
  dry: '干燥',
  sticky: '黏稠',
  creamy: '乳霜状',
  watery: '水样',
  stretchy: '可拉丝',
  unsure: '不确定'
} as const

export type CycleMode = 'period' | 'trying_to_conceive'
export type LHResult = keyof typeof lhLabels
export type Mucus = keyof typeof mucusLabels

export interface LHTest {
  result: LHResult
  measured_at: string | null
}

export interface DailyValues {
  bbt_c: string | null
  bbt_measured_at: string | null
  lh_tests: LHTest[]
  cervical_mucus: Mucus | null
  intercourse_occurred: boolean | null
}

export interface FertilityDay extends DailyValues {
  day: string
  revision: string
  updated_at: string
}

export interface DateRange {
  from: string
  to: string
}

export interface CycleRange extends DateRange {
  days: number | null
}

export interface TemperaturePoint {
  day: string
  celsius: number
}

const localTime = new Intl.DateTimeFormat('en-GB', {
  timeZone: TIME_ZONE, hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
})

export function shanghaiTime(value?: string | null): string {
  return value ? localTime.format(new Date(value)) : ''
}

export function describeDay(entry: DailyValues): string {
  const parts: string[] = []
  if (entry.bbt_c) {
    const time = shanghaiTime(entry.bbt_measured_at)
    parts.push(`体温 ${entry.bbt_c} °C${time ? '（' + time + '）' : ''}`)
  }
  if (entry.lh_tests.length) {
    parts.push('试纸 ' + entry.lh_tests.map(test => {
      const time = shanghaiTime(test.measured_at)
      return lhLabels[test.result] + '（' + (time || '时间未记录') + '）'
    }).join('、'))
  }
  if (entry.cervical_mucus) parts.push('黏液 ' + mucusLabels[entry.cervical_mucus])
  if (entry.intercourse_occurred !== null) parts.push('同房 ' + (entry.intercourse_occurred ? '有' : '无'))
  return parts.join(' · ')
}

export function cycleRanges(rows: Array<{ start_day: string }>, today: string): CycleRange[] {
  const starts = [...new Set(rows.map(row => row.start_day).filter(day => day <= today))].sort().reverse()
  return starts.map((from, index) => {
    const next = starts[index - 1]
    return { from, to: next ? addDays(next, -1) : today, days: next ? diffDays(next, from) : null }
  })
}

export function temperatureSegments(rows: Array<Pick<FertilityDay, 'day' | 'bbt_c'>>): TemperaturePoint[][] {
  const segments: TemperaturePoint[][] = []
  for (const row of [...rows].sort((a, b) => a.day.localeCompare(b.day))) {
    if (row.bbt_c === null) continue
    const point = { day: row.day, celsius: Number(row.bbt_c) }
    const segment = segments.at(-1)
    const last = segment?.at(-1)
    if (last && diffDays(point.day, last.day) === 1) segment!.push(point)
    else segments.push([point])
  }
  return segments
}

export function equalObservations(a: DailyValues, b: DailyValues): boolean {
  const epoch = (value: string | null) => value ? Date.parse(value) : null
  const tests = (items: LHTest[]) => items.map(item => [epoch(item.measured_at), item.result].join(':')).sort().join(',')
  return (a.bbt_c === null ? b.bbt_c === null : b.bbt_c !== null && Number(a.bbt_c) === Number(b.bbt_c))
    && epoch(a.bbt_measured_at) === epoch(b.bbt_measured_at)
    && a.cervical_mucus === b.cervical_mucus
    && a.intercourse_occurred === b.intercourse_occurred
    && tests(a.lh_tests) === tests(b.lh_tests)
}
