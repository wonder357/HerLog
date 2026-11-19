/**
 * 日期口径：库里的时间都是 UTC，统计与展示统一按 Asia/Shanghai 自然日。
 * 该模块不依赖 uni / vue，便于用 `node --test` 直接跑。
 */

export const TIME_ZONE = 'Asia/Shanghai'
export const TIME_ZONE_OFFSET = '+08:00'

const DAY_MS = 24 * 60 * 60 * 1000

function partsOf(iso: string): Record<string, string> {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    throw new Error(`时间格式不正确：${iso}`)
  }
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
  return formatter.formatToParts(date).reduce<Record<string, string>>((acc, part) => {
    if (part.type !== 'literal') {
      acc[part.type] = part.value
    }
    return acc
  }, {})
}

/** UTC ISO → 上海自然日（YYYY-MM-DD）。 */
export function shanghaiDayKey(iso: string): string {
  const parts = partsOf(iso)
  return `${parts.year}-${parts.month}-${parts.day}`
}

/** UTC ISO → 上海「11 月 18 日 08:00」。 */
export function formatMoment(iso: string): string {
  const parts = partsOf(iso)
  return `${Number(parts.month)} 月 ${Number(parts.day)} 日 ${parts.hour}:${parts.minute}`
}

export function todayString(): string {
  return shanghaiDayKey(new Date().toISOString())
}

export function isDayString(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value)
}

function toUtcMillis(day: string): number {
  const [year, month, date] = day.split('-').map(Number)
  return Date.UTC(year, month - 1, date)
}

export function addDays(day: string, delta: number): string {
  const next = new Date(toUtcMillis(day) + delta * DAY_MS)
  return next.toISOString().slice(0, 10)
}

export function diffDays(later: string, earlier: string): number {
  return Math.round((toUtcMillis(later) - toUtcMillis(earlier)) / DAY_MS)
}

export function formatDayLabel(day: string): string {
  const [, month, date] = day.split('-').map(Number)
  return `${month} 月 ${date} 日`
}

export function formatMonthLabel(day: string): string {
  const [year, month] = day.split('-').map(Number)
  return `${year} 年 ${month} 月`
}

export function startOfMonth(day: string): string {
  return `${day.slice(0, 7)}-01`
}

export function shiftMonth(day: string, delta: number): string {
  const [year, month] = day.split('-').map(Number)
  const shifted = new Date(Date.UTC(year, month - 1 + delta, 1))
  return shifted.toISOString().slice(0, 7) + '-01'
}

export function daysInMonth(day: string): number {
  const [year, month] = day.split('-').map(Number)
  return new Date(Date.UTC(year, month, 0)).getUTCDate()
}

/** 月历网格：返回从周一算起的空白数与日期列表。 */
export function monthGrid(day: string): { leading: number; days: string[] } {
  const first = startOfMonth(day)
  const [year, month, date] = first.split('-').map(Number)
  const weekday = new Date(Date.UTC(year, month - 1, date)).getUTCDay()
  const leading = (weekday + 6) % 7
  const total = daysInMonth(day)
  const days = Array.from({ length: total }, (_, index) => `${first.slice(0, 7)}-${String(index + 1).padStart(2, '0')}`)
  return { leading, days }
}

/** 选中日 + 时间（HH:mm）→ 带 +08:00 的 ISO，服务端再转 UTC。 */
export function toZonedIso(day: string, time: string): string {
  return `${day}T${time}:00${TIME_ZONE_OFFSET}`
}

/** 当前上海时间的 HH:mm。 */
export function currentTime(): string {
  const parts = partsOf(new Date().toISOString())
  return `${parts.hour}:${parts.minute}`
}

export function compareDay(a: string, b: string): number {
  return toUtcMillis(a) - toUtcMillis(b)
}
