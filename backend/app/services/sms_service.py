"""Issue short-lived SMS proofs for HerLog login, registration and binding."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import secrets
import time
from functools import lru_cache
from threading import Lock
from uuid import uuid4

from fastapi import Request
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.errors import ApiError
from app.schemas.auth import SmsChallengeOut, SmsProofIn

CODE_TTL = 300
COOLDOWN = 60
MAX_ATTEMPTS = 5
SEND_LIMITS = ((1, COOLDOWN), (5, 86400), (20, 3600), (200, 3600))
PREFIX = "herlog:auth:sms:"
TEST_PREFIX = "1990000"
logger = logging.getLogger(__name__)


class DemoStore:
    """Local-only delivery and expiry simulation shared by requests in one process."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.buckets = {}
        self.challenges = {}
        self.lock = Lock()

    def issue(self, key, buckets, challenge, digest) -> int:
        with self.lock:
            now = self.clock()
            self.buckets = {k: item for k, item in self.buckets.items() if item[1] > now}
            self.challenges = {k: item for k, item in self.challenges.items() if item[3] > now}
            for bucket, (limit, _) in zip(buckets, SEND_LIMITS, strict=True):
                if bucket in self.buckets and self.buckets[bucket][0] >= limit:
                    return max(1, math.ceil(self.buckets[bucket][1] - now))
            for bucket, (_, seconds) in zip(buckets, SEND_LIMITS, strict=True):
                count, until = self.buckets.get(bucket, (0, now + seconds))
                self.buckets[bucket] = (count + 1, until)
            self.challenges[key] = (challenge, digest, 0, now + CODE_TTL)
            return 0

    def consume(self, key, challenge, digest) -> bool:
        with self.lock:
            row = self.challenges.get(key)
            if row is None or row[0] != challenge:
                return False
            if row[3] <= self.clock():
                self.challenges.pop(key)
                return False
            matched = hmac.compare_digest(row[1], digest)
            if matched or row[2] + 1 >= MAX_ATTEMPTS:
                self.challenges.pop(key)
            else:
                self.challenges[key] = (row[0], row[1], row[2] + 1, row[3])
            return matched


# KEYS: challenge and four server-derived rate buckets. A resend replaces the
# proof for the same phone/purpose/account. Counters are shared across workers.
ISSUE = """
for i = 2, #KEYS do
    if tonumber(redis.call('GET', KEYS[i]) or '0') >= tonumber(ARGV[2*i]) then
        return math.max(1, redis.call('TTL', KEYS[i]))
    end
end
for i = 2, #KEYS do
    if redis.call('INCR', KEYS[i]) == 1 then
        redis.call('EXPIRE', KEYS[i], tonumber(ARGV[2*i+1]))
    end
end
redis.call('HSET', KEYS[1], 'id', ARGV[1], 'digest', ARGV[2], 'attempts', 0)
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]))
return 0
"""
CONSUME = """
if redis.call('HGET', KEYS[1], 'id') ~= ARGV[1] then return 0 end
if redis.call('HGET', KEYS[1], 'digest') == ARGV[2] then
    redis.call('DEL', KEYS[1])
    return 1
end
if redis.call('HINCRBY', KEYS[1], 'attempts', 1) >= tonumber(ARGV[3]) then
    redis.call('DEL', KEYS[1])
end
return 0
"""
CANCEL = """
if redis.call('HGET', KEYS[1], 'id') == ARGV[1] then
    redis.call('DEL', KEYS[1])
end
"""


@lru_cache
def redis_store() -> Redis:
    return Redis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD or None, socket_connect_timeout=2, socket_timeout=2,
    )


_demo_store = DemoStore()
_demo_secret = secrets.token_bytes(32)


def _demo_allowed(request: Request) -> bool:
    return (
        settings.ENV == "local" and settings.database_url.startswith(("sqlite:", "sqlite+pysqlite:"))
        and request.client is not None and request.client.host in {"127.0.0.1", "::1"}
    )


def mode_for(request: Request) -> str:
    if settings.HERLOG_SMS_MODE == "demo" and _demo_allowed(request):
        return "demo"
    if settings.HERLOG_SMS_MODE == "aliyun" and settings.REDIS_ENABLED and all((
        len(settings.HERLOG_SMS_HMAC_SECRET.encode()) >= 32, settings.HERLOG_SMS_SIGN_NAME.strip(),
        settings.HERLOG_SMS_TEMPLATE_CODE.strip(), settings.ALIBABA_CLOUD_ACCESS_KEY_ID.strip(),
        settings.ALIBABA_CLOUD_ACCESS_KEY_SECRET.strip(),
    )):
        return "live"
    return "disabled"


