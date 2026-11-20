import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  dailyPoints,
  formatDelta,
  formatKg,
  measureChange,
  pairCycleMeasurements,
  parseBodyFat,
  parseKgToGrams,
  suggestion,
  summarize
} from '../src/shared/weight.ts'

const records = [
  { id: 1, grams: 56800, measuredAt: '2026-11-16T00:00:00Z' }, // 11-16 08:00 上海
  { id: 2, grams: 57000, measuredAt: '2026-11-16T13:00:00Z' }, // 11-16 21:00
  { id: 3, grams: 56600, measuredAt: '2026-11-18T00:00:00Z' } // 11-18 08:00
]

test('可选体脂测量验证与百分点变化', () => {
  assert.equal(parseBodyFat('25.75'), '25.75')
  assert.equal(parseBodyFat(' '), null)
  for (const value of ['0', '100', '-25', '26.101', 'NaN']) assert.throws(() => parseBodyFat(value), /体脂率/)
  assert.equal(measureChange(26.7 - 27.25, 'body_fat_pct'), '−0.55 个百分点')
})

test('周期对比仅汇总同周期日双方有值的配对，阶段筛选不跨阶段补齐', () => {
  const current = [
    { cycle_day: 1, phase: 'menstrual', weight_kg: 57, bmi: 20.1, body_fat_pct: null },
    { cycle_day: 2, phase: 'menstrual', weight_kg: 58, bmi: 20.3, body_fat_pct: 25.5 },
    { cycle_day: 3, phase: 'follicular', weight_kg: 64, bmi: 22, body_fat_pct: 25 }
  ] as const
  const previous = [
    { cycle_day: 1, phase: 'menstrual', weight_kg: 58, bmi: 20.3, body_fat_pct: 26 },
    { cycle_day: 2, phase: 'follicular', weight_kg: 59, bmi: 20.6, body_fat_pct: 26.8 }
  ] as const
  const overall = pairCycleMeasurements([...current], [...previous], 'weight_kg')
  assert.deepEqual(overall.averages, { current: 57.5, previous: 58.5 })
  const stages = pairCycleMeasurements([...current], [...previous], 'weight_kg', 'menstrual')
  assert.equal(stages.pairs.length, 1)
  assert.equal(stages.averages, null)
  const fat = pairCycleMeasurements([...current], [...previous], 'body_fat_pct')
  assert.equal(fat.pairs.length, 1)
  assert.equal(fat.averages, null)
})

test('跨年的两个趋势范围使用相同的已保存测量', () => {
  const entries = [
    { id: 1, grams: 58200, measuredAt: '2026-12-06T07:00:00+08:00' },
    { id: 2, grams: 58500, measuredAt: '2026-12-29T07:00:00+08:00' },
    { id: 3, grams: 58400, measuredAt: '2027-01-04T07:00:00+08:00' }
  ]
  const short = summarize(entries, 7, '2027-01-04')
  const long = summarize(entries, 30, '2027-01-04')
  assert.deepEqual(short.points.map(point => point.day), ['2026-12-29', '2027-01-04'])
  assert.deepEqual(long.points.slice(-2), short.points)
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
