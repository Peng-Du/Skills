---
name: Cloudnet AI Diagnostics
description: Cloudnet AI Diagnostics is a skill for troubleshooting wireless issues such as poor client experience, network lag, and failure to connect to WiFi
version: "1.0"
metadata: { "openclaw": { "requires": { "bins": ["npm", "mcporter"] }, "primaryEnv": "CLOUDNET_API_KEY" } }
triggers:
  - "WiFi troubleshooting"
  - "Wireless network failure"
  - "Client internet is slow"
  - "Cannot connect to WiFi"
  - "Network lag"
author: Cloudnet Skills
---

# Cloudnet AI Diagnostics

Troubleshoots wireless issues such as poor client experience, network lag, and failure to connect to WiFi.

## Trigger Conditions

The user asks about a wireless client connectivity problem, for example:
- "Client XX at site XX has very slow internet"
- "Device XX at site XX cannot connect to WiFi"
- "User XX at site XX reports that the network is laggy"

## Prerequisite Environment Check

### Install the `mcporter` CLI and skill support

- mcporter: `npm install -g mcporter`
- Then install the `mcporter` skill via clawhub

### Configure MCP connection parameters

- `CLOUDNET_API_KEY` Required. The user must provide the API key of the Cloudnet management platform, which can be obtained from the Cloudnet management platform (Network Management => Settings => Open Platform)
- Optional: `CLOUDNET_BASE_URL` The Cloudnet management platform address. Defaults to https://oasis.h3c.com
- Run `mcporter config add cloudnet-mcp ${CLOUDNET_BASE_URL}/mcp-server/api/sse --header Authorization="Bearer ${CLOUDNET_API_KEY}"`


## Troubleshooting Steps

### Step 1: Extract key information

Extract the following information from the user's question:

| Information | Description | Example |
|------|------|------|
| **Site name** | Required. The site where the problem occurred | "Headquarters Office", "XX Store" |
| **Client information** | Required. MAC address or client username | MAC: `xxxx-xxxx-xxxx` or username: `zhangsan` |
| **Fault time** | Optional. Defaults to the current time if the user does not specify one | "2026-03-24 10:00:00" |

**Important**: If the site name and client information cannot be extracted, you must ask the user to provide them in full before continuing to the next step.

### Step 2: Look up the site ID

Call `cloudnet-mcp.getallshopsanddevofuser` to get all sites under the user, and find the site ID that corresponds to the site name. The site ID does not need to be explicitly shown to the user.

```bash
mcporter call cloudnet-mcp.getallshopsanddevofuser
```

### Step 3: Run the client diagnosis

Based on the extracted client information (MAC address, username, or IP address), call `executeStaDiagnosis` to run the diagnosis:

**Parameters**:
- `clientInfo`: The client MAC address in the format `xxxx-xxxx-xxxx`, or the client IP address, e.g. `192.168.1.1`, or the client username, e.g. `h3cuser1`
- `shopId`: The site ID (from Step 2); must be converted to a string
- `faultTime`: The fault time in the format `yyyy-MM-dd HH:mm:ss`; use the current time if the user does not specify one
- `timezone`: The user's time zone; defaults to `Asia/Shanghai`

- Example call when a MAC address is extracted

```bash
mcporter call cloudnet-mcp.executeStaDiagnosis clientInfo:"xxxx-xxxx-xxxx" shopId:"SITE_ID" faultTime:"2026-03-24 10:00:00" timezone:"Asia/Shanghai"
```

- Example call when a client IP address is extracted

```bash
mcporter call cloudnet-mcp.executeStaDiagnosis clientInfo:"192.168.1.1" shopId:"SITE_ID" faultTime:"2026-03-24 10:00:00" timezone:"Asia/Shanghai"
```

- Example call when a client username is extracted

```bash
mcporter call cloudnet-mcp.executeStaDiagnosis clientInfo:"h3cuser1" shopId:"SITE_ID" faultTime:"2026-03-24 10:00:00" timezone:"Asia/Shanghai"
```

### Step 4: Analyze the diagnosis results

The diagnosis response includes:
- Client connection overview data (including client access capability, current authentication method, signal strength, packet loss rate, retransmission rate, etc.)
- Software version information of the connected devices (including AP and AC)
- Cloud platform operation logs
- Device running status (including the number of CPU and memory issues on AC and AP devices)
- Client connection process data
- Client running status analysis: sampled data of the client's wireless metrics during the diagnosis period (interference, signal strength, traffic, rate selection, packet loss rate, retransmission rate, etc.)
- AP air interface environment analysis: sampled data of the AP's radio-related wireless metrics during the diagnosis period (interference, noise floor, signal-to-noise ratio, traffic, rate selection, channel utilization, number of associated users, etc.)
- Root cause inference conclusion (identifies the likely root cause of the client's problem)
- Diagnosis conclusion (including abnormal metrics and remediation suggestions)

Answer the user's question based on the diagnosis results and give specific recommendations for resolving the issue.

## Output Format

You are a senior wireless network troubleshooting expert. The troubleshooting work is now complete. Based on the user's question, extract only the diagnostic data and conclusions relevant to the problem, and give a professional, direct answer. The output must strictly follow these three sections:
1. Diagnosis summary: Summarize the current network status and the core conclusion in 1-2 sentences.
2. Root cause analysis: Analyze in depth the technical causes of the problem; avoid listing irrelevant data.
3. Recommended solutions: Provide specific, actionable implementation steps.
