"""
Cost guard (tiêu chí 8).

Yêu cầu:
  • Cộng dồn chi phí LLM (tính theo token) vào Redis
  • Tổng chi phí vượt DAILY_BUDGET_USD (hoặc MONTHLY_BUDGET_USD) → HTTP 402
"""

# Giá USD / 1K tokens (tham khảo gpt-4o-mini)
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def check_budget() -> None:
    """Gọi TRƯỚC khi gọi LLM. Hết budget → raise HTTPException(status_code=402)."""
    try:
        total = float(r.get(_key()) or 0)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Cost guard unavailable") from exc
    if total >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    """Gọi SAU khi gọi LLM. Cộng chi phí của request vào tổng, trả về chi phí request."""
    cost = max(0, input_tokens) / 1000 * PRICE_INPUT_PER_1K + max(0, output_tokens) / 1000 * PRICE_OUTPUT_PER_1K
    try:
        pipe = r.pipeline()
        pipe.incrbyfloat(_key(), cost)
        pipe.expire(_key(), 172800)
        pipe.execute()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Cost guard unavailable") from exc
    return cost


def _key() -> str:
    return "cost:daily:" + datetime.now(timezone.utc).strftime("%Y-%m-%d")
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r
