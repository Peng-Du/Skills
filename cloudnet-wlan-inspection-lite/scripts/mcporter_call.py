# -*- coding: utf-8 -*-
"""Call one Cloudnet MCP tool through mcporter and save the clean result as JSON.

Usage:
    python mcporter_call.py <mcp-name> <tool-name> <output.json> [key=value ...]

Example:
    python mcporter_call.py Cloudnet getProblemDistribute reports/step3a.json \
        shopId=1224164 "startTime=2026-05-19 00:00:00.000" \
        "endTime=2026-05-19 10:00:00.000" timezone=Asia/Shanghai

The saved file contains only {"response": {...}}; the large outputSchema block
that mcporter prints is dropped. Standard library only, no third-party packages.

Exit codes:
    0  success (response.code == 0)
    1  bad usage / mcporter not found / mcporter failed / output not JSON
    2  the API answered with a non-zero response.code (file is still saved)
"""
import json
import os
import shutil
import subprocess
import sys

TIMEOUT_MS = 60000


def fail(msg, code=1):
    sys.stderr.write("[mcporter_call] ERROR: " + msg + "\n")
    sys.exit(code)


def parse_json(text):
    """Parse mcporter stdout, tolerating log lines before the JSON body."""
    text = text.strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in mcporter output")
    return json.loads(text[start:end + 1])


def main(argv):
    if len(argv) < 4:
        sys.stderr.write(__doc__)
        sys.exit(1)
    server, tool, out_path = argv[1], argv[2], argv[3]
    args = argv[4:]
    for a in args:
        if "=" not in a:
            fail("argument '%s' is not in key=value format" % a)

    exe = shutil.which("mcporter")  # resolves mcporter.cmd on Windows
    if not exe:
        fail("mcporter not found on PATH. Install it with: npm install -g mcporter")

    # --raw-strings keeps values such as serial numbers and dim=1 as strings;
    # every parameter used by this skill accepts a string.
    cmd = [exe, "call", "%s.%s" % (server, tool)] + args + [
        "--output", "json", "--raw-strings", "--timeout", str(TIMEOUT_MS)]
    env = dict(os.environ, NO_COLOR="1", FORCE_COLOR="0")
    try:
        proc = subprocess.run(cmd, capture_output=True, env=env,
                              timeout=TIMEOUT_MS / 1000 + 30)
    except subprocess.TimeoutExpired:
        fail("mcporter timed out calling %s.%s" % (server, tool))

    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        fail("mcporter exited with code %d\n%s\n%s" % (proc.returncode, stdout[-2000:], stderr[-2000:]))

    try:
        result = parse_json(stdout)
    except ValueError as e:
        fail("%s\n--- stdout ---\n%s\n--- stderr ---\n%s" % (e, stdout[-2000:], stderr[-2000:]))

    response = result.get("response", result) if isinstance(result, dict) else result
    clean = {"response": response}

    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

    code = response.get("code") if isinstance(response, dict) else None
    if code not in (0, None):
        fail("%s returned code %s: %s (saved to %s)"
             % (tool, code, response.get("message", ""), out_path), code=2)
    print("[mcporter_call] OK %s -> %s" % (tool, out_path))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):  # GBK consoles on Chinese Windows
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main(sys.argv)
