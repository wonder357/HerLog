import assert from 'node:assert/strict'
import { test } from 'node:test'
import { cycleRanges, describeDay, equalObservations, shanghaiTime, temperatureSegments } from '../src/shared/fertility.ts'
import type { DailyValues } from '../src/shared/fertility.ts'

test('周期区间只用实际开始日，当前段截至今天', () => {
  assert.deepEqual(cycleRanges([
    { start_day: '2026-10-29' }, { start_day: '2026-11-25' }, { start_day: '2026-11-27' },
    { start_day: '2026-10-01' }, { start_day: '2026-10-01' }
  ], '2026-11-25'), [
    { from: '2026-11-25', to: '2026-11-25', days: null },
    { from: '2026-10-29', to: '2026-11-24', days: 27 },
    { from: '2026-10-01', to: '2026-10-28', days: 28 }
  ])
})

test('体温图只使用已记的原始点，缺失日期断开', () => {
  assert.deepEqual(temperatureSegments([
    { day: '2026-11-09', bbt_c: '36.44' },
    { day: '2026-11-06', bbt_c: '36.40' },
    { day: '2026-11-05', bbt_c: '36.30' },
    { day: '2026-11-08', bbt_c: null }
  ]), [
    [{ day: '2026-11-05', celsius: 36.3 }, { day: '2026-11-06', celsius: 36.4 }],
    [{ day: '2026-11-09', celsius: 36.44 }]
  ])
})

test('超时回查统一体温精度和时间格式，同房未记录与无保持独立', () => {
  const values: DailyValues = {
    bbt_c: '36.50', bbt_measured_at: '2026-11-08T06:08:00+08:00',
    lh_tests: [{ result: 'weak_positive', measured_at: null }],
    cervical_mucus: null, intercourse_occurred: false
  }
  assert.equal(equalObservations(values, { ...values, bbt_c: '36.5', bbt_measured_at: '2026-11-07T22:08:00Z' }), true)
  assert.equal(equalObservations(values, { ...values, intercourse_occurred: null }), false)
  assert.equal(shanghaiTime('2026-11-08T16:00:00Z'), '00:00')
  assert.match(describeDay(values), /弱阳（时间未记录）.*同房 无/)
})
