export const calendarKinds = {
  period: '实际经期', weight: '有体重记录', skin: '有皮肤观察', feeling: '有感受记录'
} as const
export type CalendarKind = keyof typeof calendarKinds

interface DayMarkInput {
  weight_kg: string | null
  skin_observation_count: number
  feeling_tags: string[]
}

export function calendarMarks(actual: boolean, row?: DayMarkInput): CalendarKind[] {
  const result: CalendarKind[] = []
  if (actual) result.push('period')
  if (row && row.weight_kg !== null) result.push('weight')
  if (row?.skin_observation_count) result.push('skin')
  if (row?.feeling_tags.length) result.push('feeling')
  return result
}

export function suggestedQuestions(phase: string, hasWeight: boolean, hasSkin: boolean): string[] {
  return [
    phase === 'follicular' || phase === 'luteal' ? '下次经期大概什么时候？' : '最近一次经期从哪天开始？',
    hasWeight ? '近 7 天有哪些体重记录？' : hasSkin ? '最近的皮肤观察是什么？' : ''
  ].filter(Boolean)
}
