# -*- coding: utf-8 -*-
"""Generate the WLAN inspection report (Lite Edition) in MD and DOCX format.

Usage:
    python gen_report.py --data-file reports/Inspection_Data_<site>_<time>.json \
        --output-dir reports/

The input format is defined in references/data-format.md. This script only
formats: it computes ratings and statistics from the numbers in the data file
and lays out the six report chapters. All narrative text comes from the
"analysis" block written by the LLM.

The DOCX file needs python-docx. If it is not installed, the MD report is still
written and the script exits with code 3.
"""
import argparse
import datetime
import json
import os
import re
import sys

TITLE = "Wireless Network O&M Inspection Report (Lite Edition)"
OK, WARN, CRIT, NODATA = "🟢 Normal", "⚠️ Needs attention", "🔴 Critical", "⚪ No data"
SEVERITY = {OK: 0, NODATA: 0, WARN: 1, CRIT: 2}


# ---------------------------------------------------------------- ratings
def rate_usage(value, normal, attention):
    """Lower is better (CPU / memory / disk)."""
    if value is None:
        return NODATA
    return OK if value <= normal else WARN if value <= attention else CRIT


def rate_rate(value):
    """Higher is better (access success rate / AP online rate)."""
    if value is None:
        return NODATA
    return OK if value >= 98 else WARN if value >= 95 else CRIT


def worst(ratings):
    return max(ratings, key=lambda r: SEVERITY[r]) if ratings else NODATA


def pct(value):
    if value is None:
        return "n/a"
    return ("%d%%" % value) if float(value).is_integer() else ("%.1f%%" % value)


