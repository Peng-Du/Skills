# -*- coding: utf-8 -*-
"""Print the inspection time window (today 00:00 -> now) for a timezone, as JSON.

Usage:
    python time_window.py [--tz Europe/Madrid]

Without --tz the host timezone is detected (TZ env var, /etc/localtime, or the
Windows time zone name). Output example:

    {"timezone": "Europe/Madrid", "detected": false,
     "start": "2026-10-02 00:00:00.000", "end": "2026-10-02 17:50:10.000",
     "inspection_time": "2026-10-02 17:50", "stamp": "20261002_1750"}

"end" is always the current time in that timezone, never the end of the day.
Standard library only (Windows also needs the tzdata package for zoneinfo).

Exit codes: 0 OK, 1 unknown timezone / zoneinfo data missing.
"""
import argparse
import datetime
import json
import os
import sys

# Common Windows time zone names -> IANA. Extend as needed.
WINDOWS_TZ = {
    "China Standard Time": "Asia/Shanghai",
    "Taipei Standard Time": "Asia/Taipei",
    "Tokyo Standard Time": "Asia/Tokyo",
    "Korea Standard Time": "Asia/Seoul",
    "Singapore Standard Time": "Asia/Singapore",
    "SE Asia Standard Time": "Asia/Bangkok",
    "India Standard Time": "Asia/Kolkata",
    "Arabian Standard Time": "Asia/Dubai",
    "Arab Standard Time": "Asia/Riyadh",
    "Russian Standard Time": "Europe/Moscow",
    "Turkey Standard Time": "Europe/Istanbul",
    "GTB Standard Time": "Europe/Athens",
    "FLE Standard Time": "Europe/Kiev",
    "E. Europe Standard Time": "Europe/Chisinau",
    "Romance Standard Time": "Europe/Paris",
    "W. Europe Standard Time": "Europe/Berlin",
    "Central Europe Standard Time": "Europe/Budapest",
    "Central European Standard Time": "Europe/Warsaw",
    "GMT Standard Time": "Europe/London",
    "Greenwich Standard Time": "Atlantic/Reykjavik",
    "UTC": "UTC",
    "South Africa Standard Time": "Africa/Johannesburg",
    "Egypt Standard Time": "Africa/Cairo",
    "E. South America Standard Time": "America/Sao_Paulo",
    "Argentina Standard Time": "America/Buenos_Aires",
    "SA Pacific Standard Time": "America/Bogota",
    "Eastern Standard Time": "America/New_York",
    "Central Standard Time": "America/Chicago",
    "Mountain Standard Time": "America/Denver",
    "Pacific Standard Time": "America/Los_Angeles",
    "Central Standard Time (Mexico)": "America/Mexico_City",
    "AUS Eastern Standard Time": "Australia/Sydney",
    "New Zealand Standard Time": "Pacific/Auckland",
}


def detect_tz():
    tz = os.environ.get("TZ")
    if tz and "/" in tz:
        return tz
    if os.path.islink("/etc/localtime"):
        target = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in target:
            return target.split("zoneinfo/", 1)[1]
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation")
            name = winreg.QueryValueEx(key, "TimeZoneKeyName")[0].strip("\x00 ")
            if name in WINDOWS_TZ:
                return WINDOWS_TZ[name]
            sys.stderr.write("[time_window] unmapped Windows time zone '%s'\n" % name)
        except OSError:
            pass
    return None


def main():
    ap = argparse.ArgumentParser(description="Inspection time window for a timezone.")
    ap.add_argument("--tz", help="IANA timezone, e.g. Europe/Madrid (default: host timezone)")
    args = ap.parse_args()

    tz_name, detected = args.tz, False
    if not tz_name:
        tz_name, detected = detect_tz(), True
    if not tz_name:
        tz_name = "Asia/Shanghai"
        sys.stderr.write("[time_window] host timezone not detected; falling back to Asia/Shanghai\n")

    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(tz_name)
    except Exception as e:  # ZoneInfoNotFoundError, missing tzdata on Windows
        sys.stderr.write("[time_window] ERROR: timezone '%s' unavailable (%s). "
                         "On Windows run: pip install tzdata\n" % (tz_name, e))
        sys.exit(1)

    now = datetime.datetime.now(tz)
    print(json.dumps({
        "timezone": tz_name,
        "detected": detected,
        "start": now.strftime("%Y-%m-%d 00:00:00.000"),
        "end": now.strftime("%Y-%m-%d %H:%M:%S.000"),
        "inspection_time": now.strftime("%Y-%m-%d %H:%M"),
        "stamp": now.strftime("%Y%m%d_%H%M"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
