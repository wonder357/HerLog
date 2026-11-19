"""DeepSeek 调用示例：直接跑一遍 app 里的适配层。

用法（在仓库根目录执行）：
    .tools\\python\\python.exe backend\\scripts\\deepseek_smoke.py
    .tools\\python\\python.exe backend\\scripts\\deepseek_smoke.py chat json
    .tools\\python\\python.exe backend\\scripts\\deepseek_smoke.py skin --image pic\\xxx.jpg

密钥来源：环境变量 HERLOG_MODEL_API_KEY，其次 DEEPSEEK_API_KEY，最后读本地密钥文件
（默认 C:\\Users\\kunlunmeta\\Desktop\\密钥.txt，可用 DEEPSEEK_KEY_FILE 覆盖）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

DEFAULT_KEY_FILE = pathlib.Path(
    os.environ.get("DEEPSEEK_KEY_FILE", r"C:\Users\kunlunmeta\Desktop\密钥.txt")
)

FACTS = {
    "模块": "体重",
    "日期范围": "2026-11-12 至 2026-11-18",
    "记录天数": 2,
    "首次": "2026-11-12 08:10 57.2 kg",
    "最近": "2026-11-18 08:00 56.8 kg",
    "delta_kg": -0.4,
}


def load_key() -> None:
    if os.environ.get("HERLOG_MODEL_API_KEY"):
        return
    for candidate in (os.environ.get("DEEPSEEK_API_KEY"), _read(DEFAULT_KEY_FILE)):
        if candidate:
            os.environ["HERLOG_MODEL_API_KEY"] = candidate
            return
    raise SystemExit("缺少 API Key：设置 HERLOG_MODEL_API_KEY 或 DEEPSEEK_API_KEY")


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.is_file() else ""


async def case_chat() -> None:
    """最基础的一次调用：非思考模式 + 温度，适合固定口径的数据解读。"""

    from app.services.deepseek_client import chat

    result = await chat(
        [
            {"role": "system", "content": "你是健康记录助手，回答不超过两句话。"},
            {"role": "user", "content": "记录体重时，为什么建议每天固定时间测量？"},
        ],
        thinking=False,
        temperature=0.2,
        max_tokens=200,
    )
    show("chat", result.content, result.usage)


async def case_json() -> None:
    """结构化输出：把程序算好的数字交给模型复述，返回可校验的 JSON。"""

    from app.services.deepseek_client import chat_json

    data = await chat_json(
        [
            {"role": "system", "content": "你只输出 JSON，不要解释。"},
            {
                "role": "user",
                "content": (
                    f"事实：{json.dumps(FACTS, ensure_ascii=False)}\n"
                    '输出 {"summary": 一句中文总结, "delta_kg": 数字, "days": 记录天数}'
                ),
            },
        ],
        required=("summary", "delta_kg", "days"),
        thinking=False,
        temperature=0,
    )
    show("json", json.dumps(data, ensure_ascii=False), None)


async def case_stream() -> None:
    """流式 + 思考模式：思维链和正文分段输出，适合首页逐字上屏。"""

    from app.services.deepseek_client import chat_stream

    messages = [
        {"role": "system", "content": "你是健康记录助手，回答不超过三句话。"},
        {"role": "user", "content": "经期记录和体重记录分开保存有什么好处？"},
    ]
    print("\n=== stream ===")
    printed = ""
    async for chunk in chat_stream(messages, thinking=True, reasoning_effort="low"):
        for kind, text in (("思考", chunk.reasoning), ("正文", chunk.text)):
            if not text:
                continue
            if printed != kind:
                print(f"\n[{kind}] ", end="")
                printed = kind
            print(text, end="", flush=True)
    print("\n[done]")


async def case_qa() -> None:
    """首页只读问答：有记录时引用日期，无记录时明确说明。"""

    from app.services.herlog_ai import answer_question

    with_data = await answer_question(FACTS, "这周体重有变化吗？")
    show("qa/有记录", with_data, None)

    empty = await answer_question({}, "这周体重有变化吗？")
    show("qa/无记录", empty, None)

    guard = await answer_question(FACTS, "帮我记一下今天 56.5 kg")
    show("qa/写入引导", guard, None)


async def case_skin(image: pathlib.Path | None) -> None:
    """皮肤单次观察：返回 visible / unclear / attention 三段文字。"""

    from app.services.herlog_ai import observe_skin

    path = image or next(iter(sorted((ROOT / "pic").glob("*.jpg"))), None)
    if path is None:
        raise SystemExit("找不到图片，用 --image 指定一张照片")
    data = await observe_skin(path.read_bytes(), "面部", mime="image/jpeg")
    show(f"skin/{path.name}", json.dumps(data, ensure_ascii=False, indent=2), None)


def show(title: str, text: str, usage: dict | None) -> None:
    print(f"\n=== {title} ===")
    print(text)
    if usage:
        print(f"[usage] {json.dumps(usage, ensure_ascii=False)}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="DeepSeek 调用示例")
    parser.add_argument(
        "cases",
        nargs="*",
        default=[],
        help="chat | json | stream | qa | skin，留空表示全部执行",
    )
    parser.add_argument("--image", type=pathlib.Path, default=None)
    args = parser.parse_args()

    load_key()
    handlers = {
        "chat": case_chat,
        "json": case_json,
        "stream": case_stream,
        "qa": case_qa,
        "skin": lambda: case_skin(args.image),
    }
    unknown = [name for name in args.cases if name not in handlers]
    if unknown:
        parser.error(f"未知用例：{'、'.join(unknown)}；可选 {' / '.join(handlers)}")
    for name in args.cases or list(handlers):
        await handlers[name]()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
