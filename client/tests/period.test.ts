import assert from 'node:assert/strict'
import { test } from 'node:test'

import { addDays, diffDays, formatMoment, monthGrid, shanghaiDayKey, toZonedIso } from '../src/shared/dates.ts'
import {
  buildHistory,
  currentStatus,
  cycleDayRole,
  durationDays,
  estimateCycleDays,
  estimateDurationDays,
  fertileWindow,
  inRange,
  ovulationDay,
  predictNextStart,
  predictedRange,
  scheduleRange,
  createReminderCalendar,
  matchesFeeling,
  openPeriodOnDay,
  periodOnDay,
  recentCycleStats,
  reminderDay,
  selectedDayInMonth,
  summarizeDiary
} from '../src/shared/period.ts'

test('UTC 时间按上海自然日归档', () => {
  // 2026-11-17T16:30Z = 2026-11-18 00:30 上海时间
  assert.equal(shanghaiDayKey('2026-11-17T16:30:00Z'), '2026-11-18')
  assert.equal(shanghaiDayKey('2026-11-18T08:00:00Z'), '2026-11-18')
  assert.equal(formatMoment('2026-11-18T00:00:00Z'), '11 月 18 日 08:00')
  assert.equal(toZonedIso('2026-11-18', '08:00'), '2026-11-18T08:00:00+08:00')
})

test('自然日加减跨月与跨年', () => {
  assert.equal(addDays('2026-11-30', 1), '2026-12-01')
  assert.equal(addDays('2027-01-01', -1), '2026-12-31')
  assert.equal(diffDays('2026-11-01', '2026-10-03'), 29)
})

test('月历网格从周一开始并给出当月天数', () => {
  const grid = monthGrid('2026-11-18')
  assert.equal(grid.days.length, 30)
  assert.equal(grid.leading, 6) // 2026-11-01 是周日
  assert.equal(grid.days[0], '2026-11-01')
})

test('附录六组预测边界', () => {
  const today = '2026-12-01'
  const predicted = predictNextStart(['2026-10-03', '2026-11-01', '2026-11-30'], today)
  assert.equal(predicted.status, 'upcoming')
  assert.equal(predicted.expectedStart, '2026-12-29')
  assert.equal(predicted.estimateDays, 29)
  assert.equal(predicted.message, '预计下次开始：12 月 29 日')

  const spread7 = predictNextStart(['2026-10-06', '2026-10-31', '2026-12-02'], '2026-12-03')
  assert.equal(spread7.status, 'upcoming')
  assert.equal(spread7.estimateDays, 29)

  const spread8 = predictNextStart(['2026-10-05', '2026-10-30', '2026-12-02'], '2026-12-03')
  assert.equal(spread8.status, 'irregular')
  assert.equal(spread8.expectedStart, null)
  assert.equal(spread8.message, '近期周期变化较大，暂不显示预计日期')

  const insufficient = predictNextStart(['2026-10-03', '2026-11-01'], today)
  assert.equal(insufficient.status, 'insufficient')
  assert.equal(insufficient.expectedStart, null)

  const overdue = predictNextStart(['2026-10-03', '2026-11-01', '2026-11-30'], '2026-12-30')
  assert.equal(overdue.status, 'overdue')
  assert.equal(overdue.expectedStart, null)
  const dueToday = predictNextStart(['2026-10-03', '2026-11-01', '2026-11-30'], '2026-12-29')
  assert.equal(dueToday.status, 'upcoming')
  assert.equal(dueToday.expectedStart, '2026-12-29')
})

test('三次以上开始日取中位数', () => {
  const { estimate, intervals } = estimateCycleDays(['2026-08-01', '2026-08-31', '2026-09-30', '2026-11-01'])
  assert.deepEqual(intervals, [32, 30, 30])
  assert.equal(estimate, 30)
})

test('持续天数含首尾，间隔按相邻开始日', () => {
  assert.equal(durationDays('2026-10-03', '2026-10-07'), 5)
  assert.equal(durationDays('2026-10-03', null), null)

  const history = buildHistory([
    { id: 1, startDay: '2026-10-03', endDay: '2026-10-07' },
    { id: 2, startDay: '2026-11-01', endDay: null }
  ])
  assert.equal(history[0].id, 2)
  assert.equal(history[0].cycleDays, 29)
  assert.equal(history[0].durationDays, null)
  assert.equal(history[1].cycleDays, null)
})

