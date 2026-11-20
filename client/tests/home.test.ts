import assert from 'node:assert/strict'
import { test } from 'node:test'
import { calendarMarks, suggestedQuestions } from '../src/shared/home.ts'

test('日历以固定顺序提供四类组合标记，0 次皮肤不出标记', () => {
  assert.deepEqual(calendarMarks(true, { weight_kg: '58.2', skin_observation_count: 1, feeling_tags: ['平静'] }),
    ['period', 'weight', 'skin', 'feeling'])
  assert.deepEqual(calendarMarks(false, { weight_kg: null, skin_observation_count: 0, feeling_tags: [] }), [])
})

test('建议问题跟随阶段，至多两枚且只使用已有数据类别', () => {
  const luteal = suggestedQuestions('luteal', false, true)
  assert.equal(luteal[0], '下次经期大概什么时候？')
  assert.match(luteal[1], /皮肤/)
  assert.equal(suggestedQuestions('unknown', false, false).length, 1)
  assert.notEqual(suggestedQuestions('menstrual', true, true)[0], luteal[0])
})
