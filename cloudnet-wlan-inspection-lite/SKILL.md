---
name: cloudnet-wlan-inspection-lite
description: |
  Cloudnet WLAN wireless network inspection skill (Lite edition). Inspects one, several or all Cloudnet sites through the Cloudnet MCP
  interfaces (direct MCP tools when connected, mcporter CLI as fallback) and runs a 6-step flow:
  get site information → AC health → problem distribution and access success rate → Cloudnet problem reasoning → AP online rate → generate the inspection report.
  Outputs one MD + DOCX report per site (English or Chinese), plus a multi-site summary when several sites are inspected.
  Titled "Wireless Network O&M Inspection Report (Lite Edition)" / "无线网络运维巡检报告（精简版）". Suitable for quick day-to-day health checks.
  Trigger words: inspection, lite inspection, WLAN inspection, wireless network inspection, cloudnet inspection, 巡检, 巡检报告, 无线巡检.
  Prerequisites: Cloudnet MCP tools in the session OR mcporter CLI + Cloudnet API key; python-docx for the DOCX report.
---

# Cloudnet WLAN Inspection Skill (Lite Edition)

> **Version: V0.1.0**
>
> 🎯 **Design principle: the LLM does data extraction and evaluation; scripts only compute ratings and format the reports (MD + DOCX).**
>
> 📂 **Paths:** `<skill-dir>` is this skill's base directory (where this SKILL.md lives). `scripts/` and `references/` are under `<skill-dir>`. `<out>` is the report directory: config `output_dir`, else `reports/` under the **project / working directory** (never inside `<skill-dir>`).

## Step 0: Pre-checks (must run first)

### 0.1 Read the configuration (optional file)

`<skill-dir>/config.json` is optional. Every field has a fallback (see the field reference at the end; `config.example.json` shows all fields).

⚠️ Never print the `api_key` value. Read the config with the key masked:

```bash
python -c "import json;c=json.load(open(r'<skill-dir>/config.json',encoding='utf-8'));c['api_key']='***' if c.get('api_key') else '';print(c)"
```

### 0.2 Choose the transport (in this order)

**A. Direct MCP tools (preferred).** If the session already has the Cloudnet MCP tools (any server whose tools include `getallshopsanddevofuser`, e.g. `mcp__<server>__getallshopsanddevofuser`; they may be deferred and need loading via ToolSearch first), call them directly. No mcporter, no API key, no step files. Tool results arrive in context; read `response.data` from them.

**B. mcporter (fallback).** Only when A is unavailable:
1. `mcporter --version` (≥ 0.9.0, else `npm install -g mcporter`).
2. `mcporter config list`; if `mcporter_name` (default `Cloudnet`) is missing and `api_key` is a real key (not a placeholder), add it:
   ```bash
   mcporter config add <mcporter_name> <base_url>/mcp-server/api/sse --transport sse --header "Authorization=Bearer <API_KEY>" --scope home
   ```
   `<base_url>` = config `base_url`, default `https://cloudnet1.h3c.com`. `--scope home` keeps the key out of the project folder. If the key is missing or a placeholder, ask the user to fill it in (Cloudnet → Network Management → Settings → Open Platform).
3. Every call goes through the wrapper, which saves clean JSON:
   ```bash
   python <skill-dir>/scripts/mcporter_call.py <mcporter_name> <tool> <out>/step<X>_<shopId>.json [key=value ...]
   ```
   Exit codes: `0` OK · `1` mcporter missing/failed · `2` API returned a non-zero `response.code` (file still saved; report the error). Use `key=value` arguments, never `--args '{json}'` (breaks under PowerShell), and pass no arguments to `getallshopsanddevofuser`.

### 0.3 python-docx

`python -c "import docx; print('OK')"`. If missing, suggest `pip install python-docx` and continue with `--no-docx` (MD only).

### 0.4 Output the check results

```
✅ Transport: direct MCP (<server>)   |   ✅ mcporter v0.x + connection <name>
✅ python-docx                         |   ⚠️ python-docx missing → MD only
✅ Language: en | zh   ✅ Output: <out>
```

Stop only if **no** transport works.

---

## Step 1: Sites and devices (serial; must complete first)

**Tool:** `getallshopsanddevofuser` (no parameters).

### 1.1 Resolve the sites to inspect

