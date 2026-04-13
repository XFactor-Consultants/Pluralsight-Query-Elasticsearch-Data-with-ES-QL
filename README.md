s
# Course Dataset — Query Elasticsearch Data with ES|QL

This repository contains the synthetic web traffic dataset used throughout the course.
Every query demonstrated across all four modules runs against these indices.

---

## Files

| File | Description |
|---|---|
| `generate_dataset.py` | Python script that regenerates all three NDJSON files |
| `logs-web.ndjson` | 500 web traffic log events — main query index |
| `service_metadata.ndjson` | 8 service ownership records — lookup index (Module 4) |
| `user_subscription.ndjson` | 60 user subscription tiers — enrich policy source (Module 4) |

---

## Prerequisites

-Create an account on https://www.elastic.co/kibana 
-Familiarize yourself with basics of the site: we'll be spending most time in 'Elastisearc -> discover', but we'll also use DevTools(the gear icon) to set up our data. 

---

## Step 1 — Create the `logs-web` index

The `status_code` field is intentionally mapped as `keyword` (not integer).
This is deliberate — Module 2 demonstrates how to identify and fix type mismatches.

```bash
curl -X PUT "$ES_URL/logs-web" \
  -u "$ES_USER:$ES_PASS" \
  -H "Content-Type: application/json" \
  -d '{
    "mappings": {
      "properties": {
        "@timestamp":       { "type": "date" },
        "user_id":          { "type": "keyword" },
        "service_name":     { "type": "keyword" },
        "http_method":      { "type": "keyword" },
        "endpoint":         { "type": "keyword" },
        "status_code":      { "type": "keyword" },
        "bytes_sent":       { "type": "long" },
        "response_time_ms": { "type": "long" },
        "region":           { "type": "keyword" },
        "user_agent":       { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
        "request_id":       { "type": "keyword" }
      }
    }
  }'
```

---

## Step 2 — Create the `service_metadata` lookup index

The `index.mode: lookup` setting is required for LOOKUP JOIN in Module 4.

```bash
curl -X PUT "$ES_URL/service_metadata" \
  -u "$ES_USER:$ES_PASS" \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "index.mode": "lookup"
    },
    "mappings": {
      "properties": {
        "service_name": { "type": "keyword" },
        "team_owner":   { "type": "keyword" },
        "environment":  { "type": "keyword" }
      }
    }
  }'
```

---

## Step 3 — Create the `user_subscription` index

This is the source index for the enrich policy used in Module 4.

```bash
curl -X PUT "$ES_URL/user_subscription" \
  -u "$ES_USER:$ES_PASS" \
  -H "Content-Type: application/json" \
  -d '{
    "mappings": {
      "properties": {
        "user_id":           { "type": "keyword" },
        "subscription_tier": { "type": "keyword" }
      }
    }
  }'
```

---

## Step 4 — Bulk index all three files

```bash
curl -X POST "$ES_URL/_bulk" \
  -u "$ES_USER:$ES_PASS" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @logs-web.ndjson

curl -X POST "$ES_URL/_bulk" \
  -u "$ES_USER:$ES_PASS" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @service_metadata.ndjson

curl -X POST "$ES_URL/_bulk" \
  -u "$ES_USER:$ES_PASS" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @user_subscription.ndjson
```

Verify the document counts:

```bash
curl -s "$ES_URL/logs-web/_count" -u "$ES_USER:$ES_PASS" | python3 -m json.tool
curl -s "$ES_URL/service_metadata/_count" -u "$ES_USER:$ES_PASS" | python3 -m json.tool
curl -s "$ES_URL/user_subscription/_count" -u "$ES_USER:$ES_PASS" | python3 -m json.tool
```

Expected counts: `logs-web` → 500, `service_metadata` → 8, `user_subscription` → 60.

---

## Step 5 — Create and execute the enrich policy

This policy is used in Module 4 Clip 2 (ENRICH command).

**Create the policy:**