test('当前状态只认已确认区间', () => {
  assert.equal(currentStatus([], '2026-11-18').message, '还没有经期记录')
  const inPeriod = currentStatus([{ startDay: '2026-11-17', endDay: null }], '2026-11-18')
  assert.equal(inPeriod.inPeriod, true)
  assert.equal(inPeriod.message, '经期第 2 天')
  const ended = currentStatus([{ startDay: '2026-11-01', endDay: '2026-11-05' }], '2026-11-18')
  assert.equal(ended.inPeriod, false)
  assert.equal(ended.message, '最近一次经期开始 2026-11-01')
})

test('月份切换同步选中日，历史未结束记录不覆盖较新周期', () => {
  const rows = [
    { start_day: '2026-11-03', end_day: '2026-11-06' },
    { start_day: '2026-10-06', end_day: null }
  ]
  assert.equal(selectedDayInMonth('2026-10-01', '2026-11-18'), '2026-10-01')
  assert.equal(selectedDayInMonth('2026-11-01', '2026-11-18'), '2026-11-18')
  assert.equal(openPeriodOnDay(rows, '2026-10-07'), rows[1])
  assert.equal(openPeriodOnDay(rows, '2026-11-18'), null)
  assert.equal(periodOnDay(rows, '2026-10-07'), null)
  assert.equal(periodOnDay(rows, '2026-11-06'), rows[0])
  assert.equal(currentStatus(rows.map(row => ({ startDay: row.start_day, endDay: row.end_day })), '2026-11-18').inPeriod, false)
})

test('本月小结按实际记录日期去重，支持按四类感受筛选', () => {
  const rows = [
    { day: '2026-11-02', symptoms: ['腹胀', '腹胀'], mood: '平静', flow: '少量' },
    { day: '2026-11-03', symptoms: ['腹胀'], flow: '少量', impact: '轻微影响' },
    { day: '2026-11-04', symptoms: [], mood: '平静' }
  ]
  assert.deepEqual(summarizeDiary(rows), {
    days: 3, symptoms: [{ label: '腹胀', days: 2 }], moods: [{ label: '平静', days: 2 }],
    flows: [{ label: '少量', days: 2 }], impacts: [{ label: '轻微影响', days: 1 }]
  })
  assert.deepEqual(rows.filter(row => matchesFeeling(row, { kind: 'mood', label: '平静' })).map(row => row.day),
    ['2026-11-02', '2026-11-04'])
  assert.equal(matchesFeeling(rows[2], { kind: 'symptom', label: '腹胀' }), false)
  assert.equal(matchesFeeling(rows[0], { kind: 'flow', label: '少量' }), true)
  assert.equal(matchesFeeling(rows[1], { kind: 'impact', label: '轻微影响' }), true)
  assert.equal(matchesFeeling(rows[0], { kind: 'impact', label: '轻微影响' }), false)
})

test('周期回顾排除缺失值，只取最近六个完整样本', () => {
  const rows = [null, 4, 5, null, 6, 5, 4, 5, 12].map((duration_days, i) => ({
    duration_days, cycle_days: i % 2 ? 28 : null
  }))
  assert.deepEqual(recentCycleStats(rows), { interval: { count: 4, min: 28, max: 28 }, duration: { count: 6, min: 4, max: 6 } })
  assert.deepEqual(recentCycleStats([]), { interval: null, duration: null })
})

test('日历提醒处理跨月和过期，文件只含通用提示与正确的 UTC 时间', () => {
  const day = reminderDay('2026-12-01', 2, '2026-11-28T01:00:00.000Z')
  assert.equal(day, '2026-11-29')
  assert.equal(reminderDay('2026-12-01', 2, '2026-11-29T01:00:00.000Z'), null)
  const file = createReminderCalendar(day!, 'sample-id', '2026-11-28T03:41:12.250Z')
  assert.match(file, /DTSTART:20261129T010000Z\r\n/)
  assert.match(file, /DTSTAMP:20261128T034112Z\r\n/)
  assert.match(file, /SUMMARY:个人日程提醒\r\nCLASS:PRIVATE/)
  assert.doesNotMatch(file, /经期|20261201/)
})

