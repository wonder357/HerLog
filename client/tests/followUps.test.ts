import assert from 'node:assert/strict'
import { test } from 'node:test'
import { suggestFollowUps } from '../src/shared/followUps.ts'

test('猜你想问最多三条，且不和已问过的重复', () => {
  const result = suggestFollowUps({ question: '经期总是推迟怎么办？', asked: ['经期总是推迟怎么办？'] })
  assert.equal(result.length, 3)
  assert.equal(new Set(result).size, 3)
  assert.ok(!result.includes('经期总是推迟怎么办？'))
})

test('命中话题的追问排在最前，问答里的关键词都算', () => {
  assert.match(suggestFollowUps({ question: '最近体重涨了', asked: [] })[0], /体重/)
  assert.match(suggestFollowUps({ question: '我想问点事', answer: '可以观察睡眠和作息。', asked: [] })[0], /睡眠/)
})

test('命中多个话题时段落按其得分高低排序', () => {
  const result = suggestFollowUps({ question: '经期前一天总是睡不好', answer: '可以记录睡眠情况。', asked: [] })
  assert.match(result[0], /经期/)
  assert.equal(result.length, 3)
})

test('没有命中话题时用通用问题补齐', () => {
  const result = suggestFollowUps({ question: '你好', asked: [] })
  assert.deepEqual(result, ['记录坚持不下来怎么办？', '哪些记录最有参考价值？', '记录多久能看出趋势？'])
})

test('已经问过的追问会被跳过并顺延下一条', () => {
  const asked = ['记录坚持不下来怎么办？', '哪些记录最有参考价值？']
  const result = suggestFollowUps({ question: '你好', asked })
  assert.equal(result[0], '记录多久能看出趋势？')
  assert.ok(!result.includes('记录坚持不下来怎么办？'))
})

test('可以只要两条', () => {
  assert.equal(suggestFollowUps({ question: '皮肤泛红', asked: [] }, 2).length, 2)
})
