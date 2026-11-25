"""
Rate limiting (tiêu chí 7).

Yêu cầu:
  • Mỗi API key tối đa RATE_LIMIT_PER_MINUTE request trong 60 giây (sliding window)
  • Vượt giới hạn → HTTP 429, nên kèm header Retry-After
  • State lưu trong Redis để mọi worker / instance dùng chung và vẫn còn sau khi
    restart agent (script chấm sẽ restart agent để kiểm tra)
"""


def check_rate_limit(key: str) -> None:
    now = time.time()
    redis_key = "rate:" + hashlib.sha256(key.encode()).hexdigest()
    try:
        allowed, retry = r.eval(_SCRIPT, 1, redis_key, now, settings.rate_limit_per_minute,
                                f"{now:.6f}:{time.time_ns()}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Rate limiter unavailable") from exc
    if not int(allowed):
        raise HTTPException(status_code=429, detail="Rate limit exceeded",
                            headers={"Retry-After": str(int(retry))})
import hashlib
import time
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

_SCRIPT = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', tonumber(ARGV[1])-60)
local count = redis.call('ZCARD', KEYS[1])
if count >= tonumber(ARGV[2]) then
 local first = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
 return {0, math.max(1, math.ceil(60-(tonumber(ARGV[1])-tonumber(first[2]))))}
end
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[3])
redis.call('EXPIRE', KEYS[1], 61)
return {1, 0}
"""
