# Cloudnet AI Diagnostics

## Overview

Cloudnet AI Diagnostics is an agent skill for troubleshooting wireless client problems — slow internet, network lag, or failure to connect to WiFi — using the H3C Cloudnet management platform. It calls the Cloudnet MCP server through the `mcporter` CLI, runs a client diagnosis, and turns the result into a concise expert answer.

## When to Use This Skill

Use this skill when a user reports a wireless client problem, for example:
- "Client XX at site XX has very slow internet"
- "Device XX at site XX cannot connect to WiFi"
- "User XX at site XX reports that the network is laggy"

## Prerequisites

1. Install the `mcporter` CLI:
   ```bash
   npm install -g mcporter
   ```
2. Get a Cloudnet API key from the Cloudnet platform: **Network Management → Settings → Open Platform**.
3. Register the Cloudnet MCP server with mcporter:
   ```bash
   mcporter config add cloudnet-mcp ${CLOUDNET_BASE_URL}/mcp-server/api/sse --header Authorization="Bearer ${CLOUDNET_API_KEY}"
   ```

| Variable | Required | Description |
|----------|----------|-------------|
| `CLOUDNET_API_KEY` | Yes | Cloudnet open platform API key |
| `CLOUDNET_BASE_URL` | No | Cloudnet platform address, default `https://oasis.h3c.com` |

## How It Works

1. **Extract key information** — site name and client info (MAC `xxxx-xxxx-xxxx`, IP, or username) are required; fault time is optional (defaults to now). The skill asks the user for anything missing.
2. **Look up the site ID** — `cloudnet-mcp.getallshopsanddevofuser`
3. **Run the client diagnosis** — `cloudnet-mcp.executeStaDiagnosis`
   ```bash
   mcporter call cloudnet-mcp.executeStaDiagnosis clientInfo:"xxxx-xxxx-xxxx" shopId:"SITE_ID" faultTime:"2026-03-24 10:00:00" timezone:"Asia/Shanghai"
   ```
4. **Analyze the results** — connection overview, AP/AC software versions, operation logs, device status, connection process, client and AP radio metrics, root cause inference, and diagnosis conclusion.

## Output

The answer always has three sections:
1. **Diagnosis summary** — current status and core conclusion in 1–2 sentences.
2. **Root cause analysis** — the technical cause, without irrelevant data.
3. **Recommended solutions** — specific, actionable steps.

## Files

```
cloudnet-ai-diagnosis/
├── SKILL.md    # Skill definition and troubleshooting flow
└── README.md   # This file
```
