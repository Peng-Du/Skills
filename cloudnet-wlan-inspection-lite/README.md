# Cloudnet WLAN Inspection (Lite Edition)

## Overview

A quick day-to-day health check for H3C Cloudnet wireless sites (version V0.1.0). The skill inspects one, several or all Cloudnet sites through the Cloudnet MCP interfaces — direct MCP tools when the session has them, the `mcporter` CLI as a fallback — collects AC health, problem distribution, access success rate, Cloudnet problem reasoning and AP online rate, and produces a **"Wireless Network O&M Inspection Report (Lite Edition)"** in Markdown and DOCX, in English or Chinese. When several sites are inspected, a multi-site summary is produced as well.

Design principle: the LLM extracts and evaluates the data; the scripts only compute ratings and format the reports.

## When to Use This Skill

Trigger words: *inspection*, *lite inspection*, *WLAN inspection*, *wireless network inspection*, *cloudnet inspection*.

## Prerequisites

- One of the following transports:
  - **Direct MCP (preferred):** the Cloudnet MCP server is already connected in the session (its tools include `getallshopsanddevofuser`). No API key needed.
  - **mcporter (fallback):** [mcporter](https://www.npmjs.com/package/mcporter) CLI ≥ 0.9.0 — `npm install -g mcporter` — plus a Cloudnet API key (Cloudnet → Network Management → Settings → Open Platform).
- Python 3 (scripts use the standard library only, except DOCX output)
- `python-docx` for the DOCX report — `pip install python-docx` (the MD report is still produced without it)

## Setup

`config.json` in the skill directory is **optional** — every field has a fallback. To set defaults, copy `config.example.json` to `config.json` and edit it:

```json
{
  "shops": [
    { "name": "Spain Office", "timezone": "Europe/Madrid" },
    { "name": "Headquarters" }
  ],
  "timezone": "Europe/Madrid",
  "language": "zh",
  "output_dir": "reports",
  "mcporter_name": "Cloudnet",
  "base_url": "https://cloudnet1.h3c.com"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `shops` | array \| `"all"` | ask the user | `[{ "name": "...", "timezone": "..." }]`; `"all"` inspects every site. Names match case-insensitively; the shopId is looked up automatically |
| `timezone` | string | site location / host tz | IANA name used for sites without their own `timezone` |
| `language` | `en` \| `zh` | user's language | Report language |
| `output_dir` | string | `reports` | Report directory, relative to the working directory |
| `mcporter_name` | string | `Cloudnet` | mcporter connection name (mcporter transport only) |
| `api_key` | string | — | Cloudnet API key (mcporter transport only; not in the example — add it to `config.json` yourself if needed) |
| `base_url` | string | `https://cloudnet1.h3c.com` | Cloudnet platform address (mcporter transport only) |

`config.json` is git-ignored — never commit your API key. With the direct MCP transport no key is needed at all. With mcporter, if the connection is missing the skill registers it with `--scope home`, so the key is stored in `~/.mcporter/mcporter.json` rather than in a project folder; the skill never prints the key.

## Inspection Flow

| Step | What | Cloudnet MCP tool |
|------|------|-------------------|
| 0 | Pre-checks: config, transport (direct MCP / mcporter), python-docx | — |
| 1 | Resolve sites, timezone per site, ACs (or router acting as AC) | `getallshopsanddevofuser` |
| 2 | AC health (CPU / memory / disk) | `getDeviceRunInfo` |
| 3 | Problem distribution + access success rate (today 00:00 → now, site timezone) | `getProblemDistribute`, `getHistoryAccessSucOneDay` |
| 4 | Cloudnet problem reasoning | `getShopNetworkProblem` |
| 5 | AP online rate and offline APs | `getCurrentApCount`, `getApRegularMatch` |
| 6 | Assemble data and generate MD + DOCX report (+ multi-site summary) | `scripts/gen_report.py` |

Steps 2–5 run in parallel, for all sites at once. A failed call is retried once and then shown as "Not collected" — one failure never aborts the inspection. With the mcporter transport, intermediate `step*.json` files are deleted after the report is generated successfully.

### Rating thresholds

| Item | 🟢 Normal | ⚠️ Needs attention | 🔴 Critical |
|------|-----------|--------------------|-------------|
| CPU | ≤50% | ≤70% | >70% |
| Memory / Disk | ≤70% | ≤85% | >85% |
| Access success rate / AP online rate | ≥98% | ≥95% | <95% |

## Report

Written to `output_dir` (default `reports/` in the current working directory):
- `Inspection_Report_<site>_<timestamp>.md`
- `Inspection_Report_<site>_<timestamp>.docx`
- `Inspection_Data_<site>_<timestamp>.json` (the structured data behind the report)
- `Inspection_Summary_<timestamp>.md` (only when several sites are inspected)

Chapters: Executive Summary · Health Assessment · Detailed Problem Analysis · Problem Handling Priority (P0/P1/P2) · Remediation Plan · Inspection Conclusion.

## Scripts

```bash
# Today 00:00 → now in a timezone (omit --tz to use the host timezone)
python scripts/time_window.py --tz Europe/Madrid

# mcporter transport: call one MCP tool and save clean JSON ({"response": {...}})
python scripts/mcporter_call.py <mcp-name> <tool-name> reports/stepX.json [key=value ...]

# Generate the MD + DOCX reports from one or more data files
python scripts/gen_report.py --data-file reports/Inspection_Data_<site>_<time>.json [--data-file ...] --output-dir reports/ [--lang zh|en] [--no-docx]
```

Exit codes — `mcporter_call.py`: `0` OK, `1` mcporter failure / non-JSON output, `2` API returned a non-zero `response.code`. `gen_report.py`: `3` python-docx missing (MD still written).

## Files

```
cloudnet-wlan-inspection-lite/
├── SKILL.md                 # Skill definition and inspection flow
├── README.md                # This file
├── config.example.json      # Configuration template (config.json is optional)
├── scripts/
│   ├── mcporter_call.py     # mcporter fallback: call one tool, save clean JSON
│   ├── time_window.py       # today 00:00 → now in a timezone (host tz detection)
│   └── gen_report.py        # ratings + MD/DOCX reports, en/zh, multi-site summary
└── references/
    └── data-format.md       # JSON schema for the inspection data
```
