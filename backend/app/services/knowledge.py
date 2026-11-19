"""体重 tag 的知识库科普。内容口径来自《体重管理指导原则（2024 年版）》。

科普不是诊疗：每条都写明来源，并在页面上固定展示「不构成医疗建议」。
自媒体里的极端方法（断食、代餐替代三餐、只做有氧不吃主食）不收录。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    slug: str
    title: str
    tag: str
    summary: str
    body: tuple[str, ...]
    source: str
    minutes: int


TOPICS: tuple[Topic, ...] = (
    Topic(
        slug="bmi",
        title="先看 BMI：我到底算不算超重",
        tag="基础",
        summary="BMI = 体重(kg) ÷ 身高(m)²。中国成人 18.5~23.9 为正常，24~27.9 为超重，28 及以上为肥胖。",
        body=(
            "BMI 只是身高和体重的比值，看不出脂肪长在哪、肌肉有多少，所以它适合做初筛，不适合单独下结论。",
            "中心型肥胖还要看腰围：脂肪堆在腹部时，即使 BMI 不算高，代谢风险也会上升。",
            "孕产期、儿童青少年、80 岁以上高龄老人的判断标准与普通成人不同，不宜直接套用上面的切点。",
            "如果 BMI 达到 28 以上，或者合并高血压、高血糖、血脂异常，先做一次体检，再决定减重方案。",
        ),
        source="《体重管理指导原则（2024 年版）》一、体重的分类标准",
        minutes=3,
    ),
    Topic(
        slug="safe-rate",
        title="每周减多少才不伤身体",
        tag="基础",
        summary="每周 0.5~1 kg、每月 2~4 kg，6 个月减当前体重的 5%~15% 并维持，比速降更稳。",
        body=(
            "体重掉得太快，先掉的多半是水和肌肉，恢复饮食后很容易反弹。",
            "BMI 在 24~32.5 之间的人，可以从每周 0.5~1 kg 起步；BMI 在正常区间的人，速度减半更合适。",
            "BMI 达到 32.5 及以上时，按减轻当前体重的 5%、10%、15% 划分阶段目标，每阶段 3~6 个月。",
            "平台期超过两三周很常见，先检查记录是否连续、份量是否估大了，再考虑调整，而不是直接砍掉一餐。",
        ),
        source="《体重管理指导原则（2024 年版）》三、超重肥胖的干预和治疗",
        minutes=3,
    ),
    Topic(
        slug="energy-gap",
        title="热量缺口怎么算：吃多少才叫「少一点」",
        tag="饮食",
        summary="每日比总消耗少吃 500 kcal 左右，或减少 30% 总能量，且不要低于基础代谢。",
        body=(
            "总消耗 = 基础代谢 + 日常活动 + 运动，App 里的目标值按轻度活动估算，实际会因人而异。",
            "缺口不是越大越好：长期吃得太少会掉肌肉、掉头发、月经紊乱，也会更难坚持。",
            "三大营养素供能比参考：碳水 50%~60%、脂肪 20%~30%、蛋白质 15%~20%；高蛋白饮食的蛋白质供能比一般不超过 30%。",
            "记录一两天就够看出问题：真正让热量超标的常常是饮料、酱料和零食，而不是正餐。",
        ),
        source="《体重管理指导原则（2024 年版）》三（一）1. 膳食干预",
        minutes=4,
    ),
    Topic(
        slug="plate",
        title="一餐怎么配：把盘子分成三块",
        tag="饮食",
        summary="一半蔬菜、四分之一优质蛋白、四分之一主食，主食优先全谷杂豆。",
        body=(
            "蔬菜先占一半，主食控制在一拳到一拳半，蛋白质一掌心（鱼虾、去皮鸡肉、瘦肉、豆制品）。",
            "三餐能量分配参考：早餐约 30%、午餐约 40%、晚餐约 30%，不要把一天的额度全留给晚上。",
            "烹饪方式优先蒸、煮、炖、拌，少用煎炸；同样的食材，做法不同热量能差一倍。",
            "外卖挑「少油少盐 + 单独装酱」的组合，汤和酱汁不要全部吃干净。",
        ),
        source="《体重管理指导原则（2024 年版）》四（二）合理膳食",
        minutes=3,
    ),
    Topic(
        slug="exercise-dose",
        title="运动剂量：每周 150 分钟只是起点",
        tag="运动",
        summary="每周至少 150 分钟中等强度有氧 + 2~3 次抗阻训练；想长期控制体重，目标 250 分钟/周。",
        body=(
            "刚开始可以每天 10~30 分钟快走、骑车、跳操，习惯后再加时长和强度。",
            "抗阻训练（弹力带、哑铃、自重深蹲、俯卧撑）负责保住肌肉，减脂期尤其不能省。",
            "运动前热身、运动后拉伸，膝踝不适时先降强度，别硬顶。",
            "有基础疾病、正在服药或运动中出现胸闷头晕的人，先咨询医生再定计划。",
        ),
        source="《体重管理指导原则（2024 年版）》三（一）2. 运动干预",
        minutes=4,
    ),
    Topic(
        slug="water-weight",
        title="今天重了 1 斤，是长胖了吗",
        tag="心态",
        summary="一天内的体重波动主要来自水分、盐分和食物残渣，看 7 天移动平均更可靠。",
        body=(
            "吃咸了、经期前后、便秘、前一天运动量大，都会让体重在 0.5~2 kg 之间上下浮动。",
            "所以这个模块用「每天最后一次测量」画图，并给出 7 天移动平均，单点不作为结论。",
            "称重条件尽量固定：早晨起床排空后、空腹、同一台秤、同样的衣服。",
            "如果某天数字让你情绪很差，可以不看单日数值，只看一周平均的变化。",
        ),
        source="《体重管理指导原则（2024 年版）》四（一）自我监测",
        minutes=3,
    ),
    Topic(
        slug="period-weight",
        title="经期前后体重变重，要不要调整目标",
        tag="经期",
        summary="黄体期到经期前，水钠潴留常让体重上升 0.5~2 kg，经期结束后会回落。",
        body=(
            "这几天不需要为了数字减少进食，重点是保证蛋白质、铁和水分摄入。",
            "如果经期腹痛明显、经量异常，先处理经期问题，减重速度可以放慢。",
            "体重模块的「一条建议」会在记录断档或波动异常时提醒，但它不做因果归因。",
            "记录经期和体重两份数据，长期看更容易分辨「水重」和「脂肪变化」。",
        ),
        source="《体重管理指导原则（2024 年版）》二、体重管理相关评估（生活方式与特殊时期）",
        minutes=2,
    ),
    Topic(
        slug="when-doctor",
        title="什么时候该去看医生，而不是继续自己减",
        tag="基础",
        summary="BMI 达到 28 以上且生活方式干预 3~6 个月减不到 5%，或合并慢性病时，需要医学评估。",
        body=(
            "药物和手术都有明确适应证，必须在医生评估后决定，App 不做推荐也不卖产品。",
            "出现月经消失、持续脱发、明显乏力、心悸、暴食后催吐等情况，应尽快就医。",
            "短期内体重无原因快速下降，也需要排查其他疾病。",
            "本模块的所有内容都是科普与记录辅助，不构成诊断或治疗建议。",
        ),
        source="《体重管理指导原则（2024 年版）》三（二）医学治疗",
        minutes=3,
    ),
)

TAG_ORDER = ("基础", "饮食", "运动", "心态", "经期")


def list_topics(tag: str | None = None) -> list[Topic]:
    if tag:
        return [topic for topic in TOPICS if topic.tag == tag]
    return list(TOPICS)


def get_topic(slug: str) -> Topic | None:
    return next((topic for topic in TOPICS if topic.slug == slug), None)


def search(text: str, limit: int = 2) -> list[Topic]:
    """给教练对话做知识检索：标题摘要命中优先，正文命中次之。"""

    hits: list[tuple[int, Topic]] = []
    for topic in TOPICS:
        score = 0
        if topic.title in text:
            score += 5
        score += sum(1 for char in topic.tag if char in text)
        for word in (topic.summary[:12], topic.title[:6]):
            if word and word in text:
                score += 2
        if score > 0:
            hits.append((score, topic))
    hits.sort(key=lambda pair: (-pair[0], pair[1].slug))
    return [topic for _, topic in hits[:limit]]
