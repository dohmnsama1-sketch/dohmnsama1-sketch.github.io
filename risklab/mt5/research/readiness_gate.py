#!/usr/bin/env python3
"""Fail-closed profitability evidence gate for ZALAH *research only*.

Never authorizes real money. No strategy is approved based on in-sample
profits, point estimates of win rate, or merely having tick data.
"""
import argparse
import json
import pathlib
import math


def judge_one(baseline: dict | None, stressed: dict | None, min_closed=100, min_holdout=30):
    reasons=[]
    if baseline is None or stressed is None:
        return {"decision":"INSUFFICIENT_EVIDENCE", "reasons":["missing relevant cost-stress run"]}
    if baseline.get("initial_equity") != 10000 or stressed.get("initial_equity") != 10000:
        reasons.append("benchmark has wrong simulated reference equity")
    for version,run in (("reference",baseline),("stressed",stressed)):
        fee=run.get("assumed_commission_usd_per_lot_round_turn")
        if not isinstance(fee,(int,float)) or not math.isfinite(fee) or not 0<=fee<=1000:
            reasons.append(f"{version} run lacks a valid explicit commission assumption")
        # Prevent a malformed or selectively edited result from claiming alpha.
        keys=("initial_equity","ending_equity","net_pnl","gross_profit","gross_loss")
        vals=[run.get(k) for k in keys]
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in vals):
            reasons.append(f"{version} run lacks internally auditable P/L components")
        else:
            starting,ending,net,gross_profit,gross_loss=vals
            if gross_profit<0 or gross_loss<0 or abs((gross_profit-gross_loss)-net)>0.05:
                reasons.append(f"{version} run gross profit/loss do not reconcile with net P/L")
            if abs((ending-starting)-net)>0.05:
                reasons.append(f"{version} run ending equity does not reconcile with net P/L")
        splits=run.get("split_60_20_20",[])
        names=[x.get("name") for x in splits] if isinstance(splits,list) else []
        if sorted(names)!=["analysis","holdout","validation"]:
            reasons.append(f"{version} run has missing or duplicated chronological partitions")
        else:
            total=run.get("number_of_closed_trades")
            crossed=run.get("boundary_crossing_trades",0)
            if not isinstance(total,int) or not isinstance(crossed,int) or crossed<0 or (
                sum(x.get("trades",0) for x in splits)+crossed!=total
            ):
                reasons.append(f"{version} run closed trade counts do not reconcile across chronological partitions")
    closed=baseline.get("number_of_closed_trades",0)
    split={x["name"]:x for x in baseline.get("split_60_20_20",[]) }
    holdout=split.get("holdout",{})
    if closed<min_closed:
        reasons.append(f"too few total independent closed trades: {closed} < {min_closed}")
    if holdout.get("trades",0)<min_holdout:
        reasons.append("too few holdout trades")
    if baseline.get("boundary_crossing_trades",0)>0 or stressed.get("boundary_crossing_trades",0)>0:
        reasons.append("cross-partition trades require separate embargoed re-runs before research approval")
    if baseline.get("net_pnl",0)<=0:
        reasons.append("negative or zero net profit after modeled trading costs")
    if holdout.get("net_pnl",0)<=0:
        reasons.append("negative or zero holdout net profit")
    if baseline.get("profit_factor") is None or baseline["profit_factor"]<=1.25:
        reasons.append("profit factor does not exceed prespecified 1.25 threshold")
    if stressed.get("net_pnl",0)<=0:
        reasons.append("adverse execution-cost stress is not profitable")
    if stressed.get("number_of_closed_trades",0)<min_closed:
        reasons.append("stressed-cost run has insufficient trades")
    if baseline.get("max_closed_equity_drawdown_fraction",1)>0.08:
        reasons.append("realized closed-equity drawdown exceeds 8% research ceiling")
    # Closed-balance P/L hides positions temporarily underwater. The OHLC
    # adverse proxy is deliberately conservative and not a tick-accurate DD.
    excursion=baseline.get("max_adverse_intrabar_equity_proxy_fraction")
    if not isinstance(excursion,(int,float)) or not math.isfinite(excursion) or excursion>0.08 or excursion<0:
        reasons.append("missing or excessive intrabar adverse-equity excursion proxy (>8% research ceiling)")
    if baseline.get("months_with_trades",0)<6:
        reasons.append("fewer than six distinct active months; insufficient regime diversity")
    monthly_share=baseline.get("positive_month_share_active")
    if not isinstance(monthly_share,(float,int)) or monthly_share<0.60:
        reasons.append("fewer than 60% of active calendar months have positive net P/L")
    largest=baseline.get("largest_trade_loss_usd")
    if not isinstance(largest,(float,int)) or largest<-(0.02*baseline["initial_equity"]):
        reasons.append("unverified or excessive largest individual realized loss")
    if not reasons:
        # A candidate worth *further testing*, not live-trading permission.
        return {"decision":"SUPERVISED_DEMO_CANDIDATE_ONLY","reasons":[
            "P/L evidence is only from an OHLC reconstruction with independent vendor quotes",
            "requires verified tick-by-tick MT5 custom symbol and live DEMO broker fill checks"]}
    return {"decision":"INSUFFICIENT_EVIDENCE","reasons":reasons}


def readiness(report:dict):
    results=report.get("results",[])
    checks=[]
    for mode in ("baseline","regime","breakout"):
        def choose(slip):
            hits=[x for x in results if
                  x.get("mode")==mode and x.get("initial_equity")==10000 and
                  abs(x.get("slippage_usd_per_oz_per_side",-100)-slip)<0.00001]
            return hits[0] if len(hits)==1 else None
        reference=choose(0.15)
        stress=choose(0.50)
        check=judge_one(reference,stress)
        checks.append({"mode":mode,**check})
    return {"mode":"research_only","real_money_release_permitted":False,
            "inputs":{"source":report.get("status"),"first":report.get("first"),
                      "last":report.get("last"),"bars":report.get("m5_bars")},
            "candidate_checks":checks,
            "hard_blockers":["No tick-exact Exness market replay",
                             "No broker-specific margin, execution, commission and swap reconciliation",
                             "No positive independent live/demo forward fill evidence",
                             "No verified $50 account min-lot risk feasibility"],
            "disclaimer":"Even supervised DEMO candidate does not guarantee profit or eliminate losses."}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    report=json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
    decision=readiness(report)
    pathlib.Path(args.output).write_text(json.dumps(decision,indent=2),encoding="utf-8")
    print(json.dumps(decision,indent=2))


if __name__=="__main__":
    main()