Priority: sites named in the user's request → config `shops[].name` → ask the user (list all sites from `shopList`).
- "all sites" / "全部场所" or config `"shops": "all"` → every site in `shopList`.
- Match names case-insensitively; a unique partial match (e.g. "Spain" → "Spain Office") is fine and must be stated in `analysis.notes`. Ambiguous or no match → list the candidates and ask.
- Never invent a site; the `shopId` always comes from this API.

### 1.2 Timezone per site

Priority: user request → `shops[].timezone` → config `timezone` → the site's location when obvious from its name/region (e.g. "Spain Office" → `Europe/Madrid`) → host timezone. Then compute the window **in that timezone**:

```bash
python <skill-dir>/scripts/time_window.py --tz <IANA tz>     # omit --tz to use the host timezone
```

It prints `start` (today 00:00), `end` (now — never end of day), `inspection_time` and `stamp`. Record which rule picked the timezone in `analysis.notes`.

### 1.3 Classify devices per site (from `deviceList`, filtered by `shopId`)

- Strip invisible U+200B from `devModel`.
- `customType` = `ac` → AC, inspect in Step 2.
- No `ac` device → a `router` / gateway with built-in WLAN (e.g. MSR1104S-W) is inspected in the AC role (`role`: "Router acting as AC / gateway").
- Cloud APs whose `acSN` equals their own `apSN` in Step 5B are **cloud-managed standalone** APs, not managed by the router; say so in the AC `note`.
- Several ACs → inspect each one (one `ac[]` entry each).
- No AC and no router → skip Step 2, `ac: []`, explain in notes.
- Offline devices: still list them; `getDeviceRunInfo` may fail → record the error, leave cpu/memory/disk `null`.

## Steps 2-5: Collect data in parallel (per site)

Steps 2/3/4/5 are independent: **issue all calls at once** (and for all sites at once when inspecting several).

| Step | Tool | Parameters | Extract |
|---|---|---|---|
| 2 AC health (each AC) | `getDeviceRunInfo` | `devSN` | `cpuRatio`, `memoryRatio`, `diskRatio`, `speed_up`, `speed_down`, `devAddress` |
| 3A Problem distribution | `getProblemDistribute` | `shopId`, `startTime`, `endTime`, `timezone` | all `data[]` categories (see below) |
| 3B Access success | `getHistoryAccessSucOneDay` | same as 3A | `data[]` → `RT`/`IUS` samples |
| 4 Problem reasoning | `getShopNetworkProblem` | `shopId` | `data.data[]` items |
| 5A AP count | `getCurrentApCount` | `shopId` | `online`, `offline`, `total` |
| 5B AP list | `getApRegularMatch` | `shopId`, `dim` | `detail[]`: `Ss==2` → offline AP names; `acSN` for device roles |

Pass `shopId` as a string. Times use `yyyy-MM-dd HH:mm:ss.SSS` from `time_window.py`.

**Rules that keep the result correct on any site:**
- **3A duplicates:** the API may return every category twice, sometimes with **different** counts. Pass all entries; `gen_report.py` keeps the highest count per type and adds a note listing the types that differed.
- **3B empty `data[]`** = no access attempts in the window → "No data", not a failure.
- **5A total** may include routers with built-in WLAN; mention it in notes when that happens.
- **5B completeness:** start with `dim=1` (H3C serial numbers contain "1"). If `totalCount > len(detail)`, query again with `dim` = `0`,`2`…`9` and merge by `apSN` until the union reaches `totalCount`; if it still falls short, set `ap.list_complete=false`.
- **Failed call** (error, non-zero `code`, timeout): retry once; if it still fails, set that section to `null` in the data file (the report shows "Not collected") and record the error message in `analysis.notes`. Never abort the whole inspection for one failed call, and never fill in guessed values.

**Rating thresholds** (applied by the script):

| Check item | 🟢 Normal | ⚠️ Needs attention | 🔴 Critical |
|---|---|---|---|
| CPU | ≤50% | ≤70% | >70% |
| Memory | ≤70% | ≤85% | >85% |
| Disk | ≤70% | ≤85% | >85% |
| Access success rate (lowest sample) | ≥98% | ≥95% | <95% |
| AP online rate | ≥98% | ≥95% | <95% |

## Step 6: Assemble data and generate the reports