```bash
curl -X PUT "$ES_URL/_enrich/policy/user_subscription" \
  -u "$ES_USER:$ES_PASS" \
  -H "Content-Type: application/json" \
  -d '{
    "match": {
      "indices": "user_subscription",
      "match_field": "user_id",
      "enrich_fields": ["subscription_tier"]
    }
  }'
```

**Execute the policy** (pre-processes the data — required before ENRICH queries work):

```bash
curl -X POST "$ES_URL/_enrich/policy/user_subscription/_execute" \
  -u "$ES_USER:$ES_PASS"
```

Re-execute the policy any time the `user_subscription` index is updated.

---

## Step 6 — Create a Kibana data view

In Kibana, navigate to **Stack Management > Data Views > Create data view**.

| Field | Value |
|---|---|
| Name | `logs-web` |
| Index pattern | `logs-web*` |
| Timestamp field | `@timestamp` |

This data view is used in the Discover ES|QL editor throughout the course.

---

## Dataset Design Notes

### `logs-web` — intentional design choices

| Field | Type | Why |
|---|---|---|
| `status_code` | `keyword` | Demonstrates type mismatch in Module 2 Clip 3 — must be cast with `TO_INTEGER()` for numeric comparisons |
| `user_id` | `keyword` (nullable) | ~5% of rows have `null` user_id — used in Module 2 Clip 2 to demonstrate `IS NULL` / `IS NOT NULL` |
| `bytes_sent` | `long` | Includes outlier values (up to 2 MB) and zeros — used in Module 2 Clip 1 for SORT validation |
| `service_name` | `keyword` | Includes `legacy-gateway` which has no entry in `service_metadata` — produces a `null` team_owner after LOOKUP JOIN |

### `service_metadata` — lookup index

Contains 8 registered services. `legacy-gateway` is intentionally absent so learners can
observe and filter unmatched rows after a LOOKUP JOIN in Module 4 Clip 1.

### `user_subscription` — enrich source

60 users mapped to `free`, `pro`, or `enterprise` tiers. Used with the
`user_subscription` enrich policy in Module 4 Clip 2.

---

## Module-to-Dataset Cross-Reference

| Module | Clip | Dataset feature exercised |
|---|---|---|
| 1 | 1 | `FROM logs-web*` — basic query and Kibana editor orientation |
| 1 | 2 | `KEEP`, `RENAME` on `@timestamp`, `user_id`, `status_code`, `bytes_sent` |
| 1 | 3 | `WHERE @timestamp >= NOW() - 1d AND status_code >= 500` (note: returns no results until type fix) |
| 2 | 1 | `SORT bytes_sent DESC` — outlier rows surface; `SORT ASC` shows zero-byte rows |
| 2 | 2 | `WHERE user_id IS NULL` — 22 null rows present; `COUNT(*)` vs `COUNT(user_id)` gap |
| 2 | 3 | `status_code` mapped as keyword — numeric filter returns wrong results; fixed with `TO_INTEGER()` |
| 3 | 1 | `EVAL response_kb = bytes_sent / 1024` — unit conversion; boolean flag `is_large` |
| 3 | 2 | `EVAL status_category = CASE(...)` — status code ranges → readable labels |
| 3 | 3 | `STATS error_count = COUNT(*) BY service_name` — ranked service error summary |
| 4 | 1 | `LOOKUP JOIN service_metadata ON service_name` — `legacy-gateway` produces null `team_owner` |
| 4 | 2 | `ENRICH user_subscription ON user_id` — errors grouped by `subscription_tier` |
| 4 | 3 | Saved search, dashboard panel, alerting rule — no dataset change required |

---

## Regenerating the Dataset

To regenerate all three NDJSON files (e.g. to refresh timestamps):

```bash
python3 generate_dataset.py
```

Then re-run the bulk index commands in Step 4 after deleting the existing indices:

```bash
curl -X DELETE "$ES_URL/logs-web,service_metadata,user_subscription" \
  -u "$ES_USER:$ES_PASS"
```

The generator uses a fixed random seed (`seed=42`) so output is deterministic unless
you change the seed or the reference data.
