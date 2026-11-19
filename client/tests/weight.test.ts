import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  dailyPoints,
  formatDelta,
  formatKg,
  parseKgToGrams,
  suggestion,
  summarize,
  trendExample
} from '../src/shared/weight.ts'

const records = [
  { id: 1, grams: 56800, measuredAt: '2026-11-16T00:00:00Z' }, // 11-16 08:00 上海
  { id: 2, grams: 57000, measuredAt: '2026-11-16T13:00:00Z' }, // 11-16 21:00
  { id: 3, grams: 56600, measuredAt: '2026-11-18T00:00:00Z' } // 11-18 08:00
]

test('示例趋势跨年对齐所选范围，近一周与长范围共用同一组测量', () => {
  const short = trendExample(7, '2027-01-04')
  const long = trendExample(30, '2027-01-04')
  assert.equal(short.length, 7)
  assert.equal(short[0].day, '2026-12-29')
  assert.equal(short.at(-1)?.day, '2027-01-04')
  assert.equal(long.length, 27)
  assert.equal(long[0].day, '2026-12-06')
  assert.deepEqual(long.slice(-7), short)
})

test('kg 输入最多三位小数并转正整数克', () => {
  assert.equal(parseKgToGrams('56.8'), 56800)
  assert.equal(parseKgToGrams('56.800'), 56800)
  assert.equal(parseKgToGrams('0.001'), 1)
  for (const bad of ['56.8001', '0', '-1', 'abc', '']) {
    assert.throws(() => parseKgToGrams(bad), /体重/)
  }
})

test('同日取最后一次测量', () => {
  const points = dailyPoints(records)
  assert.equal(points.length, 2)
  assert.equal(points[0].day, '2026-11-16')
  assert.equal(points[0].grams, 57000)
  assert.equal(points[1].day, '2026-11-18')
  assert.equal(points[1].grams, 56600)
})

test('文档示例：三笔记录、两个点、−0.4 kg', () => {
  const summary = summarize(records, 7, '2026-11-18')
  assert.equal(summary.count, 3)
  assert.equal(summary.points.length, 2)
  assert.equal(summary.deltaGrams, -400)
  assert.equal(summary.latestGrams, 56600)
  assert.equal(formatKg(summary.latestGrams), '56.6')
  assert.equal(formatDelta(summary.deltaGrams), '-0.4 kg')
  assert.equal(suggestion(summary), '如果想比较长期变化，尽量在相近的时间和条件下称重。')
})

test('只有一天数据时不判断趋势', () => {
  const summary = summarize([records[1]], 30, '2026-11-18')
  assert.equal(summary.points.length, 1)
  assert.equal(summary.deltaGrams, null)
  assert.equal(suggestion(summary), '先继续记录几天，再来看看变化趋势。')
})

test('没有记录时不给建议', () => {
  const summary = summarize([], 7, '2026-11-18')
  assert.equal(summary.count, 0)
  assert.equal(summary.latestGrams, null)
  assert.equal(suggestion(summary), null)
})

test('范围外的记录不计入次数与图表', () => {
  const summary = summarize(records, 7, '2026-12-01')
  assert.equal(summary.count, 0)
  assert.equal(summary.latestGrams, 56600) // 最近体重取全历史
})