test('预测经期区间、排卵日与易孕期按同一套规则推导', () => {
  assert.equal(ovulationDay('2027-01-04'), '2026-12-21')
  assert.deepEqual(fertileWindow('2027-01-04'), { start_day: '2026-12-16', end_day: '2026-12-22' })
  assert.deepEqual(predictedRange('2027-01-04', 5), { start_day: '2027-01-04', end_day: '2027-01-08' })
  // 持续天数夹在 2–10 天
  assert.deepEqual(predictedRange('2027-01-04', 0), { start_day: '2027-01-04', end_day: '2027-01-05' })
  assert.deepEqual(predictedRange('2027-01-04', 42), { start_day: '2027-01-04', end_day: '2027-01-13' })
})

test('未记录且已过预计日时，预测区间从今天起顺延', () => {
  assert.deepEqual(scheduleRange('2027-01-04', '2027-01-01', 5),
    { start_day: '2027-01-04', end_day: '2027-01-08', overdue_days: 0 })
  assert.deepEqual(scheduleRange('2027-01-04', '2027-01-04', 5),
    { start_day: '2027-01-04', end_day: '2027-01-08', overdue_days: 0 })
  assert.deepEqual(scheduleRange('2027-01-04', '2027-01-09', 5),
    { start_day: '2027-01-09', end_day: '2027-01-13', overdue_days: 5 })
  // 顺延后永远不早于今天
  const late = scheduleRange('2026-12-29', '2027-02-10', 5)
  assert.equal(late.start_day, '2027-02-10')
  assert.equal(late.overdue_days, 43)
})

test('持续天数只取最近四段完整记录，缺省 5 天', () => {
  assert.equal(estimateDurationDays([]), 5)
  assert.equal(estimateDurationDays([{ startDay: '2026-11-01', endDay: null }]), 5)
  assert.equal(estimateDurationDays([
    { startDay: '2026-11-01', endDay: '2026-11-04' },
    { startDay: '2026-10-03', endDay: '2026-10-08' }
  ]), 5)
  assert.equal(estimateDurationDays([
    { startDay: '2027-01-01', endDay: '2027-01-07' },
    { startDay: '2026-12-01', endDay: '2026-12-02' },
    { startDay: '2026-11-01', endDay: '2026-11-03' },
    { startDay: '2026-10-01', endDay: '2026-10-06' },
    { startDay: '2026-09-01', endDay: '2026-09-20' }
  ]), 5)
  assert.equal(estimateDurationDays([
    { startDay: '2026-11-01', endDay: '2026-11-01' },
    { startDay: '2026-10-01', endDay: '2026-10-01' }
  ]), 2)
})

test('日历高亮优先级：经期 > 预测经期 > 排卵日 > 易孕期', () => {
  const periods = [{ start_day: '2026-12-02', end_day: '2026-12-04' }]
  const ctx = {
    today: '2026-12-10',
    periods,
    predictedRange: predictedRange('2027-01-04', 5),
    ovulationDay: ovulationDay('2027-01-04'),
    fertileWindow: fertileWindow('2027-01-04')
  }
  assert.equal(cycleDayRole('2026-12-03', ctx), 'actual')
  assert.equal(cycleDayRole('2027-01-05', ctx), 'predicted')
  assert.equal(cycleDayRole('2026-12-21', ctx), 'ovulation')
  assert.equal(cycleDayRole('2026-12-18', ctx), 'fertile')
  assert.equal(cycleDayRole('2026-12-25', ctx), '')
  // 未来日期不算实际经期
  assert.equal(cycleDayRole('2026-12-20', { ...ctx, periods: [{ start_day: '2026-12-20', end_day: null }] }), 'fertile')
  assert.equal(inRange('2027-01-08', predictedRange('2027-01-04', 5)), true)
  assert.equal(inRange('2027-01-09', predictedRange('2027-01-04', 5)), false)
})
