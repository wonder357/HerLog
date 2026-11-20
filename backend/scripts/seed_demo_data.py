"""她记演示数据种子脚本。

生成四类差异化演示账号，密码统一为 ``12345678``：
- ``xiaonan``  体重型：密集体重曲线 + 减脂目标 + 饮食与运动打卡
- ``ayue``     经期型：多段周期 + 逐日经量/情绪/症状记录
- ``tangtang`` 皮肤型：皮肤观察照片 + 护肤日记
- ``niannian`` 全能型：体重/经期/皮肤/饮食/运动/基础体温全面记录

脚本幂等：重复执行会先清理这四个演示账号（以及探针账号 ``probe_zzz``）的全部数据，
再重新写入。不触碰其它既有账号。

用法（在 backend 目录下）::

    .venv\\Scripts\\python.exe scripts\\seed_demo_data.py

默认写入本地 SQLite ``herlog_local.db``；设置环境变量 ``DATABASE_URL`` 可切换到其它库。
"""

from __future__ import annotations

import io
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# 让脚本在任意目录下执行都能导入 app 包。
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, delete, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.logic import nutrition  # noqa: E402
from app.models.fertility import CyclePreference, FertilityDaily, FertilityTest  # noqa: E402
from app.models.herlog import (  # noqa: E402
    Feeling,
    Meal,
    Period,
    Profile,
    SkinObservation,
    Weight,
    WeightGoal,
    WeightPost,
)
from app.models.home import HomePreference  # noqa: E402
from app.models.member import MemberAuth, MemberAuthSession  # noqa: E402
from app.models.private_photo import CheckinPhoto, ProfilePhoto, WeightPhoto  # noqa: E402
from app.models.wellness import (  # noqa: E402
    Checkin,
    DiscussionReply,
    DiscussionReplyReport,
    GroupMembership,
    GroupReply,
    GroupShare,
    ShareReport,
    SkinJournal,
)

CN = timezone(timedelta(hours=8))
PASSWORD = "12345678"
ASSET_DIR = BACKEND_DIR / "scripts" / "seed_assets" / "skin"

DEMO_USERNAMES = ["xiaonan", "ayue", "tangtang", "niannian"]
PROBE_USERNAMES = ["probe_zzz"]
ALL_TARGETS = DEMO_USERNAMES + PROBE_USERNAMES

ATTENTION = "下次可在相近光线和角度下拍摄同一部位，便于回看。"
MODEL_ID = "fixture:deepseek-flash"
PROMPT_VERSION = "herlog-skin-v2"


def local_dt(y: int, m: int, d: int, h: int = 8, mi: int = 0) -> datetime:
    """本地（长沙）时刻 → 库内存储的 UTC naive datetime。"""

    return datetime(y, m, d, h, mi, tzinfo=CN).astimezone(timezone.utc).replace(tzinfo=None)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_key(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:24]}"


# --------------------------------------------------------------------------- #
# 清理
# --------------------------------------------------------------------------- #

def cleanup(session: Session, customer_ids: set[str]) -> None:
    """按子表到父表的顺序删除指定会员的全部数据（SQLite 外键默认未开启）。"""

    if not customer_ids:
        return

    # 照片表以 record_id 关联父记录：先取父记录 id，再清照片，避免孤儿行残留。
    weight_ids = session.scalars(select(Weight.id).where(Weight.customer_id.in_(customer_ids))).all()
    checkin_ids = session.scalars(select(Checkin.id).where(Checkin.customer_id.in_(customer_ids))).all()
    if weight_ids:
        session.execute(delete(WeightPhoto).where(WeightPhoto.record_id.in_(weight_ids)))
    if checkin_ids:
        session.execute(delete(CheckinPhoto).where(CheckinPhoto.record_id.in_(checkin_ids)))
    session.execute(delete(ProfilePhoto).where(ProfilePhoto.record_id.in_(customer_ids)))

    for model in (
        MemberAuthSession,
        FertilityTest,
        FertilityDaily,
        DiscussionReply,
        DiscussionReplyReport,
        GroupReply,
        ShareReport,
        GroupShare,
        GroupMembership,
        Checkin,
        SkinJournal,
        SkinObservation,
        Meal,
        WeightGoal,
        Weight,
        Feeling,
        Period,
        HomePreference,
        CyclePreference,
    ):
        session.execute(delete(model).where(model.customer_id.in_(customer_ids)))
    # 经验广场帖子：作者可空，只删演示账号自己发的。
    session.execute(delete(WeightPost).where(WeightPost.customer_id.in_(customer_ids)))
    session.execute(delete(Profile).where(Profile.customer_id.in_(customer_ids)))
    session.execute(delete(MemberAuth).where(MemberAuth.customer_id.in_(customer_ids)))


