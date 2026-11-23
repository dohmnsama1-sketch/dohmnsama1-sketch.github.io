#!/usr/bin/env python3
"""Streaming XAUUSD bid/ask tick-data quality gate and M5 aggregation.

Source: public Dukascopy-derived weekly data repository, pinned commit.
Independent feed: it is NOT the broker's fills, and not an MT5 Strategy Tester.
Python 3.11+, standard library only. Outputs small diagnostics, not raw ticks.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import shutil
import statistics
import tempfile
import urllib.request
from collections import Counter

REPO = "Touhid-HZ/xauusd-tick-data-2026"
PIN = "019f74d942545196adab8e481338fde7c4df67c4"
HEADER = ["timestamp", "ask", "bid", "ask_volume", "bid_volume"]
UTC = dt.timezone.utc


def week_numbers(spec: str) -> list[int]:
    weeks: set[int] = set()
    for token in spec.split(","):
        token = token.strip()
        if "-" in token:
            left, right = (int(part) for part in token.split("-", 1))
            if right < left:
                raise ValueError("week range is descending")
            weeks.update(range(left, right + 1))
        else:
            weeks.add(int(token))
    if not weeks or min(weeks) < 1 or max(weeks) > 47:
        raise ValueError("only published weeks 1..47 are supported by this pinned snapshot")
    return sorted(weeks)


def quantile_sorted(numbers: list[float], p: float) -> float | None:
    if not numbers:
        return None
    index = (len(numbers)-1)*p
    lo = int(index)
    hi = min(lo+1, len(numbers)-1)
    return round(numbers[lo]+(numbers[hi]-numbers[lo])*(index-lo), 6)


def download_file(source_url: str, target: pathlib.Path, limit_mb: int = 64) -> dict:
    request = urllib.request.Request(source_url, headers={
        "User-Agent": "ZALAH-Research-QualityGate/1.0 (non-commercial market-data study)"
    })
    sha = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as out:
        while True:
            block = response.read(1024*1024)
            if not block:
                break
            total += len(block)
            if total > limit_mb*1024*1024:
                raise ValueError("download exceeds configured size cap")
            sha.update(block)
            out.write(block)
    return {"bytes": total, "sha256": sha.hexdigest()}


def parse_tick_row(row: list[str]) -> tuple[str, float, float]:
    if len(row) != 5:
        raise ValueError("tick row must have exactly 5 fields")
    timestamp = row[0]
    if len(timestamp) != 23 or timestamp[4] != "-" or timestamp[10] != " " or timestamp[19] != ".":
        raise ValueError("timestamp must be UTC YYYY-MM-DD HH:MM:SS.mmm")
    # Strict timestamp validation prevents silently merging malformed calendar dates.
    dt.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
    ask, bid = float(row[1]), float(row[2])
    if not (math.isfinite(ask) and math.isfinite(bid) and 0 < bid <= ask):
        raise ValueError("nonpositive, nonfinite or crossed bid/ask")
    return timestamp, ask, bid


def new_bar(key: str, ask: float, bid: float) -> dict:
    return {
        "time": key,
        "bid_open": bid, "bid_high": bid, "bid_low": bid, "bid_close": bid,
        "ask_open": ask, "ask_high": ask, "ask_low": ask, "ask_close": ask,
        "ticks": 0, "spread_sum": 0.0,
    }


def consume_tick(bar: dict, ask: float, bid: float) -> None:
    bar["bid_high"] = max(bar["bid_high"], bid)
    bar["bid_low"] = min(bar["bid_low"], bid)
    bar["bid_close"] = bid
    bar["ask_high"] = max(bar["ask_high"], ask)
    bar["ask_low"] = min(bar["ask_low"], ask)
    bar["ask_close"] = ask
    bar["ticks"] += 1
    bar["spread_sum"] += ask-bid


def m5_bucket(timestamp: str) -> str:
    return timestamp[:14] + f"{int(timestamp[14:16])//5*5:02d}:00"


def summarize_gz(path: pathlib.Path, week: int, bars: list[dict], previous: str | None) -> tuple[dict, str | None]:
    rows = 0
    count_by_date: Counter[str] = Counter()
    first = last = None
    samples: list[float] = []
    spread_max = 0.0
    spread_sum = 0.0
    active_bar: dict | None = bars[-1] if bars else None
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        if next(reader) != HEADER:
            raise ValueError(f"week {week}: wrong schema/header")
        for row in reader:
            timestamp, ask, bid = parse_tick_row(row)
            if previous is not None and timestamp < previous:
                raise ValueError(f"week {week}: non-monotonic timestamp {timestamp}")
            previous = timestamp
            if first is None:
                first = timestamp
            last = timestamp
            rows += 1
            count_by_date[timestamp[:10]] += 1
            spread = ask-bid
            spread_sum += spread
            spread_max = max(spread_max, spread)
            if rows % 211 == 0:
                samples.append(spread)
            key = m5_bucket(timestamp)
            if active_bar is None or key != active_bar["time"]:
                if active_bar is not None and key < active_bar["time"]:
                    raise ValueError("bar timestamp went backwards")
                active_bar = new_bar(key, ask, bid)
                bars.append(active_bar)
            consume_tick(active_bar, ask, bid)
    if not rows:
        raise ValueError(f"week {week}: empty file")
    samples.sort()
    return {
        "week": week, "rows": rows, "first_tick_utc": first, "last_tick_utc": last,
        "days_with_ticks": len(count_by_date),
        "mean_spread_price": round(spread_sum/rows, 6),
        "sampled_p50_spread_price": quantile_sorted(samples, .5),
        "sampled_p95_spread_price": quantile_sorted(samples, .95),
        "sampled_p99_spread_price": quantile_sorted(samples, .99),
        "max_spread_price": round(spread_max, 6),
        "spread_sample_frequency": 211,
    }, previous


def read_catalog(path: pathlib.Path) -> dict:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog.get("instrument", "").split()[0] != "XAUUSD":
        raise ValueError("catalog instrument does not match")
    return catalog


def validate_source_week(week_summary: dict, expected: dict) -> None:
    if week_summary["rows"] != expected["rows"]:
        raise ValueError(f"week {week_summary['week']}: tick count differs from pinned catalog")
    if (week_summary["first_tick_utc"] != expected["first_tick_utc"] or
            week_summary["last_tick_utc"] != expected["last_tick_utc"]):
        raise ValueError(f"week {week_summary['week']}: time coverage differs from pinned catalog")


def write_m5(path: pathlib.Path, bars: list[dict]) -> None:
    fields = ["time", "bid_open", "bid_high", "bid_low", "bid_close",
              "ask_open", "ask_high", "ask_low", "ask_close", "ticks", "avg_spread"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in bars:
            writer.writerow({
                **{k: item[k] for k in fields if k not in ("avg_spread",)},
                "avg_spread": round(item["spread_sum"]/item["ticks"], 6)
            })


def run(weeks: list[int], output: pathlib.Path, fetch=download_file) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    root = f"https://raw.githubusercontent.com/{REPO}/{PIN}"
    with tempfile.TemporaryDirectory(prefix="zalah-tick-") as temp:
        tempdir = pathlib.Path(temp)
        catalog_path = tempdir/"DATA_STATUS.json"
        catalog_fetch = fetch(root+"/DATA_STATUS.json", catalog_path)
        catalog = read_catalog(catalog_path)
        inventory = {int(d["week"]): d for d in catalog["files"]}
        previous: str | None = None
        bars: list[dict] = []
        summaries: list[dict] = []
        for week in weeks:
            path = tempdir/f"XAUUSD_2026_w{week:02d}.csv.gz"
            download = fetch(f"{root}/data/tick/{path.name}", path)
            result, previous = summarize_gz(path, week, bars, previous)
            validate_source_week(result, inventory[week])
            result["file_bytes"] = download["bytes"]
            result["file_sha256"] = download["sha256"]
            summaries.append(result)
            path.unlink()
        m5_path = output/"xauusd_bidask_m5.csv"
        write_m5(m5_path, bars)
        report = {
            "status": "public-feed-data-quality-only_not_broker_validation",
            "source_repository": REPO,
            "pinned_source_commit": PIN,
            "catalog_sha256": catalog_fetch["sha256"],
            "downloaded_weeks": weeks,
            "total_ticks_validated": sum(item["rows"] for item in summaries),
            "total_m5_bars": len(bars),
            "first_tick_utc": summaries[0]["first_tick_utc"],
            "last_tick_utc": summaries[-1]["last_tick_utc"],
            "source_note": "Public third-party Dukascopy-derived BID/ASK quotes, NOT Exness fills or guaranteed data usage rights.",
            "weeks": summaries,
        }
        (output/"quality.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weeks", default="1", help="1,2,3 or 1-3; max source week 47")
    parser.add_argument("--output", default="risklab/mt5/research/output")
    args = parser.parse_args()
    report = run(week_numbers(args.weeks), pathlib.Path(args.output))
    print(json.dumps({k: report[k] for k in
        ["status", "pinned_source_commit", "downloaded_weeks", "total_ticks_validated",
         "total_m5_bars", "first_tick_utc", "last_tick_utc"]}, indent=2))


if __name__ == "__main__":
    main()
