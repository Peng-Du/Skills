---
name: cloudnet-wlan-inspection-lite
description: |
  Cloudnet WLAN wireless network inspection skill (Lite edition). Calls the Cloudnet MCP interfaces via mcporter and runs a 6-step inspection flow:
  get site information → AC health → problem distribution and access success rate → Cloudnet problem reasoning → AP online rate → generate the inspection report.
  Outputs the inspection report in English in both MD and DOCX formats, titled "Wireless Network O&M Inspection Report (Lite Edition)".
  Suitable for quick day-to-day health checks.
  Trigger words: inspection, lite inspection, WLAN inspection, wireless network inspection, cloudnet inspection.
  Prerequisites: mcporter CLI + cloudnet MCP server configuration (API key authentication) + python-docx (for the DOCX report).
---

# Cloudnet WLAN Inspection Skill (Lite Edition)

> **Version: V0.0.3**
>
> 🎯 **Design principle: the LLM does data extraction and evaluation; scripts only handle report formatting and output (both MD and DOCX).**
>
> 📂 **Paths:** `<skill-dir>` below is this skill's base directory (where this SKILL.md lives). `scripts/` and `references/` are under `<skill-dir>`; `reports/` is created in the current working directory.

## Step 0: Pre-checks (must run first)

### 0.1 Read the configuration file

```bash
# Read config.json in the skill root directory
cat <skill-dir>/config.json
```

**config.json format:**
```json
{
  "mcporter_name": "Cloudnet",
  "api_key": "xxxxxxxx",
  "timezone": "Asia/Shanghai",
  "shops": [
    { "name": "Site name" }
  ]
}
```

> 💡 `shops` only needs `name` (the site name); the shopId is fetched automatically by the Step 1 API during the inspection.
>
> 💡 `timezone` is optional (IANA name, default `Asia/Shanghai`). Set it to the **site's** timezone, e.g. `Europe/Madrid`; it is used for the Step 3 time window and passed to the APIs.
>
> ⚠️ Never print the `api_key` value in the chat or logs.

If `api_key` is placeholder text (e.g. "fill in here"), prompt the user to fill in a real API key and then run the inspection again.

### 0.2 Check the mcporter CLI

```bash
mcporter --version
```
- Pass: ≥ 0.9.0 | Fail: prompt `npm install -g mcporter`

### 0.3 Check and configure the Cloudnet MCP connection

**The only MCP address (production environment):**
```
https://cloudnet1.h3c.com/mcp-server/api/sse
```

```bash
mcporter config list
```
- If a configuration matching `mcporter_name` already exists in the list → ✅ Pass
- If it does not exist → configure it automatically:

```bash
mcporter config add <mcporter_name> https://cloudnet1.h3c.com/mcp-server/api/sse --transport sse --header "Authorization=Bearer <API_KEY>" --scope home
```

> 💡 `--scope home` stores the key in `~/.mcporter/mcporter.json`. Without it, mcporter writes `config/mcporter.json` under the current working directory, which can put the API key inside a project folder.

Verify the connection with a real call (it must print `OK`):

```bash
python <skill-dir>/scripts/mcporter_call.py <mcporter_name> getallshopsanddevofuser reports/step1.json
```

### 0.4 Confirm the site to inspect

Prefer the `shops` list in `config.json` (name field only):
- Only 1 site → use it directly, no need to ask
- Multiple sites → list them for the user to choose from
- shops is empty → ask the user to enter a site name

> ⚠️ Never assume a site name; it must come from an explicit source. **The shopId is obtained from the Step 1 API query and does not need to be pre-filled in config.json.**

### 0.5 Check python-docx (for the DOCX report)

```bash
python -c "import docx; print('OK')"
```
- Pass: ✅ | Fail: prompt `pip install python-docx` (only affects DOCX output; the MD report can still be generated)

### 0.6 Output the check results

```
✅ mcporter v0.9.0
✅ Cloudnet MCP connection: <mcporter_name>
✅ Site to inspect: XXX
✅ python-docx

All set. Starting the inspection.
```

If any item fails, list each one with ❌ and how to fix it, and **do not continue**.

---

## mcporter Calling Conventions (must read)

### Rule 1: Pass no arguments to tools that take no parameters