def _mode(request: Request, phone: str) -> str:
    mode = mode_for(request)
    if mode == "disabled":
        raise ApiError(503, "短信验证暂不可用，请稍后重试或使用账号密码登录")
    if mode == "demo" and not phone.startswith(TEST_PREFIX):
        raise ApiError(422, "本地短信演示仅支持 1990000 开头的测试号码")
    return mode


def _mac(mode: str, *parts: str) -> str:
    key = _demo_secret if mode == "demo" else settings.HERLOG_SMS_HMAC_SECRET.encode()
    return hmac.new(key, "\0".join(parts).encode(), hashlib.sha256).hexdigest()


def _challenge_key(mode: str, phone: str, purpose: str, subject: str) -> str:
    return PREFIX + "proof:" + _mac(mode, "proof", phone, purpose, subject)


def _buckets(mode: str, phone: str, request: Request) -> list[str]:
    phone_key = _mac(mode, "phone", phone)
    ip = request.client.host if request.client else "unknown"
    return [PREFIX + key for key in (
        "cooldown:" + phone_key, "daily:" + phone_key, "ip:" + _mac(mode, "ip", ip), "total",
    )]


def _deliver(phone: str, code: str) -> None:
    from alibabacloud_dysmsapi20170525.client import Client
    from alibabacloud_dysmsapi20170525.models import SendSmsRequest
    from alibabacloud_tea_openapi.models import Config
    from alibabacloud_tea_util.models import RuntimeOptions

    client = Client(Config(
        access_key_id=settings.ALIBABA_CLOUD_ACCESS_KEY_ID,
        access_key_secret=settings.ALIBABA_CLOUD_ACCESS_KEY_SECRET,
        endpoint="dysmsapi.aliyuncs.com",
    ))
    sent = client.send_sms_with_options(SendSmsRequest(
        phone_numbers=phone, sign_name=settings.HERLOG_SMS_SIGN_NAME, template_code=settings.HERLOG_SMS_TEMPLATE_CODE,
        template_param=json.dumps({"code": code}),
    ), RuntimeOptions(connect_timeout=3000, read_timeout=5000, autoretry=False))
    if not sent.body or sent.body.code != "OK":
        raise RuntimeError("SMS provider declined delivery")


def issue(request: Request, phone: str, purpose: str, subject: str = "") -> SmsChallengeOut:
    mode = _mode(request, phone)
    challenge = uuid4().hex
    code = f"{secrets.randbelow(1_000_000):06d}"
    key = _challenge_key(mode, phone, purpose, subject)
    digest = _mac(mode, "code", challenge, code)
    buckets = _buckets(mode, phone, request)
    if mode == "demo":
        wait = _demo_store.issue(key, buckets, challenge, digest)
    else:
        store = redis_store()
        args = [value for limit in SEND_LIMITS for value in limit]
        try:
            wait = store.eval(ISSUE, 1 + len(buckets), key, *buckets, challenge, digest, CODE_TTL, *args)
        except RedisError as exc:
            raise ApiError(503, "短信验证暂不可用，请稍后重试") from exc
    if wait:
        raise ApiError(429, "发送过于频繁，请稍后重试", {"retry_after": wait})
    if mode == "live":
        try:
            _deliver(phone, code)
        except Exception as exc:
            logger.warning("SMS delivery failed: %s", type(exc).__name__)
            try:
                store.eval(CANCEL, 1, key, challenge)
            except RedisError:
                pass
            raise ApiError(503, "验证码发送失败，请稍后重试", {"retry_after": COOLDOWN}) from None
    return SmsChallengeOut(
        challenge_id=challenge, expires_in=CODE_TTL, resend_in=COOLDOWN,
        demo_code=code if mode == "demo" else None,
    )


def verify(request: Request, payload: SmsProofIn, purpose: str, subject: str = "") -> None:
    mode = _mode(request, payload.phone)
    key = _challenge_key(mode, payload.phone, purpose, subject)
    digest = _mac(mode, "code", payload.challenge_id, payload.code)
    if mode == "demo":
        matched = _demo_store.consume(key, payload.challenge_id, digest)
    else:
        try:
            matched = redis_store().eval(CONSUME, 1, key, payload.challenge_id, digest, MAX_ATTEMPTS)
        except RedisError as exc:
            raise ApiError(503, "短信验证暂不可用，请稍后重试") from exc
    if not matched:
        raise ApiError(422, "验证码无效或已过期，请检查后重试", {"reason": "sms_invalid"})
