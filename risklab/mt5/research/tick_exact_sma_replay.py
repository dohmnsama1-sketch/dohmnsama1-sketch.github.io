#!/usr/bin/env python3
"""Chronological XAUUSD SMA10/30 tick replay (research-only, NEVER a live EA).

Uses the first quote of a newly opened M5 bar to enter after a crossover
confirmed by the TWO previous completed bars, broker BID/ASK sides for exit,
first chronological stop/target touch, adverse slippage, a generic assumed
commission and strict rounded-down lot sizing. Does not model broker
liquidity, margin, swaps, market latency, rejection or Exness quotes.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import gzip
import json
import math
from collections import Counter
from pathlib import Path
from public_xauusd_ingest import HEADER,parse_tick_row,m5_bucket
from walkforward_bidask import (FAST,SLOW,ATR_PERIOD,SL_ATR,REWARD_RISK,
    MIN_LOT,LOT_STEP,CONTRACT_UNITS,RISK_FRACTION,MAX_SPREAD_PRICE,
    TICK_SIZE,ASSUMED_COMMISSION_USD_PER_LOT_ROUND_TURN,atr_wilder)


def actual_tick_exit(position:dict, bid:float, ask:float, slip:float):
    """Stop order gaps may worsen fill; target cannot get optimistic improvement."""
    side=position["side"]
    if side==1:
        if bid<=position["stop"]:
            return min(position["stop"],bid)-slip,"stop"
        if bid>=position["target"]:
            return position["target"]-slip,"target"
    elif side==-1:
        if ask>=position["stop"]:
            return max(position["stop"],ask)+slip,"stop"
        if ask<=position["target"]:
            return position["target"]+slip,"target"
    else:
        raise ValueError("invalid position side")
    return None


def crossover_from_closed_bars(bars:list[dict])->int:
    """bar i (current) is NEVER consulted when deciding its opening trade."""
    if len(bars)<SLOW+1:
        return 0
    closes=[b["bid_close"] for b in bars[-(SLOW+1):]]
    f_prior=sum(closes[-FAST-1:-1])/FAST
    s_prior=sum(closes[-SLOW-1:-1])/SLOW
    f_now=sum(closes[-FAST:])/FAST
    s_now=sum(closes[-SLOW:])/SLOW
    if f_prior<=s_prior and f_now>s_now:return 1
    if f_prior>=s_prior and f_now<s_now:return -1
    return 0


def replay_week(path:Path,initial_equity:float=10000.0,
                slippage:float=.15,commission_per_lot:float=ASSUMED_COMMISSION_USD_PER_LOT_ROUND_TURN)->dict:
    if initial_equity<=0 or slippage<0 or commission_per_lot<0:
        raise ValueError("invalid simulation risk/cost parameters")
    closed_bars=[]
    bar=None
    prior_tick_time=None
    position=None
    trades=[]
    rejected=Counter()
    equity=initial_equity
    equity_peak=equity
    max_true_tick_equity_dd=0.0
    daily_ref=equity
    day=None
    frozen=False
    ticks=0
    first=None
    last=None
    last_bid=last_ask=None

    def pnl_at(exit_price,p):
        return ((exit_price-p["entry"])*CONTRACT_UNITS*p["lots"]*p["side"]
                -commission_per_lot*p["lots"])

    with gzip.open(path,"rt",encoding="utf-8",newline="") as handle:
        reader=csv.reader(handle)
        if next(reader,None)!=HEADER:raise ValueError("unexpected source columns")
        for raw in reader:
            when,ask,bid=parse_tick_row(raw)
            if prior_tick_time is not None and when<prior_tick_time:
                raise ValueError("nonmonotonic actual tick times")
            prior_tick_time=when
            ticks+=1
            if first is None:first=when
            last=when
            last_bid=bid
            last_ask=ask
            current_day=when[:10]
            if current_day!=day:
                day=current_day
                daily_ref=equity
            new_bucket=m5_bucket(when)
            new_bar=(bar is None or new_bucket!=bar["time"])
            was_open_at_bar_start=bool(position)
            if new_bar:
                if bar is not None:
                    closed_bars.append(bar)
                    if new_bucket<=bar["time"]:
                        raise ValueError("bar time moved backwards")
                bar={"time":new_bucket,"bid_open":bid,"bid_high":bid,"bid_low":bid,
                     "bid_close":bid,"ask_open":ask,"ask_high":ask,"ask_low":ask,
                     "ask_close":ask,"ticks":0}
            bar["ticks"]+=1
            for label,price in (("bid",bid),("ask",ask)):
                bar[f"{label}_high"]=max(bar[f"{label}_high"],price)
                bar[f"{label}_low"]=min(bar[f"{label}_low"],price)
                bar[f"{label}_close"]=price

            mark=equity
            if position is not None:
                mark=equity+((bid if position["side"]==1 else ask)-position["entry"])*CONTRACT_UNITS*position["lots"]*position["side"]-commission_per_lot*position["lots"]
                equity_peak=max(equity_peak,mark)
                if equity_peak>0:
                    max_true_tick_equity_dd=max(max_true_tick_equity_dd,max(0,1-mark/equity_peak))
                fill=actual_tick_exit(position,bid,ask,slippage)
                if fill is not None:
                    exit_price,why=fill
                    pnl=pnl_at(exit_price,position)
                    equity+=pnl
                    trades.append({"entry":position["entry_time"],"exit":when,
                                   "side":position["side"],"lot":position["lots"],
                                   "pnl":round(pnl,6),"exit_reason":why})
                    position=None
                    equity_peak=max(equity_peak,equity)

            if mark<=daily_ref*(1-.02) or (equity_peak>0 and mark<=equity_peak*(1-.15)):
                frozen=True
                if position is not None:
                    # Supervised simulation of immediate adverse-market close.
                    # No guarantee broker could fill this in live conditions.
                    exit_price=bid-slippage if position["side"]==1 else ask+slippage
                    pnl=pnl_at(exit_price,position)
                    equity+=pnl
                    trades.append({"entry":position["entry_time"],"exit":when,
                                   "side":position["side"],"lot":position["lots"],
                                   "pnl":round(pnl,6),"exit_reason":"equity_guard_attempt"})
                    rejected["floating_equity_guard_close"]+=1
                    position=None
            # Do not open on a candle where a prior trade just closed. Signals
            # are consumed only from fully completed candles and at 1st tick.
            if not new_bar or was_open_at_bar_start or position or frozen:
                continue
            side=crossover_from_closed_bars(closed_bars)
            if side==0:continue
            rejected["crossover_signals"]+=1
            if len(closed_bars)<ATR_PERIOD+1:continue
            # M5 signal would be unsafe after a multi-bar market-data gap.
            if closed_bars:
                prev_time=dt.datetime.strptime(closed_bars[-1]["time"],"%Y-%m-%d %H:%M:%S")
                this_time=dt.datetime.strptime(new_bucket,"%Y-%m-%d %H:%M:%S")
                if (this_time-prev_time).total_seconds()>1800:
                    rejected["market_data_gap"]+=1
                    continue
            spread=ask-bid
            if spread>MAX_SPREAD_PRICE:
                rejected["spread_cap"]+=1
                continue
            # Uses all closed bars only; the live open M5 candle is excluded.
            bars_for_atr=[{**x,"time":dt.datetime.strptime(x["time"],"%Y-%m-%d %H:%M:%S")}
                           for x in closed_bars]
            a=atr_wilder(bars_for_atr)[-1]
            if a is None or a<=0:
                rejected["indicator_warmup"]+=1
                continue
            entry=(ask+slippage) if side==1 else (bid-slippage)
            distance=a*SL_ATR
            if side==1:
                stop=math.floor((entry-distance)/TICK_SIZE)*TICK_SIZE
                target=math.ceil((entry+distance*REWARD_RISK)/TICK_SIZE)*TICK_SIZE
            else:
                stop=math.ceil((entry+distance)/TICK_SIZE)*TICK_SIZE
                target=math.floor((entry-distance*REWARD_RISK)/TICK_SIZE)*TICK_SIZE
            risk_lot=(abs(entry-stop)+2*slippage)*CONTRACT_UNITS+commission_per_lot
            qty=round(math.floor((equity*RISK_FRACTION/risk_lot+1e-9)/LOT_STEP)*LOT_STEP,8)
            if qty<MIN_LOT:
                rejected["risk_reject_min_lot"]+=1
                continue
            position={"side":side,"entry":entry,"stop":stop,"target":target,
                      "lots":qty,"entry_time":when}
            rejected["entry_attempts"]+=1
            # The first quote itself may cross a stop when spread is unusually wide.
            fill=actual_tick_exit(position,bid,ask,slippage)
            if fill is not None:
                exit_price,why=fill
                pnl=pnl_at(exit_price,position)
                equity+=pnl
                trades.append({"entry":position["entry_time"],"exit":when,
                               "side":side,"lot":qty,"pnl":round(pnl,6),
                               "exit_reason":why})
                position=None
                equity_peak=max(equity_peak,equity)

    if ticks==0:raise ValueError("no actual tick observations")
    if position is not None:
        final_quote=last_bid if position["side"]==1 else last_ask
        exit_price=final_quote-slippage if position["side"]==1 else final_quote+slippage
        pnl=pnl_at(exit_price,position)
        equity+=pnl
        trades.append({"entry":position["entry_time"],"exit":last,
                       "side":position["side"],"lot":position["lots"],
                       "pnl":round(pnl,6),"exit_reason":"forced_data_end"})
        equity_peak=max(equity_peak,equity)

    gains=sum(max(0,t["pnl"]) for t in trades)
    losses=-sum(min(0,t["pnl"]) for t in trades)
    return {
        "status":"INDEPENDENT_TICK_REPLAY_NO_REAL_BROKER_FILLS",
        "trading_model":"SMA10/30 confirmed crossover, fixed SL 2 ATR, TP 1.5R",
        "first_tick_utc":first,"last_tick_utc":last,"ticks":ticks,
        "m5_bars":len(closed_bars)+int(bar is not None),
        "reference_initial_equity_usd":initial_equity,
        "final_equity_usd":round(equity,2),"net_profit_usd":round(equity-initial_equity,2),
        "closed_trades":len(trades),"win_rate":round(sum(t["pnl"]>0 for t in trades)/len(trades),4) if trades else None,
        "profit_factor":round(gains/losses,4) if losses else None,
        "tick_order_max_marked_equity_drawdown_fraction":round(max_true_tick_equity_dd,5),
        "assumed_adverse_slippage_usd_per_oz_per_side":slippage,
        "assumed_commission_usd_per_lot_round_turn":commission_per_lot,
        "rejections":dict(rejected),
        "most_recent_5_trades":trades[-5:],
        "limitations":"Historical public Dukascopy-derived quotes, not Exness broker fills. No margin, swap, order-book, latency, broker retcode, alternative session matching or live execution proof. Equity risk max drawdown from tick-quote marks, not broker account equity.",
        "real_money_release_permitted":False
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--gz",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--deposit",type=float,default=10000)
    a=p.parse_args()
    result=replay_week(Path(a.gz),initial_equity=a.deposit)
    Path(a.output).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("status","ticks","m5_bars","reference_initial_equity_usd","net_profit_usd","closed_trades","profit_factor","tick_order_max_marked_equity_drawdown_fraction","rejections")},indent=2))


if __name__=="__main__":
    main()
