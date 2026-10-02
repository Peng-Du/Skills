# Inspection Data Format (input to `gen_report.py`)

The LLM reads the API results (direct MCP tool results, or `step*.json` files when
using the mcporter transport), extracts the fields below, writes the **analysis
text**, and saves everything as one UTF-8 JSON file **per site**:

```
<out>/Inspection_Data_<site>_<yyyyMMdd_HHmm>.json
```

**Missing data:** if an API call failed, set that top-level section (`ac[i]`
metrics, `problem_distribution`, `access_success`, `reasoning`, `ap`) to `null`.
The report then shows "Not collected" / "No data" for it. Put the error message
in `analysis.notes`. Never fill a failed section with guessed or zero values:
an empty list / zero count means "collected, nothing found".

`gen_report.py` only formats. It computes ratings, the TOP 5 problem list and the
access-rate statistics from the numbers you supply, so do not pre-format numbers
as strings (`65`, not `"65%"`). Every narrative sentence in the report comes from
the `analysis` block, which must be based on the collected data only.

## Complete example

```json
{
  "meta": {
    "site_name": "Spain Office",
    "shop_id": 1224164,
    "region": "My Network",
    "inspection_time": "2026-09-30 16:50",
    "time_window": {
      "start": "2026-09-30 00:00:00.000",
      "end": "2026-09-30 16:50:00.000",
      "timezone": "Europe/Madrid"
    },
    "tool": "Cloudnet MCP (cloudnet-wlan-inspection-lite)",
    "language": "en"
  },
  "ac": [
    {
      "name": "MSR1104S-W",
      "model": "MSR1104S-W",
      "sn": "219801A3NG924CQ00085",
      "type": "router",
      "online": true,
      "soft_ver": "Release 6749P30",
      "address": "88.2.229.149",
      "cpu": 10,
      "memory": 65,
      "disk": 48,
      "speed_up_kbps": 52,
      "speed_down_kbps": 53,
      "role": "Router acting as AC / gateway",
      "note": "No dedicated AC; the router is inspected in the AC role. Cloud AP WA6636 reports its own SN as acSN (cloud-managed standalone)."
    }
  ],
  "problem_distribution": [
    {
      "type": "apLoad",
      "name": "Wireless Condition",
      "times": 3,
      "sub_types": [
        { "name": "Severe Interference", "times": 2 },
        { "name": "High Channel Usage", "times": 1 }
      ]
    }
  ],
  "access_success": {
    "samples": [
      { "time": "2026-09-30 00:30", "rate": 100 },
      { "time": "2026-09-30 00:35", "rate": 97.5 }
    ]
  },
  "reasoning": {
    "items": [
      {
        "alarm_level": 3,
        "type": "Co-channel interference",
        "category": "WIRELESS",
        "count": 4,
        "status": "ACTIVE",
        "description": "…",
        "suggestion": "…"
      }
    ]
  },
  "ap": {
    "online": 1,
    "offline": 0,
    "total": 1,
    "offline_aps": [],
    "list_complete": true
  },
  "analysis": {
    "executive_summary": "One or two sentences on overall health, based on the data.",
    "priorities": [
      { "priority": "P0", "item": "…", "basis": "…", "action": "…" }
    ],
    "remediation": {
      "short_term": ["…"],
      "medium_term": ["…"],
      "long_term": ["…"]
    },
    "conclusion": {
      "overall": "…",
      "key_risks": ["…"],
      "trends": ["…"]
    },
    "notes": ["Data caveats, e.g. small sample size, timezone used, missing data."]
  }
}
```

## Field reference

### `meta` (required)

| Field | Type | Required | Source |
|---|---|---|---|
| `site_name` | string | ✅ | step1 `shopList[].shopName` |
| `shop_id` | number/string | ✅ | step1 `shopList[].shopId` |
| `region` | string | | step1 `shopList[].regionName` |
| `inspection_time` | string | ✅ | Time the inspection ran (local time of `timezone`) |
| `time_window.start/end/timezone` | string | ✅ | The window passed to step 3 |
| `tool` | string | | Free text; defaults to "Cloudnet MCP" |
| `language` | `en` \| `zh` | | Report language (overridden by `gen_report.py --lang`). Write all `analysis` prose in this language. |

