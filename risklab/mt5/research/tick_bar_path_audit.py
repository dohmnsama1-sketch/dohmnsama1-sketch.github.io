#!/usr/bin/env python3
"""Tick-sequence validation of M5 stop-first bar approximation.

Research diagnostic only. In each M5 candle, simulate two hypothetical
independent bracket orders entered at that bar's first bid/ask update,
then observe chronological touch ordering inside the SAME candle.

This is *not* the EA's crossover strategy, not an executable order model,
not a future forecast and not evidence of profitable gold trading.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import gzip
import json
import pathlib
from collections import Counter

from public_xauusd_ingest import HEADER,parse_tick_row,m5_bucket


def first_touch(side:int, bid:float, ask:float, stop:float, target:float)->str|None:
    """Long closes at BID; short closes at ASK. Stop wins equality."""
    if side==1:
        if bid<=stop: return "stop"
        if bid>=target: return "target"
    elif side==-1:
        if ask>=stop: return "stop"
        if ask<=target: return "target"
    else:
        raise ValueError("side must be long (+1) or short (-1)")
    return None


def audit_ticks(path:pathlib.Path, stop_distance:float=2.0,
                target_distance:float=3.0)->dict:
    """One-pass weekly quote stream; derive first-hit from *actual event order*.

    Fixed $2/$3 distances are solely a path-quality probe. Spread may make
    a hypothetical bracket touch stop immediately on a wide-spread quote.
    No orders are sent, no profit is calculated.
    """
    if stop_distance<=0 or target_distance<=0:
        raise ValueError("brackets must be positive")
    counts=Counter()
    last_timestamp=None
    current=None
    candles=0
    ticks=0
    for_side=("long","short")
    def finalize(s):
        nonlocal candles
        if s is None: return
        candles+=1
        for side,name in ((1,"long"),(-1,"short")):
            rec=s[name]
            if side==1:
                both=rec["min_bid"]<=rec["stop"] and rec["max_bid"]>=rec["target"]
            else:
                both=rec["max_ask"]>=rec["stop"] and rec["min_ask"]<=rec["target"]
            counts[f"{name}_bars"]+=1
            counts[f"{name}_first_{rec['touch'] or 'none'}"]+=1
            if both:
                counts[f"{name}_both_levels_inside_m5"]+=1
                if rec["touch"]=="target":
                    counts[f"{name}_bar_stop_first_disagrees_with_tick_order"]+=1
                else:
                    counts[f"{name}_bar_stop_first_agrees_with_tick_order"]+=1

    with gzip.open(path,"rt",encoding="utf-8",newline="") as f:
        rows=csv.reader(f)
        if next(rows,None)!=HEADER:raise ValueError("unexpected raw quote schema")
        for raw in rows:
            timestamp,ask,bid=parse_tick_row(raw)
            if last_timestamp is not None and timestamp<last_timestamp:
                raise ValueError("nonmonotonic tick timestamp")
            last_timestamp=timestamp
            ticks+=1
            bucket=m5_bucket(timestamp)
            if current is None or current["bucket"]!=bucket:
                if current is not None and bucket<=current["bucket"]:
                    raise ValueError("M5 buckets not increasing")
                finalize(current)
                current={"bucket":bucket}
                current["long"]={"stop":ask-stop_distance,"target":ask+target_distance,
                                 "touch":None,"min_bid":bid,"max_bid":bid}
                current["short"]={"stop":bid+stop_distance,"target":bid-target_distance,
                                  "touch":None,"max_ask":ask,"min_ask":ask}
            for side,name in ((1,"long"),(-1,"short")):
                rec=current[name]
                rec["min_bid"]=min(rec.get("min_bid",bid),bid)
                rec["max_bid"]=max(rec.get("max_bid",bid),bid)
                rec["min_ask"]=min(rec.get("min_ask",ask),ask)
                rec["max_ask"]=max(rec.get("max_ask",ask),ask)
                if rec["touch"] is None:
                    rec["touch"]=first_touch(side,bid,ask,rec["stop"],rec["target"])
    finalize(current)
    if not ticks:raise ValueError("empty market quote sample")
    return {"status":"TICK_SEQUENCE_PATH_AUDIT_NOT_STRATEGY_RETURN",
            "dataset":"pinned third-party Dukascopy-derived XAUUSD quote source",
            "first_quote_timestamp_utc":None,  # source caller records source manifest separately
            "last_quote_timestamp_utc":last_timestamp,
            "ticks":ticks,"m5_bars":candles,
            "hypothetical_sl_distance_price":stop_distance,
            "hypothetical_tp_distance_price":target_distance,
            "counts":dict(sorted(counts.items())),
            "interpretation":"Stop-first conservative M5 exit can disagree with actual chronological first-touch; no broker fills, spreads beyond quote stream, commissions or trading returns inferred."}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gz",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--stop-distance",type=float,default=2.0)
    p.add_argument("--target-distance",type=float,default=3.0)
    args=p.parse_args()
    result=audit_ticks(pathlib.Path(args.gz),args.stop_distance,args.target_distance)
    pathlib.Path(args.output).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
