"""Exercise 4.4: atomic per-user $10/month reservation in Redis.

Separate from the original daily in-memory demo. Inject a Redis client to use
this in a service. Reservation avoids concurrent check-then-increment races.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib
import math

RESERVE = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
local amount = tonumber(ARGV[1])
if current + amount > tonumber(ARGV[2]) then return 0 end
redis.call('INCRBY', KEYS[1], amount)
redis.call('EXPIRE', KEYS[1], 5356800)
return 1
"""

def check_budget(user_id: str, estimated_cost: float, client) -> bool:
    """Reserve estimated USD, return False if the monthly budget would exceed $10."""
    if not math.isfinite(estimated_cost) or estimated_cost < 0:
        raise ValueError("estimated_cost must be finite and nonnegative")
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    user = hashlib.sha256(user_id.encode()).hexdigest()
    # Integer nano-USD; round upward to avoid undercharging estimates.
    amount = int((Decimal(str(estimated_cost)) * 10**9).to_integral_value(rounding=ROUND_CEILING))
    return bool(client.eval(RESERVE, 1, f"lab4:budget:{user}:{month}", amount, 10 * 10**9))