```bash
# ✅ Correct
mcporter call <mcp-name> getallshopsanddevofuser

# ❌ Wrong
mcporter call <mcp-name> getallshopsanddevofuser --args '{}'
```

### Rule 2: Use key=value format for tools that take parameters (PowerShell compatible)

```bash
# ✅ Correct
mcporter call <mcp-name> getDeviceRunInfo devSN=210235A2G0B206000003
mcporter call <mcp-name> getProblemDistribute shopId=2673243 "startTime=2026-05-19 00:00:00.000" "endTime=2026-05-19 10:00:00.000" timezone=Asia/Shanghai

# ❌ Wrong — single-quoted JSON fails to parse under PowerShell
mcporter call <mcp-name> getDeviceRunInfo --args '{"devSN":"210235A2G0B206000003"}'
```

### Rule 3: Save each API result as a separate JSON file

> mcporter output contains a lot of schema information and is easily truncated in logs. **Use mcporter_call.py to save clean JSON.**

```bash
# ✅ Correct
python <skill-dir>/scripts/mcporter_call.py <mcp-name> <tool-name> reports/stepX.json [key=value ...]

# ❌ Wrong — PowerShell redirection has encoding problems
mcporter call ... > reports/stepX.json
```

> 💡 mcporter_call.py only extracts the mcporter output and saves it to a file, with no third-party dependencies. It runs `mcporter call <mcp-name>.<tool> ... --output json --raw-strings`, drops the `outputSchema` block, and saves `{"response": {...}}`. If Python is also unavailable, use cmd redirection instead: `cmd /c "mcporter call ... > reports/stepX.json 2>&1"`
>
> **Exit codes:** `0` OK · `1` mcporter missing/failed or output not JSON · `2` the API answered with a non-zero `response.code` (e.g. `17 illegal access` for a wrong serial number or an invalid API key). The JSON is still saved on exit 2; report the error instead of treating the step as empty.

---

## Inspection Steps

### Step 1: Get the site shopId and AC information (serial; must complete first)

**Tool:** `getallshopsanddevofuser` (no parameters!)

```bash
python <skill-dir>/scripts/mcporter_call.py <mcp-name> getallshopsanddevofuser reports/step1.json
```

**LLM processing:** Extract from step1.json:
- Match the site name specified by the user (from config.json or user input) → `shopId`
- Devices with customType=ac under that site → `devSN`, `devModel`, `devAlias`, `status`, `softVer`
- **No customType=ac device?** Small sites often use a router with a built-in AC (e.g. MSR1104S-W, customType=router). Use that device for Step 2 and note "acts as AC" in the report. Confirm with Step 5B: the APs' `acSN` is the device acting as AC. If no device fits, skip Step 2 and set `ac: []`.
- `devModel` may contain an invisible zero-width character (U+200B); strip it.
- Name matching: match `shops[].name` against `shopName` case-insensitively; a unique partial match (e.g. "Spain" → "Spain Office") is acceptable, but state the match in the report notes.
- If the site name cannot be matched, list all sites for the user to choose from

> 💡 The shopId is fetched live from the API in this step; config.json does not need it pre-filled.

### Steps 2-5: Collect data in parallel

> ⚠️ Steps 2/3/4/5 have no dependencies on each other and **must be started at the same time**.

#### Step 2: AC health

**Tool:** `getDeviceRunInfo`

```bash
python <skill-dir>/scripts/mcporter_call.py <mcp-name> getDeviceRunInfo reports/step2.json devSN=<AC serial number>
```

**LLM extracts:** cpuRatio / memoryRatio / diskRatio / speed_up / speed_down

**Evaluation criteria:**
| Check item | 🟢 Normal | ⚠️ Needs attention | 🔴 Critical |
|--------|---------|-----------|---------|
| CPU | ≤50% | ≤70% | >70% |
| Memory | ≤70% | ≤85% | >85% |
| Disk | ≤70% | ≤85% | >85% |

#### Step 3: Problem distribution + access success rate (2 calls in parallel)

**Tool A:** `getProblemDistribute`

```bash
python <skill-dir>/scripts/mcporter_call.py <mcp-name> getProblemDistribute reports/step3a.json shopId=<site ID> "startTime=<today 00:00:00.000>" "endTime=<current time>" timezone=<timezone>
```

