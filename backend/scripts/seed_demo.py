"""四个展示账号的种子数据：密码统一为 12345678。

人物设定（同一个 App，四种使用重心）：

1. `xiaoman`  小满 · 体重管理型
   3 个月体重曲线（含平台期、外食反弹、同日两次记录）、减重目标、餐食估算、
   运动打卡与经验讨论、2 次经期、几乎不碰皮肤记录。
2. `yueer`    月儿 · 经期关注型
   9 次规律经期（预测可用）、近一个多月每天的经量/心情/症状/生活影响、
   极少体重与皮肤数据。
3. `xiaopi`   小皮 · 皮肤管理型
   10 条皮肤观察（含合成皮肤图，覆盖脸颊/额头/下巴/颈部）、16 天皮肤日记、
   少量体重与经期（经期预测仍提示“再记录几次”）。
4. `quanquan` 圈圈 · 全能记录型
   备孕模式 + 基础体温/排卵试纸/宫颈黏液、体重、经期、感受、皮肤观察与日记、
   餐食、运动、社区与讨论全都用起来。

用法（在仓库根目录执行）：
    .tools\\python\\python.exe backend\\scripts\\seed_demo.py
    .tools\\python\\python.exe backend\\scripts\\seed_demo.py --database-url sqlite+pysqlite:///backend/herlog_local.db

默认写本地 SQLite `backend/herlog_local.db`；也可用 --database-url 指向 MySQL。
同名的四个展示账号会被先清空再重建，所以可以反复执行。
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, delete, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app.models  # noqa: F401  注册全部表
from app.core.clock import local_today, to_utc_naive, utc_now
from app.core.security import hash_password
from app.db.base import Base
from app.models.fertility import CyclePreference, FertilityDaily, FertilityTest
from app.models.herlog import (
    Feeling,
    Meal,
    Period,
    Profile,
    SkinObservation,
    Weight,
    WeightGoal,
    WeightPost,
)
from app.models.home import HomePreference
from app.models.member import MemberAuth, MemberAuthSession
from app.models.private_photo import CheckinPhoto, ProfilePhoto, WeightPhoto
from app.models.wellness import (
    Checkin,
    DiscussionReply,
    DiscussionReplyReport,
    GroupMembership,
    GroupReply,
    GroupShare,
    ShareReport,
    SkinJournal,
)

import demo_skin_art as art

PASSWORD = "12345678"
DEMO_USERNAMES = ("xiaoman", "yueer", "xiaopi", "quanquan")
SKIN_MODEL_ID = "herlog-vision-v2"
PROMPT_VERSION = "herlog-skin-v2"

BREAKFASTS = (
    ("无糖豆浆 300ml + 全麦吐司 1 片 + 水煮蛋 1 个", 320, 18, 34, 12),
    ("燕麦 40g 用热牛奶冲泡，加一小把蓝莓", 300, 15, 42, 8),
    ("小米粥 + 半个咸鸭蛋 + 凉拌菠菜", 280, 12, 38, 9),
    ("希腊酸奶 150g + 坚果 10g + 半根香蕉", 290, 16, 30, 11),
)
LUNCHES = (
    ("糙米饭一小碗 + 清蒸鲈鱼 + 蒜蓉西兰花", 520, 34, 55, 16),
    ("荞麦面 + 卤鸡腿 + 凉拌黄瓜", 560, 32, 62, 18),
    ("食堂套餐：米饭半份 + 番茄炒蛋 + 青椒肉丝", 610, 28, 68, 22),
    ("藜麦沙拉 + 烤鸡胸 + 油醋汁", 480, 38, 40, 17),
)
DINNERS = (
    ("南瓜小米粥 + 虾仁炒芦笋", 380, 26, 40, 12),
    ("少油番茄牛腩 + 半碗米饭", 520, 30, 48, 20),
    ("清汤麻辣烫，多菜少丸子", 430, 24, 42, 17),
    ("蒸红薯 + 白灼虾 8 只 + 娃娃菜", 400, 28, 44, 10),
)
SNACKS = (
    ("无糖酸奶 + 5 颗杏仁", 150, 8, 12, 8),
    ("一小把圣女果", 60, 1, 12, 1),
)

WEIGHT_NOTES = (
    "昨晚外食，口味偏咸，今天脸有点肿。",
    "经期前一周，体重比平时高一点，先观察不调整。",
    "连续三天走路一万步，腰围松了一格。",
    "力量课第二天，肌肉有点酸，体重反而涨了。",
    "出差一周，只能保证早餐称重。",
    "睡够了 7 小时，早上起来轻了 0.2 kg。",
    "聚餐后回到正常饮食，两天就回来了。",
    "今天没运动，只是把晚饭换成了粥。",
)

CHECKIN_PLAN = (
    ("walk", "easy", "comfortable", 40),
    ("strength", "hard", "tired", 45),
    ("yoga", "easy", "energetic", 30),
    ("rest", None, None, None),
    ("jog", "moderate", "tired", 35),
    ("walk", "moderate", "comfortable", 50),
    ("cycle", "moderate", "energetic", 40),
)

FEELING_NOTES = (
    "第一天量多，下午腹部坠胀，早点睡了。",
    "第二天腰酸明显，用热水袋敷了一会儿。",
    "第三天量少下来，人也轻松些。",
    "经前一周容易烦躁，先记下来看看规律。",
    "今天状态不错，走了八千步也不累。",
    "下午有点头痛，喝了水、提前下班。",
    "情绪起伏和周期好像真的有关。",
    "今天没什么特别的感觉，只想留个记录。",
)

SKIN_JOURNAL_NOTES = (
    "换季第一周，先把酸类停了，只留清洁、保湿和防晒。",
    "熬夜到一点，第二天两颊有点泛红。",
    "新换的防晒不搓泥，继续观察。",
    "中午在户外走了 20 分钟，补涂了一次防晒。",
    "下巴有两点闭口，先不挤，继续记录。",
    "今天只做基础保湿，皮肤摸起来平了一点。",
    "运动出汗后马上洗了脸，没有刺痛。",
    "生理期前一周，皮肤比平时更容易出油。",
)

SKIN_TEXT = {
    "脸颊": {
        "mild": (
            "两侧脸颊的皮肤偏薄，能看到淡淡的红血丝和细小的毛孔，整体比较平整。",
            "鼻翼两侧的毛孔在照片里不太分辨得清。",
            "换季时脸颊容易泛红，可以先从减少清洁次数开始观察。",
        ),
        "flare": (
            "脸颊中段有一片泛红，红区里能看到 3～4 个突起的红色小点，毛孔偏明显。",
            "红点表面有没有白头，这张照片看不清。",
            "泛红和作息、经期都可能有关，连续记录一周再判断变化。",
        ),
    },
    "额头": {
        "mild": (
            "额头中部有油光，毛孔比脸颊略粗，靠发际线处有两三个闭口。",
            "闭口的颜色在光线下不太分得清。",
            "可以把额头单独拍一组，看看出油和闭口的关系。",
        ),
        "flare": (
            "额头一片泛油光，能看到 5 个以上小突起，部分发红。",
            "刘海遮挡的位置反光明显，细节看不清。",
            "如果最近换了护肤品，建议先在额头小范围试用。",
        ),
    },
    "下巴": {
        "mild": (
            "下巴偏下方有 3 处红色丘疹，其中一处略有白头，周围皮肤略暗。",
            "丘疹的边界在照片里有点模糊。",
            "下巴的位置和周期关系大，可以在经前多拍两张对比。",
        ),
        "flare": (
            "下巴密集出现 6 处红色丘疹，两处有明显白头，皮肤表面粗糙。",
            "部分丘疹被阴影挡住，看不清大小。",
            "先别挤，保持清洁和保湿，观察一周是否自行消退。",
        ),
    },
    "颈部": {
        "mild": (
            "颈部皮肤颜色比面部略深，左侧有一条浅浅的横向皮纹，整体光滑。",
            "皮纹尾端的细节看不清。",
            "颈部容易被忽略，涂面部产品时可以顺手带到。",
        ),
        "flare": (
            "颈部偏下方有轻度泛红，能看到细小的红色斑点。",
            "泛红范围在照片边缘处看不清。",
            "注意是不是项链或衣领摩擦引起的，方便的话换一件衣服再观察。",
        ),
    },
    "面部": {
        "mild": (
            "整体肤色偏亮，两颊有轻微红晕，额头和鼻翼的油光比较明显。",
            "鼻翼两侧的细节被反光盖住了一部分。",
            "同一角度、同一光线下每周拍一次，更容易看出变化。",
        ),
        "flare": (
            "面部整体泛红，两颊和下巴同时有几处红色小点，毛孔清晰。",
            "额头的高光处细节看不清。",
            "先记录这几天是否换季、熬夜或换了新产品，再决定要不要调整护肤。",
        ),
    },
}


def _local(day: date, hour: int, minute: int = 0) -> datetime:
    """本地日期+时间转库内 UTC naive。"""

    return to_utc_naive(datetime.combine(day, time(hour, minute)))


def _key() -> str:
    return uuid.uuid4().hex


class Demo:
    def __init__(self, today: date, session: Session) -> None:
        self.today = today
        self.session = session
        self.customers: dict[str, str] = {}
        self.members: dict[str, MemberAuth] = {}
        self.profiles: dict[str, Profile] = {}
        self.weight_ids: dict[str, list[int]] = {}
        self.posts: list[WeightPost] = []
        self.shares: list[GroupShare] = []
        self.counts: dict[str, dict[str, int]] = {}

    # ---------- 账号 ----------

    def add_member(self, username: str, birthday: date, height: str, phone: str, password_hash: str) -> None:
        customer_id = uuid.uuid4().hex
        now = utc_now()
        member = MemberAuth(
            customer_id=customer_id,
            phone=None,
            org_id=None,
            password=password_hash,
            status="active",
            created_at=now,
            updated_at=now,
        )
        profile = Profile(
            customer_id=customer_id,
            username=username,
            birthday=birthday,
            height_cm=Decimal(height),
            contact_phone=phone,
        )
        self.session.add(member)
        self.session.add(profile)
        self.customers[username] = customer_id
        self.members[username] = member
        self.profiles[username] = profile
        self.counts[username] = {}

    def bump(self, username: str, table: str, amount: int = 1) -> None:
        self.counts[username][table] = self.counts[username].get(table, 0) + amount

    # ---------- 小满：体重管理 ----------

    def build_weight_lover(self) -> None:
        name = "xiaoman"
        customer_id = self.customers[name]
        today = self.today
        rng = random.Random(20261120)

        self.session.add(
            HomePreference(
                customer_id=customer_id,
                period_reminder_enabled=True,
                record_reminder_enabled=True,
                weekly_record_days_target=5,
                show_focus=True,
                show_summary=True,
                show_questions=True,
            )
        )
        self.session.add(
            WeightGoal(
                customer_id=customer_id,
                target_grams=55000,
                start_grams=61400,
                start_day=today - timedelta(days=96),
                weekly_rate_grams=400,
                created_at=_local(today - timedelta(days=96), 9, 10),
            )
        )

        evening_offsets = {-18, -32, -45, -61, -77}
        pms_windows = ((-68, -57), (-38, -27))
        weights: list[Weight] = []
        for offset in range(-96, 1, 2):
            progress = (offset + 96) / 96
            base = 61.4 - 4.3 * progress + 0.32 * math.sin((offset + 96) / 9)
            if -46 <= offset <= -33:
                base += 0.28  # 平台期
            if -22 <= offset <= -14:
                base += 0.42  # 外食反弹
            grams = int(round((base + rng.uniform(-0.2, 0.2)) * 1000))
            in_pms = any(low <= offset <= high for low, high in pms_windows)
            tag = "经期前" if in_pms else "晨起"
            note = WEIGHT_NOTES[len(weights) % len(WEIGHT_NOTES)] if len(weights) % 6 == 0 else None
            feeling = ["bloating"] if in_pms else None
            row = Weight(
                customer_id=customer_id,
                client_key=_key(),
                grams=grams,
                measured_at=_local(today + timedelta(days=offset), 7, rng.choice((5, 12, 20, 28))),
                tag=tag,
                note=note,
                feeling_tags=feeling,
                source="manual",
            )
            weights.append(row)
            if offset in evening_offsets:
                weights.append(
                    Weight(
                        customer_id=customer_id,
                        client_key=_key(),
                        grams=grams + rng.randint(120, 380),
                        measured_at=_local(today + timedelta(days=offset), 20, rng.choice((10, 25, 40))),
                        tag="运动后",
                        note="练完回家顺手称一下，比早上重一点。",
                        feeling_tags=["tired"],
                        source="manual",
                    )
                )
        self.session.add_all(weights)
        self.bump(name, "weight", len(weights))
        self.bump(name, "weight_goal")

        meals: list[Meal] = []
        for offset in range(-8, 1):
            day = today + timedelta(days=offset)
            plan = ((7, "早餐", BREAKFASTS), (12, "午餐", LUNCHES), (19, "晚餐", DINNERS))
            for hour, meal_type, pool in plan:
                text, kcal, protein, carb, fat = pool[abs(offset) % len(pool)]
                meals.append(
                    Meal(
                        customer_id=customer_id,
                        client_key=_key(),
                        eaten_at=_local(day, hour, rng.choice((0, 15, 30, 45))),
                        meal_type=meal_type,
                        text=text,
                        kcal=kcal + rng.randint(-20, 25),
                        protein_g=protein,
                        carb_g=carb,
                        fat_g=fat,
                        estimate_source="fixture",
                    )
                )
            if offset % 2 == 0:
                text, kcal, protein, carb, fat = SNACKS[abs(offset) % len(SNACKS)]
                meals.append(
                    Meal(
                        customer_id=customer_id,
                        client_key=_key(),
                        eaten_at=_local(day, 16, 10),
                        meal_type="加餐",
                        text=text,
                        kcal=kcal,
                        protein_g=protein,
                        carb_g=carb,
                        fat_g=fat,
                        estimate_source="fixture",
                    )
                )
        self.session.add_all(meals)
        self.bump(name, "meal", len(meals))

        checkins: list[Checkin] = []
        for offset in range(-20, 1):
            if offset in (-3, -9, -15):
                continue
            code, effort, feeling, minutes = CHECKIN_PLAN[abs(offset) % len(CHECKIN_PLAN)]
            checkins.append(
                Checkin(
                    customer_id=customer_id,
                    client_key=_key(),
                    activity_code=code,
                    started_at=_local(today + timedelta(days=offset), 19, 10),
                    duration_minutes=minutes,
                    effort=effort,
                    feeling_code=feeling,
                )
            )
        self.session.add_all(checkins)
        self.bump(name, "checkin", len(checkins))

        periods = [
            Period(customer_id=customer_id, start_day=today - timedelta(days=64), end_day=today - timedelta(days=59)),
            Period(customer_id=customer_id, start_day=today - timedelta(days=35), end_day=today - timedelta(days=30)),
        ]
        self.session.add_all(periods)
        self.bump(name, "period", len(periods))

        feelings = [
            Feeling(
                customer_id=customer_id,
                day=today - timedelta(days=35),
                flow="较多",
                mood="烦躁",
                symptoms=["腹痛", "腰酸"],
                impact="影响日常",
                note="第一天只想躺着，晚饭喝了粥。",
            ),
            Feeling(
                customer_id=customer_id,
                day=today - timedelta(days=34),
                flow="中等",
                mood="低落",
                symptoms=["腹痛", "疲惫"],
                impact="轻微影响",
                note=None,
            ),
            Feeling(
                customer_id=customer_id,
                day=today - timedelta(days=33),
                flow="少量",
                mood="平静",
                symptoms=["腰酸"],
                impact="无影响",
                note="量少下来，晚上去散了步。",
            ),
            Feeling(
                customer_id=customer_id,
                day=today - timedelta(days=2),
                flow=None,
                mood="平静",
                symptoms=["腹胀"],
                impact="无影响",
                note="经前有点腹胀，体重也跟着高了一点。",
            ),
        ]
        self.session.add_all(feelings)
        self.bump(name, "feeling", len(feelings))

        self._community_post(
            name,
            [
                ("打卡", "这周把力量课从 2 次加到 3 次，体重没怎么动，但腰围小了一格，继续记下去看趋势。"),
                ("饮食", "把外卖的酱汁单独放之后，同样一份饭吃完更轻松，餐后也不困了。"),
            ],
        )
        self._discussion_post(name, [
            ("experience", "把通勤路换成快走之后", "每天提前一站下车快走 15 分钟，坚持了两周，晚上睡得更沉，第二天起床也没那么难。"),
            ("question", "力量训练后第二天该不该继续练", "昨天练了腿，今天上下楼梯有点酸，是继续做轻一点，还是干脆休息一天比较好？"),
        ])

    # ---------- 月儿：经期关注 ----------

    def build_cycle_lover(self) -> None:
        name = "yueer"
        customer_id = self.customers[name]
        today = self.today
        rng = random.Random(998877)

        self.session.add(
            HomePreference(
                customer_id=customer_id,
                period_reminder_enabled=True,
                record_reminder_enabled=False,
                weekly_record_days_target=7,
                show_focus=True,
                show_summary=True,
                show_questions=True,
            )
        )

        starts = [today - timedelta(days=8 + 29 * index) for index in range(9)]
        periods = [Period(customer_id=customer_id, start_day=start, end_day=start + timedelta(days=4)) for start in starts]
        self.session.add_all(periods)
        self.bump(name, "period", len(periods))

        period_days: dict[date, int] = {}
        for index, start in enumerate(starts):
            for day_index in range(5):
                period_days[start + timedelta(days=day_index)] = index

        luteal_days: set[date] = set()
        for start in starts:
            for back in range(1, 4):
                luteal_days.add(start - timedelta(days=back))

        feelings: list[Feeling] = []
        skipped = {today - timedelta(days=17), today - timedelta(days=6)}
        for offset in range(-48, 1):
            day = today + timedelta(days=offset)
            if day in skipped:
                continue
            if day in period_days:
                flow = ("较多", "中等", "中等", "少量", "少量")[(today - day).days % 5]
                mood = ("烦躁", "低落", "平静", "紧张", "轻松")[period_days[day] % 5]
                symptoms = [
                    ["腹痛", "腰酸"],
                    ["腹痛", "疲惫"],
                    ["腹胀"],
                    ["腰酸", "头痛"],
                    ["疲惫"],
                ][(day - starts[0]).days % 5]
                impact = ("影响日常", "轻微影响", "影响睡眠", "轻微影响", "无影响")[(day - starts[0]).days % 5]
                note = FEELING_NOTES[(day - starts[0]).days % len(FEELING_NOTES)] if (day - starts[0]).days % 3 == 0 else None
            elif day in luteal_days:
                flow = None
                mood = ("紧张", "烦躁", "低落")[offset % 3]
                symptoms = [["腹胀", "乳房胀痛"], ["情绪变化"], ["腹胀", "疲惫"]][abs(offset) % 3]
                impact = ("轻微影响", "无影响", "影响睡眠")[abs(offset) % 3]
                note = FEELING_NOTES[abs(offset) % len(FEELING_NOTES)] if abs(offset) % 5 == 0 else None
            else:
                flow = None
                mood = ("轻松", "平静")[abs(offset) % 2]
                symptoms = [] if abs(offset) % 3 else ["疲惫"]
                impact = "无影响"
                note = FEELING_NOTES[(abs(offset) + 4) % len(FEELING_NOTES)] if abs(offset) % 6 == 0 else None
            feelings.append(
                Feeling(
                    customer_id=customer_id,
                    day=day,
                    flow=flow,
                    mood=mood,
                    symptoms=symptoms,
                    impact=impact,
                    note=note,
                )
            )
        self.session.add_all(feelings)
        self.bump(name, "feeling", len(feelings))

        weights = [
            Weight(
                customer_id=customer_id,
                client_key=_key(),
                grams=grams,
                measured_at=_local(today - timedelta(days=offset), 7, 20),
                tag="晨起",
                note=note,
                feeling_tags=tags,
                source="manual",
            )
            for offset, grams, note, tags in (
                (45, 51200, None, None),
                (31, 50900, "经期结束后称一次，比上个月轻了一点。", None),
                (14, 51400, "经前水肿，先记着。", ["puffy"]),
                (2, 50700, None, ["comfortable"]),
            )
        ]
        self.session.add_all(weights)
        self.bump(name, "weight", len(weights))

        checkins = [
            Checkin(
                customer_id=customer_id,
                client_key=_key(),
                activity_code="walk",
                started_at=_local(today - timedelta(days=offset), 18, 30),
                duration_minutes=minutes,
                effort="easy",
                feeling_code="comfortable",
            )
            for offset, minutes in ((11, 30), (7, 40), (3, 25))
        ]
        self.session.add_all(checkins)
        self.bump(name, "checkin", len(checkins))

        journals = [
            SkinJournal(
                customer_id=customer_id,
                day=today - timedelta(days=offset),
                skin_type="combination",
                comfort=comfort,
                sensations=sensations,
                routine=["cleanse", "moisturize"],
                note=note,
            )
            for offset, comfort, sensations, note in (
                (12, 3, ["shine"], "经前出油变多，晚上多洗了一次脸。"),
                (4, 4, [], None),
            )
        ]
        self.session.add_all(journals)
        self.bump(name, "skin_journal", len(journals))

        self._community_post(name, [("心情", "这个月开始记经期感受，烦躁的那几天终于有迹可循，不是自己“脾气差”。")])

    # ---------- 小皮：皮肤管理 ----------

    def build_skin_lover(self) -> None:
        name = "xiaopi"
        customer_id = self.customers[name]
        today = self.today
        rng = random.Random(20260101)

        self.session.add(
            HomePreference(
                customer_id=customer_id,
                period_reminder_enabled=False,
                record_reminder_enabled=True,
                weekly_record_days_target=4,
                show_focus=True,
                show_summary=True,
                show_questions=True,
            )
        )

        plan = (
            ("脸颊", 2, "flare", -2, 8, 15),
            ("额头", 9, "mild", -5, 21, 40),
            ("下巴", 4, "flare", -7, 8, 5),
            ("脸颊", 3, "mild", -9, 22, 5),
            ("额头", 7, "flare", -14, 7, 55),
            ("下巴", 11, "mild", -21, 21, 20),
            ("脸颊", 5, "flare", -26, 8, 30),
            ("额头", 2, "mild", -33, 22, 10),
            ("颈部", 6, "mild", -40, 8, 0),
            ("脸颊", 1, "mild", -47, 21, 45),
        )
        observations: list[SkinObservation] = []
        for site, seed, severity, offset, hour, minute in plan:
            text = SKIN_TEXT[site][severity if severity in SKIN_TEXT[site] else "mild"]
            data = art.photo_bytes(site, seed, severity=severity)
            observations.append(
                SkinObservation(
                    customer_id=customer_id,
                    analysis_id=_key(),
                    site=site,
                    captured_at=_local(today + timedelta(days=offset), hour, minute),
                    mime="image/jpeg",
                    image_bytes=data,
                    visible=text[0],
                    unclear=text[1],
                    attention=text[2],
                    model_id=SKIN_MODEL_ID,
                    prompt_version=PROMPT_VERSION,
                )
            )
        self.session.add_all(observations)
        self.bump(name, "skin_observation", len(observations))

        journals: list[SkinJournal] = []
        routine_cycle = (
            ["cleanse", "moisturize", "sunscreen"],
            ["cleanse", "moisturize", "shade", "cover"],
            ["cleanse", "moisturize", "sunscreen", "reapply"],
            ["cleanse", "moisturize"],
        )
        for offset in range(-31, 0):
            if offset in (-27, -22, -16, -11, -5):
                continue
            comfort = (3, 4, 2, 4, 5, 3, 4)[abs(offset) % 7]
            journals.append(
                SkinJournal(
                    customer_id=customer_id,
                    day=today + timedelta(days=offset),
                    skin_type=("combination", "oily", "dry", "balanced")[abs(offset) % 4],
                    comfort=comfort,
                    sensations=(
                        ["redness"] if offset in (-2, -9) else ["tight"] if offset in (-3, -17) else [] if offset % 3 == 0 else ["shine"]
                    ),
                    routine=routine_cycle[abs(offset) % len(routine_cycle)],
                    note=SKIN_JOURNAL_NOTES[abs(offset) % len(SKIN_JOURNAL_NOTES)] if offset % 4 == 0 else None,
                )
            )
        self.session.add_all(journals)
        self.bump(name, "skin_journal", len(journals))

        periods = [
            Period(customer_id=customer_id, start_day=today - timedelta(days=days), end_day=today - timedelta(days=days - 4))
            for days in (52, 81, 110)
        ]
        self.session.add_all(periods)
        self.bump(name, "period", len(periods))

        feelings = [
            Feeling(
                customer_id=customer_id,
                day=today - timedelta(days=days),
                flow="中等" if index == 0 else "少量",
                mood=("烦躁", "平静", "低落")[index],
                symptoms=[["腹痛"], ["疲惫"], ["腹胀", "头痛"]][index],
                impact="轻微影响" if index == 0 else "无影响",
                note="下巴的痘和经期前一周几乎同步。" if index == 0 else None,
            )
            for index, days in enumerate((3, 9, 21))
        ]
        self.session.add_all(feelings)
        self.bump(name, "feeling", len(feelings))

        weights = [
            Weight(
                customer_id=customer_id,
                client_key=_key(),
                grams=grams,
                measured_at=_local(today - timedelta(days=offset), 8, rng.choice((5, 20, 35))),
                tag="晨起",
                note=None,
                feeling_tags=None,
                source="manual",
            )
            for offset, grams in ((30, 52800), (21, 52600), (12, 52400), (6, 52100), (1, 52000))
        ]
        self.session.add_all(weights)
        self.bump(name, "weight", len(weights))

        checkins = [
            Checkin(
                customer_id=customer_id,
                client_key=_key(),
                activity_code="yoga",
                started_at=_local(today - timedelta(days=days), 20, 15),
                duration_minutes=minutes,
                effort="easy",
                feeling_code="comfortable",
            )
            for days, minutes in ((5, 25), (18, 30))
        ]
        self.session.add_all(checkins)
        self.bump(name, "checkin", len(checkins))

        self._community_post(name, [("心情", "把每天的防晒和泛红记下来之后，才发现熬夜对皮肤的影响比换季更明显。")])

    # ---------- 圈圈：全能记录 ----------

    def build_everything(self) -> None:
        name = "quanquan"
        customer_id = self.customers[name]
        today = self.today
        rng = random.Random(520520)

        self.session.add(
            HomePreference(
                customer_id=customer_id,
                period_reminder_enabled=True,
                record_reminder_enabled=True,
                weekly_record_days_target=7,
                show_focus=True,
                show_summary=True,
                show_questions=True,
            )
        )
        self.session.add(
            CyclePreference(
                customer_id=customer_id,
                active_mode="trying_to_conceive",
                seen_fertility=True,
                trying_started_on=today - timedelta(days=150),
            )
        )
        self.session.add(
            WeightGoal(
                customer_id=customer_id,
                target_grams=58000,
                start_grams=63500,
                start_day=today - timedelta(days=110),
                weekly_rate_grams=350,
                created_at=_local(today - timedelta(days=110), 8, 40),
            )
        )

        starts = [today - timedelta(days=16 + 29 * index) for index in range(8)]
        self.session.add_all(
            [Period(customer_id=customer_id, start_day=start, end_day=start + timedelta(days=4)) for start in starts]
        )
        self.bump(name, "period", len(starts))

        weights: list[Weight] = []
        for offset in range(-110, 1):
            progress = (offset + 110) / 110
            base = 63.5 - 5.2 * progress + 0.3 * math.sin((offset + 110) / 8)
            grams = int(round((base + rng.uniform(-0.16, 0.16)) * 1000))
            weights.append(
                Weight(
                    customer_id=customer_id,
                    client_key=_key(),
                    grams=grams,
                    measured_at=_local(today + timedelta(days=offset), 6, rng.choice((40, 50, 55))),
                    tag="晨起",
                    note=WEIGHT_NOTES[abs(offset) % len(WEIGHT_NOTES)] if abs(offset) % 9 == 0 else None,
                    feeling_tags=["bloating"] if offset % 23 == 0 else ["comfortable"] if offset % 17 == 0 else None,
                    source="manual",
                )
            )
        for offset in (-4, -9, -16):
            weights.append(
                Weight(
                    customer_id=customer_id,
                    client_key=_key(),
                    grams=weights[offset + 110].grams + rng.randint(150, 320),
                    measured_at=_local(today + timedelta(days=offset), 20, 50),
                    tag="运动后",
                    note="练完称一次，和早上差 0.3 kg 左右。",
                    feeling_tags=["tired"],
                    source="manual",
                )
            )
        self.session.add_all(weights)
        self.bump(name, "weight", len(weights))

        feelings: list[Feeling] = []
        for offset in range(-46, 1):
            day = today + timedelta(days=offset)
            in_period = any((day - start).days in range(0, 5) for start in starts)
            in_luteal = any((start - day).days in range(1, 4) for start in starts)
            if in_period:
                index = (day - starts[0]).days % 5
                flow = ("中等", "较多", "中等", "少量", "少量")[index]
                mood = ("平静", "烦躁", "低落", "紧张", "轻松")[index]
                symptoms = [["腹痛"], ["腹痛", "腰酸"], ["腹胀"], ["疲惫"], ["头痛"]][index]
                impact = ("轻微影响", "影响日常", "影响睡眠", "轻微影响", "无影响")[index]
            elif in_luteal:
                flow = None
                mood = ("紧张", "烦躁", "低落")[abs(offset) % 3]
                symptoms = [["腹胀", "乳房胀痛"], ["情绪变化"], ["腹胀", "疲惫"]][abs(offset) % 3]
                impact = "轻微影响"
            else:
                flow = None
                mood = ("轻松", "平静")[abs(offset) % 2]
                symptoms = [] if abs(offset) % 4 else ["疲惫"]
                impact = "无影响"
            feelings.append(
                Feeling(
                    customer_id=customer_id,
                    day=day,
                    flow=flow,
                    mood=mood,
                    symptoms=symptoms,
                    impact=impact,
                    note=FEELING_NOTES[abs(offset) % len(FEELING_NOTES)] if abs(offset) % 5 == 0 else None,
                )
            )
        self.session.add_all(feelings)
        self.bump(name, "feeling", len(feelings))

        journals: list[SkinJournal] = []
        routine_cycle = (
            ["cleanse", "moisturize", "sunscreen"],
            ["cleanse", "moisturize", "sunscreen", "reapply"],
            ["cleanse", "moisturize", "shade", "cover"],
        )
        for offset in range(-40, 0):
            if offset in (-33, -28, -19, -13, -7, -2):
                continue
            journals.append(
                SkinJournal(
                    customer_id=customer_id,
                    day=today + timedelta(days=offset),
                    skin_type=("combination", "balanced", "oily", "dry")[abs(offset) % 4],
                    comfort=(4, 3, 5, 2, 4, 3)[abs(offset) % 6],
                    sensations=(["redness"] if offset in (-6, -21) else ["tight"] if offset in (-11, -37) else []) or (["shine"] if offset % 5 == 0 else []),
                    routine=routine_cycle[abs(offset) % len(routine_cycle)],
                    note=SKIN_JOURNAL_NOTES[abs(offset) % len(SKIN_JOURNAL_NOTES)] if offset % 5 == 0 else None,
                )
            )
        self.session.add_all(journals)
        self.bump(name, "skin_journal", len(journals))

        skin_plan = (
            ("面部", 12, "mild", -3, 8, 20),
            ("下巴", 13, "flare", -12, 8, 35),
            ("额头", 14, "mild", -20, 21, 50),
            ("脸颊", 15, "flare", -30, 8, 10),
            ("颈部", 16, "mild", -45, 8, 25),
            ("面部", 17, "mild", -58, 21, 15),
        )
        observations: list[SkinObservation] = []
        for site, seed, severity, offset, hour, minute in skin_plan:
            text = SKIN_TEXT[site][severity if severity in SKIN_TEXT[site] else "mild"]
            data = art.photo_bytes(site, seed, severity=severity, tone_shift=(-8, -4, -6))
            observations.append(
                SkinObservation(
                    customer_id=customer_id,
                    analysis_id=_key(),
                    site=site,
                    captured_at=_local(today + timedelta(days=offset), hour, minute),
                    mime="image/jpeg",
                    image_bytes=data,
                    visible=text[0],
                    unclear=text[1],
                    attention=text[2],
                    model_id=SKIN_MODEL_ID,
                    prompt_version=PROMPT_VERSION,
                )
            )
        self.session.add_all(observations)
        self.bump(name, "skin_observation", len(observations))

        meals: list[Meal] = []
        for offset in range(-9, 1):
            day = today + timedelta(days=offset)
            for hour, meal_type, pool in ((7, "早餐", BREAKFASTS), (12, "午餐", LUNCHES), (19, "晚餐", DINNERS)):
                text, kcal, protein, carb, fat = pool[abs(offset) % len(pool)]
                meals.append(
                    Meal(
                        customer_id=customer_id,
                        client_key=_key(),
                        eaten_at=_local(day, hour, rng.choice((0, 10, 20, 30))),
                        meal_type=meal_type,
                        text=text,
                        kcal=kcal + rng.randint(-15, 20),
                        protein_g=protein,
                        carb_g=carb,
                        fat_g=fat,
                        estimate_source="fixture",
                    )
                )
        self.session.add_all(meals)
        self.bump(name, "meal", len(meals))

        checkins: list[Checkin] = []
        for offset in range(-30, 1):
            if offset in (-24, -17):
                continue
            code, effort, feeling, minutes = CHECKIN_PLAN[abs(offset) % len(CHECKIN_PLAN)]
            checkins.append(
                Checkin(
                    customer_id=customer_id,
                    client_key=_key(),
                    activity_code=code,
                    started_at=_local(today + timedelta(days=offset), 19, 0),
                    duration_minutes=minutes,
                    effort=effort,
                    feeling_code=feeling,
                )
            )
        self.session.add_all(checkins)
        self.bump(name, "checkin", len(checkins))

        daily: list[FertilityDaily] = []
        tests: list[FertilityTest] = []
        bbt = {
            -21: 36.32, -20: 36.35, -19: 36.31, -18: 36.38, -17: 36.40,
            -16: 36.36, -15: 36.33, -14: 36.30, -13: 36.28, -12: 36.22,
            -11: 36.35, -10: 36.52, -9: 36.61, -8: 36.66, -7: 36.70,
            -6: 36.68, -5: 36.72, -4: 36.74, -3: 36.70, -2: 36.76,
        }
        mucus = {
            -21: "sticky", -20: "sticky", -19: "creamy", -18: "creamy", -17: "watery",
            -16: "watery", -15: "stretchy", -14: "stretchy", -13: "stretchy", -12: "watery",
            -11: "creamy", -10: "creamy", -9: "sticky", -8: "dry", -7: "dry",
            -6: "sticky", -5: "creamy", -4: "creamy", -3: "sticky", -2: "dry",
        }
        intercourse = {-14, -12, -11, -5}
        for offset, value in bbt.items():
            day = today + timedelta(days=offset)
            daily.append(
                FertilityDaily(
                    customer_id=customer_id,
                    day=day,
                    bbt_c=Decimal(str(value)),
                    bbt_measured_at=_local(day, 6, 40),
                    cervical_mucus=mucus[offset],
                    intercourse_occurred=offset in intercourse,
                    revision=_key(),
                    updated_at=_local(day, 7, 5),
                )
            )
        self.session.add_all(daily)
        self.session.flush()
        for offset, result, hour, minute in (
            (-13, "negative", 8, 0),
            (-12, "weak_positive", 8, 10),
            (-11, "strong_positive", 7, 30),
            (-10, "negative", 8, 20),
            (-5, "negative", 7, 50),
        ):
            day = today + timedelta(days=offset)
            tests.append(
                FertilityTest(
                    customer_id=customer_id,
                    day=day,
                    measured_at=_local(day, hour, minute),
                    result=result,
                )
            )
        self.session.add_all(tests)
        self.bump(name, "fertility_daily", len(daily))
        self.bump(name, "fertility_test", len(tests))

        self._community_post(
            name,
            [
                ("减脂", "三个月从 63.5 到 58 出头，最有用的是每天同一时间称重和把餐食记下来。"),
                ("健身", "把运动排进日历之后，一周三次就不再靠意志力硬撑了。"),
            ],
        )
        self._discussion_post(name, [
            ("checkin", "经期结束后恢复训练的第一天", "按自己的节奏先做了 20 分钟拉伸和散步，第二天再加重量，身体接受度更好。"),
            ("experience", "备孕期间把运动强度降下来", "把高强度间歇换成快走和瑜伽，睡眠反而更稳，记录体温也更有规律。"),
        ])

    # ---------- 公共社区 ----------

    def _community_post(self, username: str, items: list[tuple[str, str]]) -> None:
        customer_id = self.customers[username]
        for index, (tag, body) in enumerate(items):
            self.posts.append(
                WeightPost(
                    customer_id=customer_id,
                    nickname=self.profiles[username].username,
                    tag=tag,
                    body=body,
                    like_count=0,
                    liked_by=[],
                    official=False,
                    created_at=_local(self.today - timedelta(days=3 + index * 4), 21, 10),
                )
            )
        self.bump(username, "weight_post", len(items))

    def _discussion_post(self, username: str, items: list[tuple[str, str, str]]) -> None:
        customer_id = self.customers[username]
        for index, (category, title, body) in enumerate(items):
            share = GroupShare(
                public_id=_key(),
                customer_id=customer_id,
                topic="exercise",
                group_key="discussion",
                reference_key=_key(),
                client_key=_key(),
                snapshot={"category": category, "title": title, "body": body},
                status="published",
                published_at=_local(self.today - timedelta(days=2 + index * 5), 21, 30),
            )
            self.shares.append(share)
        self.bump(username, "discussion_post", len(items))

    def add_social(self) -> None:
        """点赞与他人的回复：让社区和讨论区看起来是活的。"""

        self.session.add_all(self.posts)
        self.session.flush()
        likers = [self.customers[name] for name in ("yueer", "xiaopi", "quanquan")]
        for index, post in enumerate(self.posts):
            selected = likers[: 1 + index % 3]
            post.liked_by = selected
            post.like_count = len(selected)

        reply_pool = (
            "我也有同感，记录比硬撑更有用。",
            "这个思路不错，我也试试看。",
            "今天照着做了一次，确实轻松一点。",
            "请问你一般练多久？想参考一下。",
            "谢谢分享，先收藏了。",
        )
        self.session.add_all(self.shares)
        self.session.flush()
        repliers = ("yueer", "xiaopi", "quanquan", "xiaoman")
        for index, share in enumerate(self.shares):
            author = next(name for name, cid in self.customers.items() if cid == share.customer_id)
            for step in range(1 + index % 2):
                replier = next(name for name in repliers if name != author)
                self.session.add(
                    DiscussionReply(
                        public_id=_key(),
                        share_id=share.id,
                        customer_id=self.customers[replier],
                        client_key=_key(),
                        body=reply_pool[(index + step) % len(reply_pool)],
                        status="published",
                        published_at=_local(self.today - timedelta(days=1 + step), 20, 15 + step),
                    )
                )


# ---------- 清理与写库 ----------

def purge(session: Session, usernames: tuple[str, ...]) -> None:
    customer_ids = list(
        session.scalars(select(Profile.customer_id).where(Profile.username.in_(usernames)))
    )
    if not customer_ids:
        return

    weight_ids = list(session.scalars(select(Weight.id).where(Weight.customer_id.in_(customer_ids))))
    checkin_ids = list(session.scalars(select(Checkin.id).where(Checkin.customer_id.in_(customer_ids))))
    share_ids = list(session.scalars(select(GroupShare.id).where(GroupShare.customer_id.in_(customer_ids))))
    reply_ids = list(session.scalars(select(DiscussionReply.id).where(DiscussionReply.share_id.in_(share_ids))))
    other_reply_ids = list(session.scalars(select(DiscussionReply.id).where(DiscussionReply.customer_id.in_(customer_ids))))

    def clear(model, condition) -> None:
        session.execute(delete(model).where(condition))

    if reply_ids or other_reply_ids:
        ids = list(set(reply_ids + other_reply_ids))
        clear(DiscussionReplyReport, DiscussionReplyReport.reply_id.in_(ids))
    if share_ids:
        clear(DiscussionReply, DiscussionReply.share_id.in_(share_ids))
        clear(ShareReport, ShareReport.share_id.in_(share_ids))
        clear(GroupReply, GroupReply.share_id.in_(share_ids))
    clear(DiscussionReply, DiscussionReply.customer_id.in_(customer_ids))
    clear(GroupShare, GroupShare.customer_id.in_(customer_ids))
    clear(GroupMembership, GroupMembership.customer_id.in_(customer_ids))
    clear(WeightPost, WeightPost.customer_id.in_(customer_ids))

    if weight_ids:
        clear(WeightPhoto, WeightPhoto.record_id.in_(weight_ids))
    if checkin_ids:
        clear(CheckinPhoto, CheckinPhoto.record_id.in_(checkin_ids))
    clear(ProfilePhoto, ProfilePhoto.record_id.in_(customer_ids))

    clear(FertilityTest, FertilityTest.customer_id.in_(customer_ids))
    clear(FertilityDaily, FertilityDaily.customer_id.in_(customer_ids))
    clear(CyclePreference, CyclePreference.customer_id.in_(customer_ids))
    clear(SkinObservation, SkinObservation.customer_id.in_(customer_ids))
    clear(SkinJournal, SkinJournal.customer_id.in_(customer_ids))
    clear(Meal, Meal.customer_id.in_(customer_ids))
    clear(WeightGoal, WeightGoal.customer_id.in_(customer_ids))
    clear(Feeling, Feeling.customer_id.in_(customer_ids))
    clear(Period, Period.customer_id.in_(customer_ids))
    clear(Weight, Weight.customer_id.in_(customer_ids))
    clear(Checkin, Checkin.customer_id.in_(customer_ids))
    clear(HomePreference, HomePreference.customer_id.in_(customer_ids))
    clear(MemberAuthSession, MemberAuthSession.customer_id.in_(customer_ids))
    clear(Profile, Profile.customer_id.in_(customer_ids))
    clear(MemberAuth, MemberAuth.customer_id.in_(customer_ids))

    # 别人的帖子里如果点过赞，把展示账号的痕迹去掉。
    for post in session.scalars(select(WeightPost).where(WeightPost.customer_id.is_(None))):
        liked = [cid for cid in (post.liked_by or []) if cid not in customer_ids]
        if len(liked) != len(post.liked_by or []):
            post.liked_by = liked
            post.like_count = len(liked)
    session.commit()


def resolve_url(explicit: str | None) -> str:
    for candidate in (explicit, os.environ.get("HERLOG_DEMO_DATABASE_URL"), os.environ.get("DATABASE_URL")):
        if candidate:
            return candidate
    return f"sqlite+pysqlite:///{(BACKEND / 'herlog_local.db').as_posix()}"


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False}, future=True)
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, future=True)


def seed(url: str) -> dict[str, dict[str, int]]:
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)()
    try:
        purge(session, DEMO_USERNAMES)
        demo = Demo(local_today(), session)
        password_hash = hash_password(PASSWORD)
        demo.add_member("xiaoman", date(1996, 8, 12), "163.0", "13800001001", password_hash)
        demo.add_member("yueer", date(1999, 3, 5), "158.0", "13800001002", password_hash)
        demo.add_member("xiaopi", date(2001, 11, 2), "165.0", "13800001003", password_hash)
        demo.add_member("quanquan", date(1994, 6, 18), "168.0", "13800001004", password_hash)
        session.flush()

        demo.build_weight_lover()
        demo.build_cycle_lover()
        demo.build_skin_lover()
        demo.build_everything()
        session.add_all(demo.posts)
        session.add_all(demo.shares)
        session.flush()
        demo.add_social()
        session.commit()
        return demo.counts
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


PERSONAS = {
    "xiaoman": "体重管理型：体重曲线 + 目标 + 餐食 + 运动",
    "yueer": "经期关注型：9 次经期 + 每天的感受记录",
    "xiaopi": "皮肤管理型：皮肤观察（含合成图）+ 皮肤日记",
    "quanquan": "全能记录型：备孕 + 体重 + 经期 + 皮肤 + 运动 + 餐食",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成她记的四个展示账号")
    parser.add_argument("--database-url", dest="database_url", help="目标库连接串，默认本地 SQLite")
    args = parser.parse_args()
    url = resolve_url(args.database_url)
    counts = seed(url)

    print(f"目标库：{url}")
    print(f"统一密码：{PASSWORD}")
    for username in DEMO_USERNAMES:
        detail = "  ".join(f"{table}={count}" for table, count in counts[username].items())
        print(f"- {username:<9} {PERSONAS[username]}")
        print(f"  {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
