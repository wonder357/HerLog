import { addDays, formatMoment, shanghaiDayKey, shiftMonth, startOfMonth } from './dates.ts'

export interface SkinRecordKey {
  id: number
  site: string
  captured_at: string
}

export function skinMonthRange(day: string): { from: string; to: string } {
  return { from: startOfMonth(day), to: addDays(shiftMonth(day, 1), -1) }
}

export function groupSkinDays<T extends SkinRecordKey>(rows: T[]): Map<string, T[]> {
  const groups = new Map<string, T[]>()
  for (const row of rows) {
    const day = shanghaiDayKey(row.captured_at)
    const group = groups.get(day)
    if (group) group.push(row)
    else groups.set(day, [row])
  }
  return groups
}

export function skinMoment(iso: string): string {
  return `${shanghaiDayKey(iso).slice(0, 4)} 年 ${formatMoment(iso)}`
}

export function compareSkinRecords(first: SkinRecordKey, second: SkinRecordKey): string | null {
  if (first.id === second.id) return '请选择另一条记录'
  if (first.site !== second.site) return '请选择同一部位的另一条记录'
  return null
}

export function chronologicalSkinPair<T extends SkinRecordKey>(records: T[]): T[] {
  return [...records].sort((first, second) =>
    Date.parse(first.captured_at) - Date.parse(second.captured_at) || first.id - second.id
  )
}

export function selfAssessedSkinType(
  shine: 'all' | 't_zone' | 'little' | null,
  tight: 'often' | 'rarely' | null
): 'dry' | 'oily' | 'combination' | 'balanced' | 'unsure' {
  if (!shine || !tight) return 'unsure'
  if (shine === 't_zone') return 'combination'
  if (shine === 'all') return tight === 'often' ? 'unsure' : 'oily'
  return tight === 'often' ? 'dry' : 'balanced'
}
