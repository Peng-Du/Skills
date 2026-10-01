# Cloudnet WLAN Inspection (Lite Edition)

## Overview

A quick day-to-day health check for H3C Cloudnet wireless sites. The skill calls the Cloudnet MCP server through the `mcporter` CLI, collects AC health, problem distribution, access success rate, Cloudnet problem reasoning and AP online rate, and produces an English report — **"Wireless Network O&M Inspection Report (Lite Edition)"** — in both Markdown and DOCX.

Design principle: the LLM extracts and evaluates the data; the scripts only call the APIs and format the report.

## When to Use This Skill

Trigger words: *inspection*, *lite inspection*, *WLAN inspection*, *wireless network inspection*, *cloudnet inspection*.

## Prerequisites

- [mcporter](https://www.npmjs.com/package/mcporter) CLI ≥ 0.9.0 — `npm install -g mcporter`
- Python 3 (scripts use the standard library only, except DOCX output)
- `python-docx` for the DOCX report — `pip install python-docx` (the MD report is still produced without it)
- A Cloudnet API key

## Setup

Copy `config.example.json` to `config.json` in the skill directory and fill it in:

```json
{
  "mcporter_name": "Cloudnet",
  "api_key": "your-cloudnet-api-key",
  "timezone": "Europe/Madrid",
  "shops": [
    { "name": "Spain" }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `mcporter_name` | Yes | Connection name used with `mcporter config add` |
| `api_key` | Yes | Cloudnet API key |
| `timezone` | No | IANA timezone of the site, default `Asia/Shanghai` |
| `shops[].name` | Yes | Site name; the shopId is looked up automatically |

`config.json` is git-ignored — never commit your API key. If the MCP connection is missing, the skill registers it with `--scope home`, so the key is stored in `~/.mcporter/mcporter.json` rather than in a project folder.

## Inspection Flow

| Step | What | Cloudnet MCP tool |
|------|------|-------------------|
| 0 | Pre-checks: config, mcporter, MCP connection, site, python-docx | — |
| 1 | Site shopId and AC (or router acting as AC) | `getallshopsanddevofuser` |
| 2 | AC health (CPU / memory / disk) | `getDeviceRunInfo` |
| 3 | Problem distribution + access success rate (today, site timezone) | `getProblemDistribute`, `getHistoryAccessSucOneDay` |
| 4 | Cloudnet problem reasoning | `getShopNetworkProblem` |
| 5 | AP online rate and offline APs | `getCurrentApCount`, `getApRegularMatch` |
| 6 | Assemble data and generate MD + DOCX report | `scripts/gen_report.py` |

Steps 2–5 run in parallel. Intermediate `reports/step*.json` files are deleted after the report is generated successfully.

### Rating thresholds

| Item | 🟢 Normal | ⚠️ Needs attention | 🔴 Critical |
|------|-----------|--------------------|-------------|
| CPU | ≤50% | ≤70% | >70% |
| Memory / Disk | ≤70% | ≤85% | >85% |
| Access success rate / AP online rate | ≥98% | ≥95% | <95% |

## Report

Written to `reports/` in the current working directory:
- `Inspection_Report_<site>_<timestamp>.md`
- `Inspection_Report_<site>_<timestamp>.docx`
- `Inspection_Data_<site>_<timestamp>.json` (the structured data behind the report)

Chapters: Executive Summary · Health Assessment · Detailed Problem Analysis · Problem Handling Priority (P0/P1/P2) · Remediation Plan · Inspection Conclusion.

## Scripts

```bash
# Call one MCP tool and save clean JSON ({"response": {...}})
python scripts/mcporter_call.py <mcp-name> <tool-name> reports/stepX.json [key=value ...]

# Generate the MD + DOCX report from the structured data file
python scripts/gen_report.py --data-file reports/Inspection_Data_<site>_<time>.json --output-dir reports/
```

Exit codes — `mcporter_call.py`: `0` OK, `1` mcporter failure / non-JSON output, `2` API returned a non-zero `response.code`. `gen_report.py`: `3` python-docx missing (MD still written).

## Files

```
cloudnet-wlan-inspection-lite/
├── SKILL.md                 # Skill definition and inspection flow
├── README.md                # This file
├── config.example.json      # Configuration template
├── scripts/
│   ├── mcporter_call.py     # mcporter call wrapper (standard library only)
│   └── gen_report.py        # MD + DOCX report generator
└── references/
    └── data-format.md       # JSON schema for the inspection data
```