# ---------------------------------------------------------------- data prep
def load(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    missing = [k for k in ("meta", "ap", "analysis") if k not in data]
    if missing:
        sys.exit("[gen_report] ERROR: data file is missing required keys: %s "
                 "(see references/data-format.md)" % ", ".join(missing))
    for k in ("site_name", "inspection_time"):
        if not data["meta"].get(k):
            sys.exit("[gen_report] ERROR: meta.%s is required" % k)
    return data


def dedupe_problems(items):
    """The API may return each category twice; keep the highest count per type."""
    merged = {}
    for p in items or []:
        key = p.get("type") or p.get("name")
        if key not in merged or (p.get("times") or 0) > (merged[key].get("times") or 0):
            merged[key] = p
    return list(merged.values())


def compute(data):
    c = {}
    acs = data.get("ac") or []
    for ac in acs:
        ac["model"] = (ac.get("model") or "").replace("\u200b", "").strip()
        ac["_ratings"] = {
            "cpu": rate_usage(ac.get("cpu"), 50, 70),
            "memory": rate_usage(ac.get("memory"), 70, 85),
            "disk": rate_usage(ac.get("disk"), 70, 85),
        }
    c["ac_rating"] = worst([r for ac in acs for r in ac["_ratings"].values()]) if acs else NODATA

    problems = dedupe_problems(data.get("problem_distribution"))
    c["problems"] = problems
    c["problem_total"] = sum(p.get("times") or 0 for p in problems)
    c["top5"] = sorted([p for p in problems if (p.get("times") or 0) > 0],
                       key=lambda p: -(p.get("times") or 0))[:5]

    samples = (data.get("access_success") or {}).get("samples") or []
    if samples:
        low = min(samples, key=lambda s: s["rate"])
        c["access_min"], c["access_min_time"] = low["rate"], low.get("time", "")
        c["access_below98"] = sum(1 for s in samples if s["rate"] < 98)
    else:
        c["access_min"], c["access_min_time"], c["access_below98"] = None, "", 0
    c["access_samples"] = len(samples)
    c["access_rating"] = rate_rate(c["access_min"])

    ap = data["ap"]
    total = ap.get("total") or 0
    c["ap_rate"] = round((ap.get("online") or 0) * 100.0 / total, 1) if total else None
    c["ap_rating"] = rate_rate(c["ap_rate"])

    items = (data.get("reasoning") or {}).get("items") or []
    c["high"] = [i for i in items if (i.get("alarm_level") or 0) >= 3]
    c["medium"] = [i for i in items if (i.get("alarm_level") or 0) == 2]
    c["low"] = [i for i in items if (i.get("alarm_level") or 0) < 2]

    risk = CRIT if c["high"] else WARN if c["medium"] else OK
    c["overall"] = worst([c["ac_rating"], c["access_rating"], c["ap_rating"], risk])
    return c


# ---------------------------------------------------------------- content
def build_blocks(data, c):
    """Return the report as a list of (kind, payload) blocks shared by MD and DOCX.

    kinds: h1, h2, p, bullets (list of str), table ((headers, rows))
    """
    meta, ap, an = data["meta"], data["ap"], data["analysis"]
    acs = data.get("ac") or []
    b = []
    add = lambda kind, payload: b.append((kind, payload))

    # 1. Executive summary
    add("h1", "1. Executive Summary")
    if an.get("executive_summary"):
        add("p", an["executive_summary"])
    rows = []
    for ac in acs:
        r = ac["_ratings"]
        rows.append(["AC %s CPU / Memory / Disk" % ac.get("name", ""),
                     "%s / %s / %s" % (pct(ac.get("cpu")), pct(ac.get("memory")), pct(ac.get("disk"))),
                     worst(list(r.values()))])
    if not acs:
        rows.append(["AC health", "No AC inspected", NODATA])
    rows += [
        ["Access success rate (lowest)",
         "%s (%d sample%s)" % (pct(c["access_min"]), c["access_samples"], "" if c["access_samples"] == 1 else "s")
         if c["access_samples"] else "No samples",
         c["access_rating"]],
        ["AP online rate",
         "%s (%s online / %s total)" % (pct(c["ap_rate"]), ap.get("online", 0), ap.get("total", 0)),
         c["ap_rating"]],
        ["Problems recorded", str(c["problem_total"]), OK if c["problem_total"] == 0 else WARN],
        ["Reasoned problems", "%d high-risk / %d medium-risk" % (len(c["high"]), len(c["medium"])),
         CRIT if c["high"] else WARN if c["medium"] else OK],
        ["Overall", "", c["overall"]],
    ]
    add("table", (["Metric", "Value", "Rating"], rows))

    # 2. Health assessment
    add("h1", "2. Health Assessment")
    add("h2", "2.1 AC Health")
    if not acs:
        add("p", "No AC was inspected for this site.")
    for ac in acs:
        add("table", (["Item", "Value"], [
            ["Device name", ac.get("name", "")],
            ["Model", ac.get("model", "")],
            ["Serial number", ac.get("sn", "")],
            ["Device type", ac.get("type", "")],
            ["Status", "Online" if ac.get("online") else "Offline"],
            ["Software version", ac.get("soft_ver", "")],
            ["Device address", ac.get("address", "") or "n/a"],
        ]))
        r = ac["_ratings"]
        add("table", (["Check item", "Value", "Threshold (Normal / Attention)", "Rating"], [
            ["CPU", pct(ac.get("cpu")), "≤50% / ≤70%", r["cpu"]],
            ["Memory", pct(ac.get("memory")), "≤70% / ≤85%", r["memory"]],
            ["Disk", pct(ac.get("disk")), "≤70% / ≤85%", r["disk"]],
        ]))
        if ac.get("speed_up_kbps") is not None or ac.get("speed_down_kbps") is not None:
            add("p", "Live throughput: %s Kbps up / %s Kbps down."
                % (ac.get("speed_up_kbps", "n/a"), ac.get("speed_down_kbps", "n/a")))
        if ac.get("note"):
            add("p", ac["note"])

    add("h2", "2.2 Problem Distribution")
    tw = meta.get("time_window") or {}
    if tw:
        add("p", "Window: %s to %s (%s)." % (tw.get("start", ""), tw.get("end", ""), tw.get("timezone", "")))
    if c["top5"]:
        rows = []
        for i, p in enumerate(c["top5"], 1):
            subs = ", ".join("%s (%d)" % (s.get("name", ""), s.get("times", 0))
                             for s in sorted(p.get("sub_types") or [], key=lambda s: -(s.get("times") or 0))
                             if (s.get("times") or 0) > 0)
            rows.append([str(i), p.get("name", p.get("type", "")), str(p.get("times", 0)), subs or "-"])
        add("table", (["#", "Problem category", "Occurrences", "Sub-types"], rows))
    else:
        add("p", "No problems were recorded in any category during the window.")

    add("h2", "2.3 Access Success Rate")
    add("table", (["Item", "Value"], [
        ["Lowest success rate", pct(c["access_min"]) if c["access_samples"] else "No samples"],
        ["Time of lowest rate", c["access_min_time"] or "n/a"],
        ["Periods below 98%", str(c["access_below98"])],
        ["Samples in window", str(c["access_samples"])],
        ["Rating", c["access_rating"]],
    ]))

    add("h2", "2.4 AP Online Rate")
    offline = ap.get("offline_aps") or []
    offline_text = ", ".join(offline) if offline else "None"
    if ap.get("list_complete") is False:
        offline_text += " (list may be incomplete)"
    add("table", (["Item", "Value"], [
        ["Total APs", str(ap.get("total", 0))],
        ["Online", str(ap.get("online", 0))],
        ["Offline", str(ap.get("offline", 0))],
        ["Online rate", pct(c["ap_rate"])],
        ["Offline AP list", offline_text],
        ["Rating", c["ap_rating"]],
    ]))

    # 3. Detailed problem analysis
    add("h1", "3. Detailed Problem Analysis")
    for title, items, level in (("3.1 High-risk Problems", c["high"], 3),
                                ("3.2 Medium-risk Problems", c["medium"], 2)):
        add("h2", title)
        if not items:
            add("p", "None. Cloudnet problem reasoning returned no items with alarm level %d." % level)
            continue
        for it in items:
            add("table", (["Field", "Value"], [
                ["Problem type", it.get("type", "")],
                ["Category", it.get("category", "")],
                ["Occurrences", str(it.get("count", ""))],
                ["Status", it.get("status", "")],
                ["Description", it.get("description", "")],
                ["Suggestion", it.get("suggestion", "")],
            ]))
    if c["low"]:
        add("h2", "3.3 Low-risk Problems")
        add("table", (["Problem type", "Category", "Occurrences", "Status"],
                      [[i.get("type", ""), i.get("category", ""), str(i.get("count", "")), i.get("status", "")]
                       for i in c["low"]]))

    # 4. Priority
    add("h1", "4. Problem Handling Priority")
    pr = an.get("priorities") or []
    if not pr:
        # Fallback so a risky site never reads "nothing to do": derive P0/P1
        # straight from the reasoning items.
        pr = [{"priority": "P0" if it in c["high"] else "P1", "item": it.get("type", ""),
               "basis": "Cloudnet reasoning, alarm level %s" % it.get("alarm_level"),
               "action": it.get("suggestion", "")} for it in c["high"] + c["medium"]]
    if pr:
        add("table", (["Priority", "Item", "Basis", "Action"],
                      [[p.get("priority", ""), p.get("item", ""), p.get("basis", ""), p.get("action", "")]
                       for p in sorted(pr, key=lambda p: p.get("priority", "P9"))]))
    elif c["overall"] in (OK, NODATA):
        add("p", "No items require handling.")
    else:
        add("p", "No priorities were provided; review the ratings in chapter 2.")

    # 5. Remediation
    add("h1", "5. Remediation Plan")
    rem = an.get("remediation") or {}
    for title, key in (("5.1 Short Term", "short_term"), ("5.2 Medium Term", "medium_term"),
                       ("5.3 Long Term", "long_term")):
        add("h2", title)
        items = rem.get(key) or []
        if items:
            add("bullets", items)
        else:
            add("p", "No actions required." if c["overall"] in (OK, NODATA) else "No actions listed.")

    # 6. Conclusion
    add("h1", "6. Inspection Conclusion")
    con = an.get("conclusion") or {}
    add("p", ("Overall assessment: %s. %s" % (c["overall"], con.get("overall", ""))).strip())
    add("h2", "Key Risks")
    add("bullets", con.get("key_risks") or ["None identified."])
    add("h2", "Trend Recommendations")
    add("bullets", con.get("trends") or ["None."])
    if an.get("notes"):
        add("h2", "Data Notes")
        add("bullets", an["notes"])
    return b


# ---------------------------------------------------------------- renderers
def cover_lines(meta):
    return [("Site", meta["site_name"]),
            ("Inspection time", meta["inspection_time"]),
            ("Inspection tool", meta.get("tool") or "Cloudnet MCP via mcporter")]


def render_md(meta, blocks):
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
    out = ["# " + TITLE, ""]
    out += ["- **%s:** %s" % kv for kv in cover_lines(meta)] + [""]
    for kind, payload in blocks:
        if kind == "h1":
            out += ["## " + payload, ""]
        elif kind == "h2":
            out += ["### " + payload, ""]
        elif kind == "p":
            out += [payload, ""]
        elif kind == "bullets":
            out += ["- " + x for x in payload] + [""]
        elif kind == "table":
            headers, rows = payload
            out.append("| " + " | ".join(esc(h) for h in headers) + " |")
            out.append("|" + "---|" * len(headers))
            out += ["| " + " | ".join(esc(x) for x in r) + " |" for r in rows]
            out.append("")
    return "\n".join(out)


def render_docx(meta, blocks, path):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Pt

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")

    for _ in range(6):
        doc.add_paragraph()
    t = doc.add_heading(TITLE, level=0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()
    for label, value in cover_lines(meta):
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.add_run(label + ": ").bold = True
        para.add_run(str(value))
    doc.add_page_break()

    for kind, payload in blocks:
        if kind == "h1":
            doc.add_heading(payload, level=1)
        elif kind == "h2":
            doc.add_heading(payload, level=2)
        elif kind == "p":
            doc.add_paragraph(payload)
        elif kind == "bullets":
            for x in payload:
                doc.add_paragraph(x, style="List Bullet")
        elif kind == "table":
            headers, rows = payload
            table = doc.add_table(rows=1, cols=len(headers))
            table.style = "Table Grid"
            for cell, text in zip(table.rows[0].cells, headers):
                cell.text = ""
                cell.paragraphs[0].add_run(str(text)).bold = True
            for row in rows:
                for cell, text in zip(table.add_row().cells, row):
                    cell.text = str(text)
            doc.add_paragraph()
    doc.save(path)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Generate the WLAN inspection report (MD + DOCX).")
    ap.add_argument("--data-file", required=True, help="Structured inspection data JSON")
    ap.add_argument("--output-dir", required=True, help="Directory for the reports")
    args = ap.parse_args()

    data = load(args.data_file)
    c = compute(data)
    blocks = build_blocks(data, c)

    os.makedirs(args.output_dir, exist_ok=True)
    site = re.sub(r'[\\/:*?"<>|\s]+', "_", data["meta"]["site_name"]).strip("_")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(os.path.abspath(args.output_dir), "Inspection_Report_%s_%s" % (site, stamp))

    md_path = base + ".md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_md(data["meta"], blocks))
    print("MD: " + md_path)

    try:
        render_docx(data["meta"], blocks, base + ".docx")
    except ImportError:
        sys.stderr.write("[gen_report] python-docx is not installed; DOCX skipped. "
                         "Install it with: pip install python-docx\n")
        sys.exit(3)
    print("DOCX: " + base + ".docx")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()
