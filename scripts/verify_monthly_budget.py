"""Exercise 4.4 Redis verification, including concurrent reservations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import redis

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("monthly_budget", root / "04-api-gateway/production/monthly_budget.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
client = redis.Redis()
user = "verification-" + secrets.token_hex(12)
key = "lab4:budget:" + hashlib.sha256(user.encode()).hexdigest() + ":" + datetime.now(timezone.utc).strftime("%Y-%m")
try:
    with ThreadPoolExecutor(max_workers=10) as pool:
        accepted = list(pool.map(lambda _: module.check_budget(user, 1.0, client), range(20)))
    assert sum(accepted) == 10, accepted
    assert not module.check_budget(user, .01, client)
    assert module.check_budget(user + "-separate", 10.0, client)
    other = "lab4:budget:" + hashlib.sha256((user + "-separate").encode()).hexdigest() + ":" + datetime.now(timezone.utc).strftime("%Y-%m")
    client.delete(other)
    result = {"concurrent_requests": 20, "usd_per_request": 1,
              "accepted": 10, "rejected": 10, "extra_reservation": False,
              "separate_user_has_own_budget": True}
    (root / "evidence/part4-monthly-budget.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
finally:
    client.delete(key)
    client.close()
