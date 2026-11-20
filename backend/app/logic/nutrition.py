"""饮食热量口径：关键词识菜、宏量营养素配比与能量差。

离线也要能用，所以先按常见中式份量做规则估算；接模型时由模型在同一结构上细化，
数字始终由服务端写入，用户不能直接改 kcal，避免手填一个「想看到的数」。
"""

from __future__ import annotations

from dataclasses import dataclass

CARB_ENERGY = 4
PROTEIN_ENERGY = 4
FAT_ENERGY = 9


@dataclass(frozen=True)
class FoodItem:
    name: str
    keywords: tuple[str, ...]
    kcal: int
    protein_g: int
    carb_g: int
    fat_g: int
    portion: str


@dataclass(frozen=True)
class MealEstimate:
    items: list[FoodItem]
    kcal: int
    protein_g: int
    carb_g: int
    fat_g: int
    confidence: str
    note: str


# 常见一份的量，单位 kcal / 克；份量写在 portion 里，界面上必须和数字一起展示。
FOOD_TABLE: tuple[FoodItem, ...] = (
    FoodItem("米饭", ("米饭", "白饭", "盖饭", "米线"), 232, 4, 52, 1, "一碗约 150g"),
    FoodItem("面条", ("面条", "拉面", "拌面", "汤面"), 280, 9, 55, 3, "一碗约 200g"),
    FoodItem("全麦面包", ("全麦", "全麦面包"), 130, 5, 24, 2, "两片约 60g"),
    FoodItem("白粥", ("白粥", "粥", "稀饭"), 90, 2, 20, 0, "一碗约 250g"),
    FoodItem("包子", ("包子", "馒头", "花卷"), 220, 6, 42, 3, "一个约 100g"),
    FoodItem("鸡蛋", ("鸡蛋", "水煮蛋", "煎蛋"), 78, 6, 1, 5, "一个约 50g"),
    FoodItem("牛奶", ("牛奶", "酸奶"), 130, 7, 10, 7, "一杯约 250ml"),
    FoodItem("豆浆", ("豆浆",), 80, 6, 6, 3, "一杯约 250ml"),
    FoodItem("鸡胸肉", ("鸡胸", "鸡胸肉", "鸡胸肉片"), 165, 31, 0, 4, "一块约 100g"),
    FoodItem("牛肉", ("牛肉", "牛腩", "肥牛"), 250, 26, 0, 16, "一份约 100g"),
    FoodItem("鱼虾", ("鱼", "虾", "三文鱼", "龙利鱼"), 140, 20, 0, 6, "一份约 100g"),
    FoodItem("豆腐", ("豆腐", "豆干"), 90, 9, 3, 5, "一块约 100g"),
    FoodItem("沙拉", ("沙拉", "轻食", "蔬菜沙拉"), 120, 4, 12, 6, "一份约 200g"),
    FoodItem("炒青菜", ("青菜", "小炒", "炒时蔬", "西兰花"), 110, 3, 8, 7, "一盘约 200g"),
    FoodItem("苹果", ("苹果",), 90, 0, 24, 0, "一个约 200g"),
    FoodItem("香蕉", ("香蕉",), 90, 1, 22, 0, "一根约 100g"),
    FoodItem("坚果", ("坚果", "杏仁", "核桃", "腰果"), 180, 5, 6, 16, "一小把约 30g"),
    FoodItem("火锅", ("火锅", "麻辣烫", "串串"), 800, 30, 45, 55, "一人份约 500g"),
    FoodItem("炸鸡", ("炸鸡", "鸡排", "薯条"), 600, 25, 40, 38, "一份约 200g"),
    FoodItem("汉堡", ("汉堡", "三明治"), 500, 22, 45, 26, "一个约 200g"),
    FoodItem("奶茶", ("奶茶", "珍珠奶茶"), 380, 4, 60, 14, "一杯约 500ml"),
    FoodItem("拿铁", ("拿铁", "咖啡", "美式"), 120, 6, 10, 6, "一杯约 350ml"),
    FoodItem("蛋糕", ("蛋糕", "甜点", "面包店"), 350, 4, 45, 17, "一块约 100g"),
    FoodItem("烧烤", ("烧烤", "烤串"), 520, 28, 12, 40, "一份约 200g"),
    FoodItem("啤酒", ("啤酒", "果酒", "白酒"), 150, 1, 12, 0, "一瓶约 500ml"),
)

MEAL_TYPES = ("早餐", "午餐", "晚餐", "加餐")


def estimate_by_text(text: str) -> MealEstimate:
    """按关键词命中的最长词匹配食物，一样食物只计一次。"""

    cleaned = text.strip()
    if not cleaned:
        return MealEstimate([], 0, 0, 0, 0, "none", "先写一句吃了什么，例如「一碗牛肉面和一个鸡蛋」。")

    matched: dict[str, tuple[int, FoodItem]] = {}
    for item in FOOD_TABLE:
        best = max((word for word in item.keywords if word in cleaned), key=len, default="")
        if best:
            matched[item.name] = (len(best), item)

    if not matched:
        return MealEstimate(
            [], 0, 0, 0, 0, "none",
            "没认出具体食物，可以换成常见说法，或到知识库看看一份大概多少热量。",
        )

    items = [item for _, item in sorted(matched.values(), key=lambda pair: -pair[0])]
    return MealEstimate(
        items=items,
        kcal=sum(item.kcal for item in items),
        protein_g=sum(item.protein_g for item in items),
        carb_g=sum(item.carb_g for item in items),
        fat_g=sum(item.fat_g for item in items),
        confidence="medium",
        note="按常见一份的份量估算，实际以食物称重和做法为准。",
    )


def macro_percent(protein_g: int, carb_g: int, fat_g: int) -> dict[str, float]:
    """供能比：指导原则建议碳水 50~60%、脂肪 20~30%、蛋白质 15~20%。"""

    carb = carb_g * CARB_ENERGY
    protein = protein_g * PROTEIN_ENERGY
    fat = fat_g * FAT_ENERGY
    total = carb + protein + fat
    if total <= 0:
        return {"carb": 0.0, "protein": 0.0, "fat": 0.0}
    return {
        "carb": round(carb / total * 100, 1),
        "protein": round(protein / total * 100, 1),
        "fat": round(fat / total * 100, 1),
    }


def energy_gap(intake_kcal: int, target_kcal: int | None) -> tuple[int | None, str]:
    """返回（剩余可用热量，文案）；没有目标时只报已摄入。"""

    if target_kcal is None:
        return None, f"今天已记录 {intake_kcal} kcal，补全身高和生日后可以算出个人摄入目标。"
    gap = target_kcal - intake_kcal
    if gap >= 0:
        return gap, f"今天还可以吃约 {gap} kcal，别为了留缺口跳过正餐。"
    return gap, f"今天超出目标约 {abs(gap)} kcal，明天回到正常节奏就好，不用补偿性节食。"