**LLM extracts:** The TOP 5 problem types sorted by times in descending order, with their subcategory details

> ⚠️ The API may return every category **twice** in `data[]`. Keep one entry per `type` before ranking.

**Tool B:** `getHistoryAccessSucOneDay` (same parameters as above)

```bash
python <skill-dir>/scripts/mcporter_call.py <mcp-name> getHistoryAccessSucOneDay reports/step3b.json shopId=<site ID> "startTime=<today 00:00:00.000>" "endTime=<current time>" timezone=<timezone>
```

**LLM extracts:** The lowest access success rate, the time it occurred, and the number of time periods below 98%

> ⚠️ **Time window rules (Step 3A and 3B):**
> - `timezone` = config.json `timezone` (default `Asia/Shanghai`). Returned `RT` times are in that timezone.
> - `<today>` and `<current time>` must be computed **in that timezone**, not the machine's local time.
> - `endTime` must be the **current time**, never the end of the day: with a future `endTime`, getHistoryAccessSucOneDay returns samples stamped with times that have not happened yet.
> - An empty `data[]` means no access attempts in the window → rating "No data", not a failure.

**Evaluation:** ≥98% 🟢 | ≥95% ⚠️ | <95% 🔴

#### Step 4: Cloudnet problem reasoning

**Tool:** `getShopNetworkProblem`

```bash
python <skill-dir>/scripts/mcporter_call.py <mcp-name> getShopNetworkProblem reports/step4.json shopId=<site ID>
```

**LLM extracts:**
- `data.summary[]` → count high-risk (3) / medium-risk (2) items by alarmLevel
- `data.data[]` → group by alarmLevel and extract reasoningType / count / reasoningCategory / suggestion / status

#### Step 5: AP online rate (2 calls in parallel)

**Tool A:** `getCurrentApCount`

```bash
python <skill-dir>/scripts/mcporter_call.py <mcp-name> getCurrentApCount reports/step5a.json shopId=<site ID>
```

**LLM extracts:** online / offline / total, and calculates the online rate

**Tool B:** `getApRegularMatch`

```bash
python <skill-dir>/scripts/mcporter_call.py <mcp-name> getApRegularMatch reports/step5b.json shopId=<site ID> dim=1
```

**LLM extracts:** Filter the APs with Ss=2 from detail[] and extract the apName list

> 💡 `dim=1` is a fuzzy match on AP name/SN/MAC/IP; it matches H3C serial numbers, which contain "1". If `totalCount` is larger than `len(detail)`, the offline list may be partial: set `ap.list_complete=false`.

**Evaluation:** ≥98% 🟢 | ≥95% ⚠️ | <95% 🔴

### Step 6: Assemble the data + generate the dual-format report

#### 6.1 Assemble the structured inspection data

The LLM reads the step1~step5b JSON files one by one, extracts the key fields from `response.data`, and assembles them into a JSON file that conforms to the format in `references/data-format.md`.

```bash
# Write the structured data to reports/Inspection_Data_<site>_<yyyyMMdd_HHmm>.json
```

> 📄 Data format reference: read `<skill-dir>/references/data-format.md` for the complete JSON schema **before** writing the file.
>
> The data file holds the raw numbers (the script computes ratings, the TOP 5 and the access statistics) plus an `analysis` block with all report prose written by the LLM: executive summary, P0/P1/P2 priorities, short/medium/long-term remediation, conclusion and data notes.

**Alarm level evaluation criteria:**

| Check item | 🟢 Normal | ⚠️ Needs attention | 🔴 Critical |
|--------|---------|-----------|---------|
| CPU | ≤50% | ≤70% | >70% |
| Memory | ≤70% | ≤85% | >85% |
| Disk | ≤70% | ≤85% | >85% |
| Access success rate | ≥98% | ≥95% | <95% |
| AP online rate | ≥98% | ≥95% | <95% |

#### 6.2 Generate the MD + DOCX dual-format report

```bash
python <skill-dir>/scripts/gen_report.py --data-file reports/Inspection_Data_<site>_<time>.json --output-dir reports/
```

This script outputs both (exit code 3 = python-docx missing; the MD report is still written):
- MD report: `reports/Inspection_Report_<site>_<timestamp>.md`
- DOCX report: `reports/Inspection_Report_<site>_<timestamp>.docx`