### `ac` (array; may be empty)

One entry per AC inspected in step 2. Source: step1 `deviceList[]` + step2 `data`.

| Field | Type | Source |
|---|---|---|
| `name` / `model` / `sn` / `type` / `soft_ver` | string | step1 `devAlias` / `devModel` / `devSn` / `customType` / `softVer` |
| `online` | bool | step1 `status == 1` |
| `address` | string | step2 `devAddress` |
| `cpu` / `memory` / `disk` | number (%) | step2 `cpuRatio` / `memoryRatio` / `diskRatio` |
| `speed_up_kbps` / `speed_down_kbps` | number | step2 `speed_up` / `speed_down` |
| `role` | string | Optional, e.g. "AC", "Router acting as AC / gateway" |
| `note` | string | Optional remark, e.g. which APs this device manages |

`devModel` can contain an invisible zero-width character (U+200B); strip it.
If the site has **no** AC, use `[]` and explain why in `analysis.notes`.
If `getDeviceRunInfo` failed for a device (e.g. it is offline), keep the entry
with `cpu`/`memory`/`disk` set to `null`.

### `problem_distribution` (array)

Source: 3A `response.data[]`. **The API may return every category twice, and the
copies can have different counts.** Pass every entry as returned (or drop only
exact duplicates); the script keeps the highest count per `type` and adds a
note naming the categories whose copies differed. Use the `en` names (or `cn`
for a Chinese report). Categories with `times == 0` can be included or left
out; the script ranks the TOP 5 with `times > 0` by itself.

### `access_success.samples` (array)

Source: step3b `response.data[]`, mapping `RT → time` and `IUS → rate`. The
script computes the lowest rate, when it occurred, and how many samples are
below 98%. An empty array means there were no access attempts in the window;
the rating is then shown as "No data".

### `reasoning.items` (array)

Source: step4 `response.data.data[]`. `alarm_level` 3 = high risk, 2 = medium
risk, anything lower = low risk. `type` ← `reasoningType`, `category` ←
`reasoningCategory`. Write `description` and `suggestion` in the report language. The
script counts high/medium items from this list.

### `ap` (`null` if not collected)

| Field | Source |
|---|---|
| `online` / `offline` / `total` | step5a `data` |
| `offline_aps` | step5b `detail[]` where `Ss == 2` → `apName` |
| `list_complete` | `false` when the merged 5B results (all `dim` queries, deduplicated by `apSN`) still have fewer entries than `totalCount` |

`total` may include routers with built-in WLAN; mention it in `analysis.notes`.

### `analysis` (required; written by the LLM)

All report prose comes from here. Keep it factual and tied to the data above.

| Field | Content |
|---|---|
| `executive_summary` | Overall status in 1–3 sentences |
| `priorities[]` | P0 = 🔴 critical / high-risk, P1 = ⚠️ attention / medium-risk, P2 = low-risk or watch items. Leave empty if nothing applies. |
| `remediation.short_term/medium_term/long_term` | Lists of concrete actions tied to actual findings |
| `conclusion.overall` / `key_risks[]` / `trends[]` | Chapter 6 content |
| `notes[]` | Data caveats shown at the end of the report |

## Rating thresholds (applied by the script)

| Check item | 🟢 Normal | ⚠️ Needs attention | 🔴 Critical |
|---|---|---|---|
| CPU | ≤50% | ≤70% | >70% |
| Memory | ≤70% | ≤85% | >85% |
| Disk | ≤70% | ≤85% | >85% |
| Access success rate (lowest sample) | ≥98% | ≥95% | <95% |
| AP online rate | ≥98% | ≥95% | <95% |

A site with `ap.total == 0` gets "No data" for the AP online rate.

## Multi-site runs

Write one data file per site and pass them all to one `gen_report.py` call
(`--data-file` repeated). The script writes one report per site plus
`Inspection_Summary_<timestamp>.md` with one row per site.