def resolve_target_ids(session: Session) -> set[str]:
    rows = session.scalars(select(Profile.customer_id).where(Profile.username.in_(ALL_TARGETS))).all()
    return set(rows)


# --------------------------------------------------------------------------- #
# 成员与资料
# --------------------------------------------------------------------------- #

def create_member(session: Session, username: str, birthday: date | None, height: float | None) -> str:
    customer_id = uuid.uuid4().hex
    now = utc_now()
    session.add(
        MemberAuth(
            customer_id=customer_id,
            phone=None,
            org_id=None,
            password=hash_password(PASSWORD),
            status="active",
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        Profile(
            customer_id=customer_id,
            username=username,
            birthday=birthday,
            height_cm=height,
            contact_phone=None,
        )
    )
    return customer_id


def add_home_pref(
    session: Session,
    customer_id: str,
    *,
    period_reminder: bool,
    record_reminder: bool,
    weekly_target: int | None,
) -> None:
    session.add(
        HomePreference(
            customer_id=customer_id,
            period_reminder_enabled=period_reminder,
            record_reminder_enabled=record_reminder,
            weekly_record_days_target=weekly_target,
            show_focus=True,
            show_summary=True,
            show_questions=True,
            password_attempt_count=0,
            password_attempt_window=None,
        )
    )


# --------------------------------------------------------------------------- #
# 域数据写入助手
# --------------------------------------------------------------------------- #

def add_period(session: Session, cid: str, start: date, end: date | None) -> None:
    session.add(Period(customer_id=cid, start_day=start, end_day=end))


def add_feeling(
    session: Session,
    cid: str,
    day: date,
    flow: str | None,
    mood: str | None,
    symptoms: list[str],
    impact: str | None,
    note: str | None,
) -> None:
    session.add(
        Feeling(
            customer_id=cid,
            day=day,
            flow=flow,
            mood=mood,
            symptoms=symptoms,
            impact=impact,
            note=note,
        )
    )


def add_weight(
    session: Session,
    cid: str,
    day: date,
    kg: float,
    hh: int,
    mm: int,
    tag: str | None = None,
    note: str | None = None,
    feeling_tags: list[str] | None = None,
) -> None:
    grams = int(round(kg * 1000))
    session.add(
        Weight(
            customer_id=cid,
            client_key=new_key("w"),
            grams=grams,
            measured_at=local_dt(day.year, day.month, day.day, hh, mm),
            tag=tag,
            note=note,
            feeling_tags=feeling_tags,
            source="manual",
            device_id=None,
            source_record_id=None,
        )
    )


def add_meal(
    session: Session,
    cid: str,
    day: date,
    meal_type: str,
    text: str,
    hh: int,
    mm: int,
) -> None:
    estimate = nutrition.estimate_by_text(text)
    session.add(
        Meal(
            customer_id=cid,
            client_key=new_key("m"),
            eaten_at=local_dt(day.year, day.month, day.day, hh, mm),
            meal_type=meal_type,
            text=text,
            kcal=estimate.kcal,
            protein_g=estimate.protein_g,
            carb_g=estimate.carb_g,
            fat_g=estimate.fat_g,
            estimate_source="fixture",
        )
    )


def add_checkin(
    session: Session,
    cid: str,
    day: date,
    activity: str,
    hh: int,
    mm: int,
    duration: int | None,
    effort: str | None,
    feeling: str | None,
) -> None:
    session.add(
        Checkin(
            customer_id=cid,
            client_key=new_key("c"),
            activity_code=activity,
            started_at=local_dt(day.year, day.month, day.day, hh, mm),
            duration_minutes=duration,
            effort=effort,
            feeling_code=feeling,
        )
    )


def add_skin_journal(
    session: Session,
    cid: str,
    day: date,
    skin_type: str | None,
    comfort: int | None,
    sensations: list[str],
    routine: list[str],
    note: str | None,
) -> None:
    session.add(
        SkinJournal(
            customer_id=cid,
            day=day,
            skin_type=skin_type,
            comfort=comfort,
            sensations=sensations,
            routine=routine,
            note=note,
        )
    )


def _load_skin_image(filename: str) -> bytes:
    """压缩皮肤照片到最长边 768、JPEG q82，返回入库字节。"""

    from PIL import Image, ImageOps

    path = ASSET_DIR / filename
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((768, 768), Image.Resampling.LANCZOS)
        rgb = image.convert("RGB")
        clean = Image.new("RGB", rgb.size)
        clean.paste(rgb)
        buffer = io.BytesIO()
        clean.save(buffer, "JPEG", quality=82)
    data = buffer.getvalue()
    if len(data) > 3 * 1024 * 1024:
        raise RuntimeError(f"皮肤图片超出 3 MiB 限制: {filename}")
    return data


def add_skin_observation(
    session: Session,
    cid: str,
    day: date,
    hh: int,
    mm: int,
    site: str,
    image_file: str,
    visible: str,
    unclear: str,
) -> None:
    session.add(
        SkinObservation(
            customer_id=cid,
            analysis_id=uuid.uuid4().hex,
            site=site,
            captured_at=local_dt(day.year, day.month, day.day, hh, mm),
            mime="image/jpeg",
            image_bytes=_load_skin_image(image_file),
            visible=visible,
            unclear=unclear,
            attention=ATTENTION,
            model_id=MODEL_ID,
            prompt_version=PROMPT_VERSION,
        )
    )


def add_fertility_daily(
    session: Session,
    cid: str,
    day: date,
    bbt_c: str | None,
    mucus: str | None,
    intercourse: bool | None,
    bbt_hh: int = 6,
    bbt_mm: int = 50,
) -> None:
    session.add(
        FertilityDaily(
            customer_id=cid,
            day=day,
            bbt_c=bbt_c,
            bbt_measured_at=local_dt(day.year, day.month, day.day, bbt_hh, bbt_mm) if bbt_c else None,
            cervical_mucus=mucus,
            intercourse_occurred=intercourse,
            revision=str(uuid.uuid4()),
            updated_at=utc_now(),
        )
    )


def add_lh_test(session: Session, cid: str, day: date, result: str, hh: int, mm: int) -> None:
    session.add(
        FertilityTest(
            customer_id=cid,
            day=day,
            measured_at=local_dt(day.year, day.month, day.day, hh, mm),
            result=result,
        )
    )


def add_post(
    session: Session,
    cid: str | None,
    nickname: str,
    tag: str,
    body: str,
    likes: int,
    created: datetime,
) -> None:
    session.add(
        WeightPost(
            customer_id=cid,
            nickname=nickname,
            tag=tag,
            body=body,
            like_count=likes,
            liked_by=[],
            official=False,
            created_at=created,
        )
    )


# --------------------------------------------------------------------------- #
# 四类演示账号
# --------------------------------------------------------------------------- #

def build_xiaonan(session: Session) -> str:
    """体重型：密集减脂曲线 + 目标 + 饮食 + 运动。"""

    cid = create_member(session, "xiaonan", date(2000, 5, 12), 162.00)
    add_home_pref(session, cid, period_reminder=True, record_reminder=True, weekly_target=5)

    # 减脂目标：起点 58.4kg → 目标 50.0kg，每周 0.5kg。
    session.add(
        WeightGoal(
            customer_id=cid,
            target_grams=50000,
            start_grams=58400,
            start_day=date(2026, 10, 1),
            weekly_rate_grams=500,
            created_at=utc_now(),
        )
    )

    # 体重：10-01 起每 1~2 天一次，整体由 58.4kg 缓降到 55.1kg，带小幅波动。
    import random

    rng = random.Random(42)
    start = date(2026, 10, 1)
    end = date(2026, 11, 20)
    day = start
    idx = 0
    feeling_pool = [None, ["comfortable"], ["tired"], ["bloating", "puffy"], ["comfortable"]]
    while day <= end:
        progress = (day - start).days / (end - start).days
        kg = 58.4 - 3.3 * progress + rng.uniform(-0.15, 0.15)
        note = None
        if day == date(2026, 11, 5):
            note = "经期前两天，身体有点水肿"
        add_weight(
            session, cid, day, round(kg, 2), 7, 30,
            tag="晨起空腹", note=note, feeling_tags=feeling_pool[idx % len(feeling_pool)],
        )
        day += timedelta(days=1 if idx % 2 == 0 else 2)
        idx += 1

    # 近 7 天饮食：清淡减脂餐。
    meals = [
        (date(2026, 11, 14), "早餐", "一杯牛奶、一个水煮蛋和两片全麦面包", 7, 30),
        (date(2026, 11, 14), "午餐", "一块鸡胸肉、一碗米饭和一盘炒青菜", 12, 20),
        (date(2026, 11, 14), "晚餐", "一份鱼虾、一碗米饭和一份蔬菜沙拉", 18, 30),
        (date(2026, 11, 15), "早餐", "一杯豆浆、一个鸡蛋", 7, 40),
        (date(2026, 11, 15), "午餐", "牛肉炒时蔬配一碗米饭", 12, 30),
        (date(2026, 11, 15), "加餐", "一个苹果", 15, 0),
        (date(2026, 11, 16), "早餐", "牛奶、水煮蛋和全麦面包", 7, 25),
        (date(2026, 11, 16), "午餐", "鸡胸肉沙拉加一碗米饭", 12, 10),
        (date(2026, 11, 17), "午餐", "清蒸鱼、炒西兰花和一碗米饭", 12, 25),
        (date(2026, 11, 17), "晚餐", "豆腐蔬菜汤和一小碗米饭", 18, 20),
        (date(2026, 11, 18), "早餐", "一杯牛奶、一个鸡蛋", 7, 35),
        (date(2026, 11, 18), "午餐", "鸡胸肉、米饭和炒青菜", 12, 15),
        (date(2026, 11, 18), "加餐", "一小把坚果", 16, 30),
        (date(2026, 11, 19), "早餐", "白粥配一个鸡蛋", 7, 30),
        (date(2026, 11, 19), "午餐", "鱼虾沙拉和全麦面包", 12, 20),
        (date(2026, 11, 20), "早餐", "牛奶、水煮蛋和两片全麦面包", 7, 30),
        (date(2026, 11, 20), "午餐", "鸡胸肉、一碗米饭和炒青菜", 12, 20),
    ]
    for day, mtype, text, hh, mm in meals:
        add_meal(session, cid, day, mtype, text, hh, mm)

    # 运动打卡。
    checkins = [
        (date(2026, 11, 6), "walk", 18, 30, 30, "easy", "comfortable"),
        (date(2026, 11, 9), "jog", 19, 0, 25, "moderate", "tired"),
        (date(2026, 11, 12), "yoga", 20, 0, 40, "easy", "comfortable"),
        (date(2026, 11, 15), "strength", 19, 30, 30, "moderate", "energetic"),
        (date(2026, 11, 18), "cycle", 18, 40, 35, "moderate", "comfortable"),
        (date(2026, 11, 19), "walk", 20, 0, 20, "easy", "comfortable"),
    ]
    for day, act, hh, mm, dur, effort, feeling in checkins:
        add_checkin(session, cid, day, act, hh, mm, dur, effort, feeling)

    # 两段经期与少量感受。
    add_period(session, cid, date(2026, 10, 8), date(2026, 10, 12))
    add_period(session, cid, date(2026, 11, 5), date(2026, 11, 9))
    add_feeling(session, cid, date(2026, 11, 5), "中等", "平静", ["腹痛", "疲惫"], "轻微影响", "第一天，肚子有点坠")
    add_feeling(session, cid, date(2026, 11, 6), "中等", "烦躁", ["腹胀", "腰酸"], "影响日常", None)
    add_feeling(session, cid, date(2026, 11, 7), "少量", "平静", ["疲惫"], "无影响", None)

    # 一条护肤日记（非重点）。
    add_skin_journal(
        session, cid, date(2026, 11, 18), "combination", 3, ["tight"],
        ["cleanse", "moisturize"], "换季脸颊有点紧，加强了保湿",
    )

    add_post(session, cid, "xiaonan", "减脂", "坚持记录一个多月，晨起空腹称重已经成习惯，体重慢慢往下走，继续保持节奏。", 12, local_dt(2026, 11, 19, 21, 0))
    return cid


def build_ayue(session: Session) -> str:
    """经期型：多段完整周期，逐日经量/情绪/症状/影响记录。"""

    cid = create_member(session, "ayue", date(1999, 8, 23), 165.00)
    add_home_pref(session, cid, period_reminder=True, record_reminder=False, weekly_target=None)
    session.add(CyclePreference(customer_id=cid, active_mode="period", seen_fertility=False))

    add_period(session, cid, date(2026, 9, 7), date(2026, 9, 11))
    add_period(session, cid, date(2026, 10, 5), date(2026, 10, 9))
    add_period(session, cid, date(2026, 11, 2), date(2026, 11, 6))

    feelings = [
        (date(2026, 9, 6), None, "紧张", ["乳房胀痛", "情绪变化"], "轻微影响", "快来了，胸有点胀，情绪也敏感"),
        (date(2026, 9, 7), "较多", "烦躁", ["腹痛", "腰酸", "疲惫"], "影响日常", "量偏大，肚子绞痛，请假在家休息"),
        (date(2026, 9, 8), "较多", "低落", ["腹痛", "疲惫"], "影响睡眠", "夜里疼醒两次，睡得不好"),
        (date(2026, 9, 9), "中等", "平静", ["腹胀", "腰酸"], "轻微影响", None),
        (date(2026, 9, 10), "中等", "轻松", ["疲惫"], "无影响", None),
        (date(2026, 9, 11), "少量", "轻松", [], "无影响", "基本干净了"),
        (date(2026, 10, 4), None, "紧张", ["乳房胀痛"], "轻微影响", "经前乳房发胀，脾气有点急"),
        (date(2026, 10, 5), "中等", "烦躁", ["腹痛", "情绪变化"], "影响日常", None),
        (date(2026, 10, 6), "中等", "低落", ["头痛", "疲惫", "腹胀"], "轻微影响", "头有点沉，下午眯了一会儿"),
        (date(2026, 10, 7), "中等", "平静", ["腰酸"], "无影响", None),
        (date(2026, 10, 8), "少量", "平静", ["疲惫"], "无影响", None),
        (date(2026, 10, 9), "少量", "轻松", [], "无影响", None),
        (date(2026, 11, 1), None, "紧张", ["乳房胀痛", "情绪变化"], "轻微影响", "预感明天会来，情绪不太稳定"),
        (date(2026, 11, 2), "较多", "烦躁", ["腹痛", "腰酸", "恶心"], "影响日常", "这次来得突然，下腹坠痛明显"),
        (date(2026, 11, 3), "较多", "低落", ["腹痛", "疲惫"], "影响睡眠", "今晚热敷了肚子，希望能睡好"),
        (date(2026, 11, 4), "中等", "平静", ["腹胀", "头痛"], "轻微影响", None),
        (date(2026, 11, 5), "中等", "轻松", ["腰酸"], "无影响", "量在减少，状态回升"),
        (date(2026, 11, 6), "少量", "轻松", [], "无影响", None),
    ]
    for day, flow, mood, symptoms, impact, note in feelings:
        add_feeling(session, cid, day, flow, mood, symptoms, impact, note)

    # 零星体重（经前水肿 → 经后回落）。
    add_weight(session, cid, date(2026, 10, 5), 53.60, 8, 0)
    add_weight(session, cid, date(2026, 10, 20), 53.20, 8, 0)
    add_weight(session, cid, date(2026, 11, 2), 53.90, 8, 5, note="经前水肿")
    add_weight(session, cid, date(2026, 11, 16), 53.10, 8, 0)

    add_skin_journal(
        session, cid, date(2026, 11, 10), "dry", 3, ["tight", "rough"],
        ["cleanse", "moisturize"], "入秋后皮肤偏干，加强了保湿",
    )
    add_meal(session, cid, date(2026, 11, 18), "午餐", "一份牛肉配一碗米饭", 12, 30)
    add_meal(session, cid, date(2026, 11, 19), "加餐", "一个苹果", 15, 0)
    add_checkin(session, cid, date(2026, 11, 12), "walk", 19, 0, 20, "easy", "comfortable")
    return cid


def build_tangtang(session: Session) -> str:
    """皮肤型：皮肤观察照片 + 护肤日记为主体。"""

    cid = create_member(session, "tangtang", date(2001, 3, 30), 160.00)
    add_home_pref(session, cid, period_reminder=False, record_reminder=True, weekly_target=4)

    # 五次皮肤观察，对应五张生成素材，状态随护理进程变化。
    observations = [
        (date(2026, 10, 28), 9, 20, "面部", "face-healthy.jpg",
         "可见皮肤表面纹理。", "画面边缘的细节看不清。"),
        (date(2026, 11, 3), 20, 10, "额头", "forehead-oily.jpg",
         "可见局部反光。", "光线影响了部分区域的可见性。"),
        (date(2026, 11, 9), 21, 5, "脸颊", "cheek-dry.jpg",
         "可见局部表面细屑。", "较细的表面纹理看不清。"),
        (date(2026, 11, 14), 19, 40, "脸颊", "cheek-redness.jpg",
         "可见局部偏红区域。", "画面边缘的细节看不清。"),
        (date(2026, 11, 19), 22, 0, "下巴", "chin-bump.jpg",
         "可见局部轻微隆起。", "照片覆盖的观察区域有限。"),
    ]
    for day, hh, mm, site, image, visible, unclear in observations:
        add_skin_observation(session, cid, day, hh, mm, site, image, visible, unclear)

    journals = [
        (date(2026, 11, 3), "combination", 3, ["shine"], ["cleanse", "moisturize", "sunscreen"],
         "T 区出油、两颊偏干，中午补了一次防晒"),
        (date(2026, 11, 7), "dry", 2, ["tight", "rough"], ["cleanse", "moisturize"],
         "脸颊紧绷起皮，晚上厚涂了保湿霜"),
        (date(2026, 11, 11), "combination", 2, ["redness", "sensitive"], ["cleanse", "moisturize", "shade"],
         "换季泛红发痒，停了功效型产品"),
        (date(2026, 11, 15), "oily", 3, ["shine"], ["cleanse", "moisturize", "reapply"],
         "下巴冒了一颗痘，没有挤"),
        (date(2026, 11, 19), "combination", 4, [], ["cleanse", "moisturize", "sunscreen"],
         "这周坚持精简护肤，泛红消退了一些"),
    ]
    for day, stype, comfort, sensations, routine, note in journals:
        add_skin_journal(session, cid, day, stype, comfort, sensations, routine, note)

    add_period(session, cid, date(2026, 11, 1), date(2026, 11, 5))
    add_feeling(session, cid, date(2026, 11, 1), "中等", "平静", ["乳房胀痛"], "轻微影响", None)
    add_feeling(session, cid, date(2026, 11, 3), "少量", "轻松", ["疲惫"], "无影响", None)

    add_weight(session, cid, date(2026, 11, 1), 49.20, 8, 10)
    add_weight(session, cid, date(2026, 11, 15), 48.90, 8, 10)

    add_meal(session, cid, date(2026, 11, 18), "早餐", "一杯牛奶和一个水煮蛋", 7, 50)
    add_meal(session, cid, date(2026, 11, 19), "午餐", "一份蔬菜沙拉和一份鱼虾", 12, 20)
    add_checkin(session, cid, date(2026, 11, 16), "yoga", 19, 30, 30, "easy", "comfortable")
    return cid


def build_niannian(session: Session) -> str:
    """全能记录型：体重/经期/皮肤/饮食/运动/基础体温全面记录。"""

    cid = create_member(session, "niannian", date(1998, 11, 5), 168.00)
    add_home_pref(session, cid, period_reminder=True, record_reminder=True, weekly_target=6)
    session.add(CyclePreference(customer_id=cid, active_mode="period", seen_fertility=True))

    # 体重：近 30 天几乎每天一次，52.0~53.2kg 平稳波动。
    import random

    rng = random.Random(7)
    day = date(2026, 10, 22)
    idx = 0
    pool = [["comfortable"], None, ["tired"], ["comfortable"], ["puffy"]]
    while day <= date(2026, 11, 20):
        kg = 52.6 + rng.uniform(-0.5, 0.6)
        add_weight(session, cid, day, round(kg, 2), 7, 20, tag="晨起", feeling_tags=pool[idx % len(pool)])
        day += timedelta(days=1)
        idx += 1

    # 三段周期 + 经期感受。
    add_period(session, cid, date(2026, 9, 9), date(2026, 9, 13))
    add_period(session, cid, date(2026, 10, 7), date(2026, 10, 11))
    add_period(session, cid, date(2026, 11, 4), date(2026, 11, 8))
    period_feelings = [
        (date(2026, 10, 7), "中等", "平静", ["腹痛"], "轻微影响", "第一天，轻微坠痛"),
        (date(2026, 10, 8), "中等", "轻松", ["疲惫"], "无影响", None),
        (date(2026, 10, 9), "少量", "轻松", [], "无影响", None),
        (date(2026, 11, 4), "中等", "平静", ["腹痛", "乳房胀痛"], "轻微影响", None),
        (date(2026, 11, 5), "中等", "轻松", ["疲惫"], "无影响", None),
        (date(2026, 11, 6), "少量", "轻松", [], "无影响", None),
        (date(2026, 11, 7), "少量", "轻松", [], "无影响", "基本干净"),
    ]
    for row in period_feelings:
        add_feeling(session, cid, *row)

    # 两张皮肤观察 + 多条护肤日记。
    add_skin_observation(
        session, cid, date(2026, 11, 10), 9, 10, "面部", "face-calm.jpg",
        "可见皮肤表面纹理。", "较细的表面纹理看不清。",
    )
    add_skin_observation(
        session, cid, date(2026, 11, 17), 20, 30, "脸颊", "cheek-texture.jpg",
        "可见皮肤表面纹理。", "画面边缘的细节看不清。",
    )
    journals = [
        (date(2026, 11, 5), "balanced", 4, [], ["cleanse", "moisturize", "sunscreen"], "日常精简护理"),
        (date(2026, 11, 8), "combination", 3, ["shine"], ["cleanse", "moisturize"], "T 区略出油"),
        (date(2026, 11, 11), "balanced", 4, [], ["cleanse", "moisturize", "sunscreen"], "状态稳定"),
        (date(2026, 11, 14), "dry", 3, ["tight"], ["cleanse", "moisturize"], "空调房里偏干"),
        (date(2026, 11, 17), "combination", 4, ["rough"], ["cleanse", "moisturize", "reapply"], "额头有点粗糙"),
        (date(2026, 11, 19), "balanced", 5, [], ["cleanse", "moisturize", "sunscreen"], "今天皮肤状态很好"),
    ]
    for day, stype, comfort, sensations, routine, note in journals:
        add_skin_journal(session, cid, day, stype, comfort, sensations, routine, note)

    # 近 7 天三餐 + 加餐，种类更丰富。
    meals = [
        (date(2026, 11, 14), "早餐", "拿铁、全麦面包和一个鸡蛋", 7, 40),
        (date(2026, 11, 14), "午餐", "鸡胸肉、一碗米饭和炒青菜", 12, 20),
        (date(2026, 11, 14), "晚餐", "清蒸鱼、豆腐和一小碗米饭", 18, 30),
        (date(2026, 11, 15), "早餐", "白粥、鸡蛋和一杯豆浆", 7, 30),
        (date(2026, 11, 15), "午餐", "牛肉沙拉配两片全麦面包", 12, 15),
        (date(2026, 11, 15), "加餐", "一杯奶茶", 15, 30),
        (date(2026, 11, 16), "早餐", "牛奶、鸡蛋和全麦面包", 7, 35),
        (date(2026, 11, 16), "午餐", "鱼虾、西兰花和一碗米饭", 12, 25),
        (date(2026, 11, 16), "晚餐", "蔬菜豆腐汤和一个包子", 18, 20),
        (date(2026, 11, 17), "早餐", "拿铁和一个鸡蛋", 8, 0),
        (date(2026, 11, 17), "午餐", "鸡胸肉盖饭配炒时蔬", 12, 30),
        (date(2026, 11, 17), "加餐", "一块蛋糕", 16, 0),
        (date(2026, 11, 18), "早餐", "牛奶、水煮蛋和苹果", 7, 25),
        (date(2026, 11, 18), "午餐", "三文鱼、米饭和沙拉", 12, 20),
        (date(2026, 11, 18), "晚餐", "虾仁豆腐汤和一小碗米饭", 18, 25),
        (date(2026, 11, 19), "早餐", "豆浆、鸡蛋和全麦面包", 7, 40),
        (date(2026, 11, 19), "午餐", "牛肉炒青菜配米饭", 12, 20),
        (date(2026, 11, 19), "加餐", "一小把坚果和一根香蕉", 15, 0),
        (date(2026, 11, 20), "早餐", "牛奶、鸡蛋和两片全麦面包", 7, 30),
        (date(2026, 11, 20), "午餐", "鸡胸肉、米饭和炒青菜", 12, 20),
    ]
    for day, mtype, text, hh, mm in meals:
        add_meal(session, cid, day, mtype, text, hh, mm)

    # 一周运动打卡。
    checkins = [
        (date(2026, 11, 14), "walk", 8, 0, 30, "easy", "comfortable"),
        (date(2026, 11, 15), "yoga", 20, 0, 35, "easy", "comfortable"),
        (date(2026, 11, 16), "strength", 19, 0, 40, "moderate", "energetic"),
        (date(2026, 11, 18), "jog", 18, 30, 25, "moderate", "tired"),
        (date(2026, 11, 19), "dance", 19, 30, 30, "moderate", "energetic"),
    ]
    for day, act, hh, mm, dur, effort, feeling in checkins:
        add_checkin(session, cid, day, act, hh, mm, dur, effort, feeling)

    # 近 14 天基础体温与黏液观察（双相趋势），排卵前后两条 LH 试纸。
    bbt_map = {
        date(2026, 11, 7): ("36.45", "dry", None),
        date(2026, 11, 8): ("36.42", "sticky", None),
        date(2026, 11, 9): ("36.48", "creamy", None),
        date(2026, 11, 10): ("36.46", "creamy", None),
        date(2026, 11, 11): ("36.50", "watery", None),
        date(2026, 11, 12): ("36.52", "watery", None),
        date(2026, 11, 13): ("36.49", "stretchy", True),
        date(2026, 11, 14): ("36.68", "creamy", True),
        date(2026, 11, 15): ("36.71", "creamy", None),
        date(2026, 11, 16): ("36.74", "dry", None),
        date(2026, 11, 17): ("36.70", "dry", None),
        date(2026, 11, 18): ("36.72", "dry", None),
        date(2026, 11, 19): ("36.69", "unsure", None),
        date(2026, 11, 20): ("36.73", "dry", None),
    }
    for day, (bbt, mucus, intercourse) in bbt_map.items():
        add_fertility_daily(session, cid, day, bbt, mucus, intercourse)
    add_lh_test(session, cid, date(2026, 11, 12), "weak_positive", 8, 10)
    add_lh_test(session, cid, date(2026, 11, 13), "strong_positive", 8, 10)

    add_post(session, cid, "niannian", "打卡", "这周体重、饮食、运动和护肤都记全了，看着记录一点点变完整，很有成就感。", 21, local_dt(2026, 11, 20, 12, 0))
    return cid


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #

def _engine():
    url = os.environ.get("DATABASE_URL")
    if url:
        return create_engine(url, future=True)
    sqlite_path = BACKEND_DIR / "herlog_local.db"
    return create_engine(f"sqlite+pysqlite:///{sqlite_path.as_posix()}", future=True)


def _count(session: Session, model, cid: str) -> int:
    return session.query(model).filter(model.customer_id == cid).count()


def main() -> None:
    engine = _engine()
    with Session(engine, autoflush=False, expire_on_commit=False) as session:
        target_ids = resolve_target_ids(session)
        cleanup(session, target_ids)
        session.commit()

        built: dict[str, str] = {}
        built["xiaonan"] = build_xiaonan(session)
        built["ayue"] = build_ayue(session)
        built["tangtang"] = build_tangtang(session)
        built["niannian"] = build_niannian(session)
        session.commit()

        # 校验输出。
        print("演示账号已写入（密码统一：12345678）\n")
        summary_models = [
            ("体重", Weight),
            ("经期段", Period),
            ("感受", Feeling),
            ("饮食", Meal),
            ("运动打卡", Checkin),
            ("皮肤观察", SkinObservation),
            ("护肤日记", SkinJournal),
            ("体温记录", FertilityDaily),
        ]
        header = "用户名".ljust(12) + "".join(name.ljust(10) for name, _ in summary_models)
        print(header)
        for username, cid in built.items():
            row = username.ljust(12)
            for _, model in summary_models:
                row += str(_count(session, model, cid)).ljust(10)
            print(row)

        for username, cid in built.items():
            profile = session.get(Profile, cid)
            print(f"  - {username}  customer_id={cid} 身高={profile.height_cm} 生日={profile.birthday}")

    engine.dispose()
    print("\n完成。")


if __name__ == "__main__":
    main()
