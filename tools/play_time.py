#!/usr/bin/env python3
"""Shared response-time ledger; an assistant safeguard, not an account lock."""

import argparse
from datetime import datetime, time, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "campaigns" / "_shared" / "play-time.json"
LOCAL = ZoneInfo("America/Chicago")
UTC = timezone.utc


def stamp(value):
    return value.astimezone(UTC).isoformat()


def parse_stamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamps must include a timezone")
    return result.astimezone(UTC)


def split_interval(start, end):
    """Split at Chicago midnight, handling DST with UTC subtraction."""
    if end < start:
        raise ValueError("End precedes start")
    while start < end:
        local_date = start.astimezone(LOCAL).date()
        boundary = datetime.combine(local_date + timedelta(days=1), time(), LOCAL)
        stop = min(end, boundary.astimezone(UTC))
        yield local_date.isoformat(), (stop - start).total_seconds()
        start = stop


def usage(data, now):
    totals = {}
    intervals = list(data["intervals"])
    if data["active"]:
        intervals.append({"start": data["active"]["start"], "end": stamp(now)})
    for interval in intervals:
        for day, seconds in split_interval(parse_stamp(interval["start"]),
                                           parse_stamp(interval["end"])):
            totals[day] = totals.get(day, 0) + seconds
    return totals


def report(data, now):
    today = now.astimezone(LOCAL).date()
    used = usage(data, now).get(today.isoformat(), 0)
    limit = 3600 if today.weekday() < 5 else 7200
    remaining = max(0, limit - used)
    reset = datetime.combine(today + timedelta(days=1), time(), LOCAL)
    return {
        "date": today.isoformat(), "timezone": "America/Chicago",
        "limit_seconds": limit, "used_seconds": round(used, 2),
        "remaining_seconds": round(remaining, 2), "exhausted": remaining <= 0,
        "overrun_seconds": round(max(0, used - limit), 2),
        "accepting_new_tasks": remaining > 0,
        "finish_current_task": bool(data["active"]) and remaining <= 0,
        "next_reset": reset.isoformat(), "active": data["active"],
        "measurement": "Observed response wall time plus explicitly labeled estimates",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["begin", "status", "finish"])
    parser.add_argument("--campaign", default="unspecified")
    parser.add_argument("--started-at", help="Known first clock timestamp for initial setup")
    parser.add_argument("--ended-at", help="Known response end when recovering a stale timer")
    parser.add_argument("--tail-seconds", type=float, default=0,
                        help="Labeled estimate for generation after this final tool call")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    if args.tail_seconds < 0:
        parser.error("Tail estimate must be nonnegative")
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        now = datetime.now(UTC)
        data = json.loads(LEDGER.read_text()) if LEDGER.exists() else {
            "version": 1, "timezone": "America/Chicago",
            "weekday_limit_seconds": 3600, "weekend_limit_seconds": 7200,
            "scope": "All campaigns using this shared workspace ledger",
            "intervals": [], "active": None,
        }
        if args.command == "begin":
            if data["active"]:
                sys.exit("An open response exists; resolve it without charging player idle time.")
            if report(data, now)["exhausted"]:
                print(json.dumps(report(data, now), indent=2))
                return 2
            start = parse_stamp(args.started_at) if args.started_at else now
            if start > now:
                parser.error("Start cannot be in the future")
            data["active"] = {"campaign": args.campaign, "start": stamp(start),
                              "last_checkpoint": stamp(now), "note": args.note}
        elif args.command == "finish":
            if not data["active"]:
                sys.exit("No response is running.")
            active = data["active"]
            end = parse_stamp(args.ended_at) if args.ended_at else now
            if end > now or end < parse_stamp(active["start"]):
                parser.error("End must be between response start and the current time")
            data["intervals"].append({"campaign": active["campaign"],
                                     "start": active["start"], "end": stamp(end),
                                     "kind": "measured",
                                     "note": active["note"], "finish_note": args.note})
            if args.tail_seconds:
                data["intervals"].append({"campaign": active["campaign"],
                                         "start": stamp(end),
                                         "end": stamp(end + timedelta(seconds=args.tail_seconds)),
                                         "kind": "estimated_final_generation",
                                         "note": args.note})
            data["active"] = None
        elif data["active"]:
            data["active"]["last_checkpoint"] = stamp(now)
        pending = LEDGER.with_suffix(".tmp")
        pending.write_text(json.dumps(data, indent=2) + "\n")
        os.replace(pending, LEDGER)
        result = report(data, now)
        print(json.dumps(result, indent=2))
        return 2 if result["exhausted"] and not result["active"] else 0


if __name__ == "__main__":
    sys.exit(main())
