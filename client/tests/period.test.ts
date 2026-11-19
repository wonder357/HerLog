import assert from 'node:assert/strict'
import { test } from 'node:test'

import { addDays, diffDays, formatMoment, monthGrid, shanghaiDayKey, toZonedIso } from '../src/shared/dates.ts'
import {
  buildHistory,
  currentStatus,
  durationDays,
  estimateCycleDays,
  predictNextStart
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
  assert.equal(overdue.expectedStart, '2026-12-29')
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
