import assert from 'node:assert/strict'
import { test } from 'node:test'
import { assistantStarters, assistantTitle, calendarMarks, suggestedQuestions } from '../src/shared/home.ts'

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

test('首页 DeepSeek 建议问题使用通用主题，对应阶段并与查记录的文案独立', () => {
  const prompts = assistantStarters('luteal', true, false)
  assert.deepEqual(prompts, ['回看经期估算时要留意什么？', '怎样读懂体重趋势？'])
  assert.notEqual(assistantStarters('menstrual', true, false)[0], prompts[0])
  assert.notEqual(prompts[0], suggestedQuestions('luteal', true, false)[0])
})

test('自动标题取主题，省略问题里的日期和手机号', () => {
  assert.equal(assistantTitle('我的电话是 13800000000，11 月 18 日开始记睡眠', 'general'), '关于睡眠记录')
  assert.equal(assistantTitle('查 2026 年 11 月 15 日', 'records'), '健康记录查询')
  assert.equal(assistantTitle('想了解 bmi', 'general'), '体重记录回顾')
})