**Report structure (6 chapters):**
```
1. Executive Summary → key metrics + risk overview
2. Health Assessment → AC health + problem distribution + access success rate + AP online rate
3. Detailed Problem Analysis → details of high-risk / medium-risk problems
4. Problem Handling Priority → P0/P1/P2 grading
5. Remediation Plan → short term / medium term / long term
6. Inspection Conclusion → overall assessment + key risks + trend recommendations
```

**Report writing requirements:**
- Entirely in English, with terms/abbreviations kept in English (CPU, RSSI, AP, AC, SSID, Portal, DHCP, SNMP, ARP, DNS, MTU, MSS, MCP, Cloudnet, mcporter, etc.)
- First page: the title "Wireless Network O&M Inspection Report (Lite Edition)" + site name + inspection time + inspection tool name
- Rate each item according to the alarm level evaluation criteria
- Problem analysis must be based on actual data; do not fabricate anything
- The remediation plan must give targeted recommendations based on the actual problems

#### 6.3 Delete the temporary step files (mandatory)

The `step*.json` files are only intermediate API results. Once both reports exist, delete them (works in PowerShell and bash):

```bash
python -c "import glob, os; [os.remove(f) for f in glob.glob('reports/step*.json')]"
```

- Run this **only after gen_report.py exited 0** and both the MD and DOCX paths were printed. If report generation failed, keep the step files so the run can be fixed and re-run without calling the APIs again.
- Delete only `reports/step*.json`. Keep `Inspection_Data_*.json` (the structured data behind the report) and all `Inspection_Report_*` files.

#### 6.4 Output the inspection summary to the user (mandatory)

> ⚠️ **After the report is generated, you must output a summary in the chat interface; do not just say "the report has been generated".**

```
📋 Inspection complete — {site name}

🏥 AC health: CPU {x}% / Memory {x}% / Disk {x}% — {🟢 Normal / ⚠️ Needs attention / 🔴 Critical}
📊 Access success rate: {min}%~100% — {🟢/⚠️/🔴}
📡 AP online rate: {rate}% (online {on} / total {total}) — {🟢/⚠️/🔴}
⚠️ Problems: {h} high-risk / {m} medium-risk

🔴 Requires immediate action:
  1. {highest-priority problem} — {recommendation}
  2. {second-highest-priority problem} — {recommendation}

📁 Reports generated:
  MD: {full path of the md file}
  DOCX: {full path of the docx file}
```

---

## Execution Flowchart

```
Step 0: Read config.json → mcporter check → MCP connection configuration → site confirmation
        │
        ▼
Step 1: Get shopId + devSN (serial) → step1.json
        │
        ├──────────┬──────────┬──────────┐
        ▼          ▼          ▼          ▼
     Step 2      Step 3      Step 4      Step 5      ← parallel
     step2.json  step3a/b   step4.json  step5a/b
        │          │          │          │
        └──────────┴──────────┴──────────┘
                        │
                        ▼
Step 6: LLM extracts data → assemble structured JSON → gen_report.py
        │
        ├── reports/Inspection_Report_XXX.md    (MD format)
        └── reports/Inspection_Report_XXX.docx  (DOCX format)
                        │
                        ▼
              Delete reports/step*.json
                        │
                        ▼
              Output the inspection summary
```

## File Structure

```
skills/cloudnet-wlan-inspection-lite/
├── SKILL.md                        # This file
├── config.json                     # API key + site configuration (filled in by the user)
├── scripts/
│   ├── mcporter_call.py            # mcporter output extraction (no third-party dependencies)
│   └── gen_report.py               # MD + DOCX dual-format report generation (depends on python-docx)
└── references/
    └── data-format.md              # Structured JSON format definition for the inspection data
```

## config.json Field Reference

| Field | Type | Required | Description |
|------|------|------|------|
| `mcporter_name` | string | ✅ | The connection name used with mcporter config add |
| `api_key` | string | ✅ | Cloudnet API key (obtained from the Cloudnet platform) |
| `timezone` | string | | IANA timezone of the site, default `Asia/Shanghai` |
| `shops` | array | ✅ | List of sites; each site contains name |
| `shops[].name` | string | ✅ | Site name (the shopId is fetched automatically via the API during the inspection) |
