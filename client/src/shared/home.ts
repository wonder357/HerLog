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

const cycleStarters: Record<string, string> = {
  menstrual: '经期感受适合记哪些内容？',
  follicular: '月历上的实际日期和估算有什么区别？',
  ovulatory: '月历上的周期阶段估算该怎么理解？',
  luteal: '回看经期估算时要留意什么？'
}

export function assistantStarters(phase: string, hasWeight: boolean, hasSkin: boolean): string[] {
  return [
    cycleStarters[phase] ?? '怎样开始记录经期？',
    hasWeight ? '怎样读懂体重趋势？' : hasSkin ? '怎样对比同一部位的皮肤观察？' : '肤质观察可以记哪些内容？'
  ]
}
