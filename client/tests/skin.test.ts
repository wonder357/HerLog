import assert from 'node:assert/strict'
import { test } from 'node:test'
import { chronologicalSkinPair, compareSkinRecords, groupSkinDays, selfAssessedSkinType, skinMonthRange } from '../src/shared/skin.ts'

const earlier = { id: 8, site: '下巴', captured_at: '2026-11-30T15:59:59Z' }
const later = { id: 4, site: '下巴', captured_at: '2026-11-30T16:00:00Z' }

test('肤质自评保留缺失与冲突状态，区分区域油光', () => {
  assert.equal(selfAssessedSkinType(null, 'often'), 'unsure')
  assert.equal(selfAssessedSkinType('all', 'often'), 'unsure')
  assert.equal(selfAssessedSkinType('all', 'rarely'), 'oily')
  assert.equal(selfAssessedSkinType('t_zone', 'often'), 'combination')
  assert.equal(selfAssessedSkinType('little', 'often'), 'dry')
  assert.equal(selfAssessedSkinType('little', 'rarely'), 'balanced')
})

test('皮肤月历按上海自然日归组，午夜后的记录进入下一月', () => {
  const sameDay = { ...later, id: 9 }
  const groups = groupSkinDays([sameDay, later, earlier])
  assert.deepEqual(groups.get('2026-11-30'), [earlier])
  assert.deepEqual(groups.get('2026-12-01'), [sameDay, later])
})

test('查询月界覆盖闰日与跨年', () => {
  assert.deepEqual(skinMonthRange('2024-02-15'), { from: '2024-02-01', to: '2024-02-29' })
  assert.deepEqual(skinMonthRange('2026-12-01'), { from: '2026-12-01', to: '2026-12-31' })
})

test('同部位对比支持跨月和同日多条', () => {
  assert.equal(compareSkinRecords(earlier, later), null)
  assert.equal(compareSkinRecords(later, { ...later, id: 5 }), null)
  assert.equal(compareSkinRecords(earlier, earlier), '请选择另一条记录')
  assert.equal(compareSkinRecords(earlier, { ...later, site: '额头' }), '请选择同一部位的另一条记录')
})

test('对比按拍摄时间从早到晚，同一时刻按记录 ID', () => {
  const tie = { ...later, id: 7 }
  assert.deepEqual(chronologicalSkinPair([later, earlier]), [earlier, later])
  assert.deepEqual(chronologicalSkinPair([tie, later]), [later, tie])
})
