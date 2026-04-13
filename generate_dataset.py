"""
generate_dataset.py
-------------------
Generates ~500 rows of synthetic web traffic log data for the
"Query Elasticsearch Data with ES|QL" course.

Outputs:
  logs-web.ndjson           — Elasticsearch bulk-ready NDJSON
  service_metadata.ndjson   — Lookup index (service ownership)
  user_subscription.ndjson  — Enrich policy source index (user tiers)

Usage:
  python generate_dataset.py
"""

import random
import json
import datetime
import uuid

random.seed(42)

# ── Reference data ────────────────────────────────────────────────────────────

SERVICES = [
    {"service_name": "auth-service",       "team_owner": "Platform",   "environment": "production"},
    {"service_name": "payment-service",    "team_owner": "Payments",   "environment": "production"},
    {"service_name": "search-service",     "team_owner": "Discovery",  "environment": "production"},
    {"service_name": "recommendation-api", "team_owner": "Discovery",  "environment": "production"},
    {"service_name": "user-profile-api",   "team_owner": "Identity",   "environment": "production"},
    {"service_name": "checkout-service",   "team_owner": "Payments",   "environment": "production"},
    {"service_name": "inventory-api",      "team_owner": "Logistics",  "environment": "staging"},
    {"service_name": "notification-svc",   "team_owner": "Platform",   "environment": "staging"},
]

# Intentionally leave one service unregistered in metadata (for the IS NULL demo)
UNREGISTERED_SERVICE = "legacy-gateway"

SUBSCRIPTION_TIERS = ["free", "pro", "enterprise"]

ENDPOINTS = [
    "/api/v1/login",
    "/api/v1/logout",
    "/api/v1/search",
    "/api/v1/products",
    "/api/v1/checkout",
    "/api/v1/recommendations",
    "/api/v1/user/profile",
    "/api/v1/inventory",
    "/api/v1/notifications",
    "/api/v1/orders",
]

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE"]

# Status code distribution — weighted to produce realistic mix
STATUS_CODES = (
    [200] * 55 +
    [201] * 10 +
    [204] * 5  +
    [301] * 5  +
    [304] * 5  +
    [400] * 5  +
    [401] * 5  +
    [403] * 3  +
    [404] * 5  +
    [429] * 2  +
    [500] * 8  +
    [502] * 4  +
    [503] * 4  +
    [504] * 2  +
    [0]   * 1    # edge case for type demo
)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36",
    "python-requests/2.28.0",
    "curl/7.88.1",
]

REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]

# ── Generate users ─────────────────────────────────────────────────────────────

NUM_USERS = 60
users = []
for i in range(NUM_USERS):
    users.append({
        "user_id": f"user_{1000 + i}",
        "subscription_tier": random.choice(SUBSCRIPTION_TIERS),
    })

# 5% of events will have null user_id (unauthenticated requests)
NULL_USER_PROBABILITY = 0.05

# ── Generate log events ────────────────────────────────────────────────────────

NOW = datetime.datetime.utcnow()
START = NOW - datetime.timedelta(days=7)

def random_timestamp():
    delta = NOW - START
    random_seconds = random.uniform(0, delta.total_seconds())
    return START + datetime.timedelta(seconds=random_seconds)

def random_bytes(status_code):
    if status_code in (204, 304):
        return 0
    if status_code >= 500:
        return random.randint(200, 2000)
    if status_code >= 400:
        return random.randint(100, 800)
    # Occasionally generate a large response to demo outlier detection
    if random.random() < 0.02:
        return random.randint(500_000, 2_000_000)
    return random.randint(1_000, 80_000)

def random_response_time(status_code):
    if status_code >= 500:
        return random.randint(2000, 10000)
    if status_code >= 400:
        return random.randint(50, 500)
    return random.randint(20, 800)

logs = []
for _ in range(500):
    user = random.choice(users) if random.random() > NULL_USER_PROBABILITY else None
    service = random.choice(SERVICES + [{"service_name": UNREGISTERED_SERVICE, "team_owner": None, "environment": "production"}])
    status_code = random.choice(STATUS_CODES)
    ts = random_timestamp()

    log = {
        "@timestamp":      ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "user_id":         user["user_id"] if user else None,
        "service_name":    service["service_name"],
        "http_method":     random.choice(HTTP_METHODS),
        "endpoint":        random.choice(ENDPOINTS),
        # status_code stored as keyword to demonstrate type mismatch in Module 2
        "status_code":     str(status_code),
        "bytes_sent":      random_bytes(status_code),
        "response_time_ms": random_response_time(status_code),
        "region":          random.choice(REGIONS),
        "user_agent":      random.choice(USER_AGENTS),
        "request_id":      str(uuid.uuid4()),
    }
    logs.append(log)

# Sort by timestamp ascending
logs.sort(key=lambda x: x["@timestamp"])

# ── Write logs-web.ndjson ──────────────────────────────────────────────────────

with open("/home/claude/logs-web.ndjson", "w") as f:
    for doc in logs:
        f.write(json.dumps({"index": {"_index": "logs-web"}}) + "\n")
        f.write(json.dumps(doc) + "\n")

print(f"logs-web.ndjson written — {len(logs)} documents")

# ── Write service_metadata.ndjson ─────────────────────────────────────────────
# This is the lookup index used in Module 4 LOOKUP JOIN

with open("/home/claude/service_metadata.ndjson", "w") as f:
    for svc in SERVICES:
        f.write(json.dumps({"index": {"_index": "service_metadata"}}) + "\n")
        f.write(json.dumps(svc) + "\n")

print(f"service_metadata.ndjson written — {len(SERVICES)} documents")

# ── Write user_subscription.ndjson ────────────────────────────────────────────
# Source index for the user_subscription enrich policy used in Module 4 ENRICH

with open("/home/claude/user_subscription.ndjson", "w") as f:
    for user in users:
        f.write(json.dumps({"index": {"_index": "user_subscription"}}) + "\n")
        f.write(json.dumps(user) + "\n")

print(f"user_subscription.ndjson written — {len(users)} documents")

# ── Summary stats ─────────────────────────────────────────────────────────────

from collections import Counter
status_counts = Counter(int(l["status_code"]) if l["status_code"] != "0" else 0 for l in logs)
null_users = sum(1 for l in logs if l["user_id"] is None)

print("\n── Dataset summary ──────────────────────────────────")
print(f"Total log events : {len(logs)}")
print(f"Null user_id rows: {null_users}")
print(f"Status codes     : {dict(sorted(status_counts.items()))}")
print(f"Services         : {len(SERVICES) + 1} (incl. unregistered: {UNREGISTERED_SERVICE})")
print(f"Users            : {NUM_USERS}")
print(f"Time range       : {logs[0]['@timestamp']} → {logs[-1]['@timestamp']}")