### 6.1 Write one data file per site

Read `<skill-dir>/references/data-format.md` **before** writing. Save `<out>/Inspection_Data_<site>_<stamp>.json` (UTF-8). It holds the raw numbers plus the `analysis` block (all report prose), written in the report language:

- Language: user request → config `language` → the language the user is writing in (`zh` for Chinese, else `en`). Set `meta.language`. Keep technical terms in English (CPU, RSSI, AP, AC, SSID, Portal, DHCP, DNS…).
- Prose must be based on the collected data only. If the session already contains related findings (e.g. a client diagnosis of this site), they may be cited, labelled as such in `notes`.

### 6.2 Generate

```bash
python <skill-dir>/scripts/gen_report.py --data-file <out>/Inspection_Data_<siteA>_<stamp>.json [--data-file <out>/Inspection_Data_<siteB>_<stamp>.json ...] --output-dir <out> [--lang zh|en] [--no-docx]
```

Outputs `Inspection_Report_<site>_<timestamp>.md/.docx` per site, and `Inspection_Summary_<timestamp>.md` when more than one site is given. Exit code 3 = python-docx missing (MD still written).

Report structure (6 chapters): 1 Executive Summary · 2 Health Assessment (AC / problem distribution / access success / AP online) · 3 Detailed Problem Analysis · 4 Handling Priority (P0/P1/P2) · 5 Remediation (short/medium/long term) · 6 Conclusion (+ data notes).

### 6.3 Clean up (mcporter transport only)

After `gen_report.py` succeeded, delete the intermediate API files; keep `Inspection_Data_*` and `Inspection_Report_*`:

```bash
python -c "import glob, os; [os.remove(f) for f in glob.glob(r'<out>/step*.json')]"
```

If generation failed, keep them so the run can be fixed without calling the APIs again.

### 6.4 Summarize in chat (mandatory, in the user's language)

```
📋 Inspection complete — {site}

🏥 AC health: CPU {x}% / Memory {x}% / Disk {x}% — {rating}
📊 Access success rate: {min}%~100% — {rating}
📡 AP online rate: {rate}% ({on}/{total}) — {rating}
⚠️ Problems: {h} high-risk / {m} medium-risk

🔴 / 🔶 Act first:
  1. {top item} — {action}
  2. …

📁 Reports: MD {path} · DOCX {path}
```

For several sites: one line per site (overall rating + top issue), the summary file path, then details only for sites rated ⚠️ or 🔴.

---

## Execution flow

```
Step 0: config (optional) → transport: direct MCP | mcporter → python-docx
Step 1: getallshopsanddevofuser → resolve sites → timezone + time_window.py → classify devices
Steps 2-5 (parallel, all sites): getDeviceRunInfo ×AC · getProblemDistribute · getHistoryAccessSucOneDay
                                 · getShopNetworkProblem · getCurrentApCount · getApRegularMatch
Step 6: Inspection_Data_<site>.json → gen_report.py → MD + DOCX (+ summary) → cleanup → chat summary
```

## File structure

```
cloudnet-wlan-inspection-lite/
├── SKILL.md
├── config.json            # optional, user settings (may hold the API key)
├── config.example.json    # all fields with examples
├── scripts/
│   ├── mcporter_call.py   # mcporter fallback: call one tool, save clean JSON
│   ├── time_window.py     # today 00:00 → now in a timezone (host tz detection)
│   └── gen_report.py      # ratings + MD/DOCX reports, en/zh, multi-site summary
└── references/
    └── data-format.md     # data file schema
```

## config.json field reference (all optional)

| Field | Type | Default | Description |
|---|---|---|---|
| `shops` | array \| `"all"` | ask the user | `[{ "name": "...", "timezone": "..." }]`; `"all"` inspects every site |
| `timezone` | string | site location / host tz | IANA name used for sites without their own `timezone` |
| `language` | `en` \| `zh` | user's language | Report language |
| `output_dir` | string | `reports` | Report directory, relative to the working directory |
| `mcporter_name` | string | `Cloudnet` | mcporter connection name (mcporter transport only) |
| `api_key` | string | — | Cloudnet API key (mcporter transport only) |
| `base_url` | string | `https://cloudnet1.h3c.com` | Cloudnet platform address (mcporter transport only) |
