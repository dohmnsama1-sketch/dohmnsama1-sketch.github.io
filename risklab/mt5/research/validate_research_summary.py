#!/usr/bin/env python3
"""Validate exact three XAUUSD reference runs; keep tiny-$50 control separate.

No financial approval is implied by matching benchmark schema. A successful
workflow means the benchmark was generated reproducibly, NOT that it profits.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

EXPECTED={"baseline","regime","breakout"}
SLIP=0.15
CAPITAL=10000


def select_reference_runs(report:dict)->list[dict]:
    if report.get("status")!="exploratory_not_MT5_or_Exness_verified":
        raise ValueError("unrecognized external-source report status")
    selected=[
        row for row in report.get("results",[])
        if row.get("mode") in EXPECTED
        and row.get("slippage_usd_per_oz_per_side")==SLIP
        and row.get("initial_equity")==CAPITAL
        and row.get("news_event_mode")=="not_enabled"
    ]
    if len(selected)!=3 or {x["mode"] for x in selected}!=EXPECTED:
        raise ValueError("expected one $10000 no-news reference run for EACH strategy, not $50 or alternate feed")
    for row in selected:
        mode=row["mode"]
        if row.get("bootstrap_week_count",0)<26 or row.get("bootstrap_status")!="EXPLORATORY":
            raise ValueError(f"{mode}: insufficient weekly resampling diagnostics")
        if row.get("bootstrap_net_pnl_p2p5") is None or row.get("bootstrap_positive_fraction") is None:
            raise ValueError(f"{mode}: no bootstrap risk statistics")
    return sorted(selected,key=lambda x:x["mode"])


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    raw=json.loads(Path(args.input).read_text(encoding="utf-8"))
    runs=select_reference_runs(raw)
    summary={"status":"RESEARCH_PROVENANCE_VERIFIED_NOT_PROFITABILITY",
             "reference_only":True,
             "release_to_real_money":False,
             "candidates":[{
                "mode":r["mode"],
                "trades":r["number_of_closed_trades"],
                "net_pnl":r["net_pnl"],
                "bootstrap_weeks":r["bootstrap_week_count"],
                "bootstrap_lower_pnl":r["bootstrap_net_pnl_p2p5"],
                "bootstrap_positive_fraction":r["bootstrap_positive_fraction"],
                "disclaimer":"historical research, not forecast or verified live fills"
             } for r in runs]}
    Path(args.output).write_text(json.dumps(summary,indent=2),encoding="utf-8")
    for x in summary["candidates"]:
        print(f'{x["mode"]}: trades={x["trades"]} net={x["net_pnl"]} weeks={x["bootstrap_weeks"]} exploratory_2p5={x["bootstrap_lower_pnl"]} sampled_positive_fraction={x["bootstrap_positive_fraction"]}')


if __name__=="__main__":
    main()
