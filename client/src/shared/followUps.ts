export interface FollowUpInput {
  question: string
  answer?: string
  asked: string[]
}

interface TopicRule {
  keywords: string[]
  questions: string[]
}

/** 话题关键词 -> 候选追问。命中越多越靠前，词在问题里权重高于在回答里。 */
const TOPIC_RULES: TopicRule[] = [
  {
    keywords: ['经期', '月经', '周期', '痛经', '排卵', '经前'],
    questions: ['经期不规律要重点记录哪些信息？', '经期前的情绪波动怎么记？', '痛经的程度怎样记录更清楚？']
  },
  {
    keywords: ['体重', '称重', '减重', '增重', '公斤', '斤'],
    questions: ['体重多久称一次更有参考意义？', '除了体重，还要一起记录什么？', '体重是看单日数字还是看趋势？']
  },
  {
    keywords: ['皮肤', '肤质', '泛红', '痘痘', '干燥', '出油', '防晒', '护肤'],
    questions: ['拍照记录皮肤要固定哪些条件？', '皮肤泛红可以怎样记录？', '护肤步骤需要一起记下来吗？']
  },
  {
    keywords: ['睡眠', '熬夜', '失眠', '作息', '入睡', '早醒'],
    questions: ['怎样记录睡眠才容易坚持？', '熬夜之后需要补记什么？', '入睡和醒来时间都要记吗？']
  },
  {
    keywords: ['饮食', '营养', '咖啡', '喝水', '三餐', '吃'],
    questions: ['饮食记录记到多细比较合适？', '外食的时候怎么记？', '记录饮食能看出什么趋势？']
  },
  {
    keywords: ['运动', '锻炼', '走路', '跑步', '瑜伽', '健身'],
    questions: ['运动后顺手记下什么最有价值？', '经期可以照常运动吗？', '运动量怎么记才看得懂？']
  },
  {
    keywords: ['情绪', '压力', '焦虑', '心情', '感受', '烦躁'],
    questions: ['情绪和身体感受可以一起记录吗？', '压力大的那几天重点记什么？', '情绪波动和周期有关系吗？']
  },
  {
    keywords: ['备孕', '受孕', '怀孕', '体温', '试纸'],
    questions: ['备孕期间要记录哪些指标？', '基础体温怎么测、怎么记？', '记录多久能看出规律？']
  }
]

const FALLBACK = ['记录坚持不下来怎么办？', '哪些记录最有参考价值？', '记录多久能看出趋势？']

function normalize(text: string): string {
  return text.replace(/\s+/g, '').replace(/[?？!！。.,，、:：]/g, '')
}

/**
 * 猜你想问：按最近一问一答里的话题关键词挑候追问，跳过已经问过的，
 * 命中话题排前面，不足时用通用问题补齐，最多返回 limit 条。
 */
export function suggestFollowUps(input: FollowUpInput, limit = 3): string[] {
  const asked = new Set(input.asked.map(normalize))
  const ranked = TOPIC_RULES
    .map(rule => ({
      rule,
      score: rule.keywords.reduce(
        (total, keyword) =>
          total + (input.question.includes(keyword) ? 2 : 0) + (input.answer?.includes(keyword) ? 1 : 0),
        0
      )
    }))
    .filter(item => item.score > 0)
    .sort((left, right) => right.score - left.score)

  const pool = ranked.flatMap(item => item.rule.questions).concat(FALLBACK)
  const result: string[] = []
  for (const question of pool) {
    const key = normalize(question)
    if (asked.has(key) || result.some(item => normalize(item) === key)) continue
    result.push(question)
    if (result.length === limit) break
  }
  return result
}
