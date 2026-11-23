#!/usr/bin/env python3
"""Conservative independent BID/ASK M5 research benchmark for ZALAH.

This is NOT MT5 strategy-tester equivalence or a live-trading bot.
Independent 5-minute quotes lose tick sequence. If SL and TP occur within
a single candle, the stop is chosen first. Entry uses the NEXT bar's quote.
The historical source is NOT Exness and margin/swaps are not modelled.
All parameters fixed *before* inspecting holdout performance.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import json
import math
import statistics
from collections import Counter
from pathlib import Path

FAST=10
SLOW=30
ATR_PERIOD=14
ADX_PERIOD=14
H1_EMA_PERIOD=100
SL_ATR=2.0
REWARD_RISK=1.5
RISK_FRACTION=0.005
MAX_SPREAD_PRICE=0.50
MAX_SPREAD_ATR=0.20
MIN_ADX=20.0
CONTRACT_UNITS=100.0
MIN_LOT=0.01
LOT_STEP=0.01
MAX_EQUITY_DRAWDOWN=0.15
MAX_DAILY_LOSS=0.02
TICK_SIZE=0.01

def read_bars(path: Path):
    required=["time","bid_open","bid_high","bid_low","bid_close",
              "ask_open","ask_high","ask_low","ask_close","ticks"]
    bars=[]
    with path.open(newline="",encoding="utf-8") as handle:
        reader=csv.DictReader(handle)
        if not set(required).issubset(reader.fieldnames or []):
            raise ValueError("missing required BID/ASK M5 columns")
        last=None
        for row in reader:
            time=dt.datetime.strptime(row["time"],"%Y-%m-%d %H:%M:%S")
            if time.minute%5!=0 or time.second!=0 or (last is not None and time<=last):
                raise ValueError("M5 timestamps not strictly increasing/aligned")
            last=time
            b={"time":time}
            for field in required[1:-1]:
                b[field]=float(row[field])
                if not math.isfinite(b[field]) or b[field]<=0:
                    raise ValueError("non-positive or non-finite quote")
            b["ticks"]=int(row["ticks"])
            if b["ticks"]<=0: raise ValueError("empty M5 quote interval")
            for s in ("bid","ask"):
                if not (b[s+"_low"]<=min(b[s+"_open"],b[s+"_close"])
                        <=max(b[s+"_open"],b[s+"_close"])<=b[s+"_high"]):
                    raise ValueError("invalid OHLC price range")
            if b["bid_open"]>b["ask_open"] or b["bid_high"]>b["ask_high"] or b["bid_low"]>b["ask_low"]:
                raise ValueError("crossed or inconsistent BID/ASK data")
            bars.append(b)
    if not bars: raise ValueError("empty series")
    return bars

def atr_wilder(bars, period=ATR_PERIOD):
    out=[None]*len(bars)
    tr=[0.0]*len(bars)
    for i in range(1,len(bars)):
        b,p=bars[i],bars[i-1]
        tr[i]=max(b["bid_high"]-b["bid_low"],
                  abs(b["bid_high"]-p["bid_close"]),
                  abs(b["bid_low"]-p["bid_close"]))
        if i==period:
            out[i]=sum(tr[1:i+1])/period
        elif i>period:
            out[i]=(out[i-1]*(period-1)+tr[i])/period
    return out

def directional_wilder(bars, period=ADX_PERIOD):
    count=len(bars)
    dx=[None]*count
    adx=[None]*count
    plus=[None]*count
    minus=[None]*count
    tr_dm=[]
    for i in range(1,count):
        b,p=bars[i],bars[i-1]
        up=b["bid_high"]-p["bid_high"]
        down=p["bid_low"]-b["bid_low"]
        dmplus=up if up>down and up>0 else 0.0
        dmminus=down if down>up and down>0 else 0.0
        tr=max(b["bid_high"]-b["bid_low"],
               abs(b["bid_high"]-p["bid_close"]),
               abs(b["bid_low"]-p["bid_close"]))
        tr_dm.append((tr,dmplus,dmminus))
        if i<period: continue
        if i==period:
            t,pd,md=[sum(x[k] for x in tr_dm[:period]) for k in (0,1,2)]
        else:
            t=t-t/period+tr
            pd=pd-pd/period+dmplus
            md=md-md/period+dmminus
        plus[i]=100*pd/t if t else 0
        minus[i]=100*md/t if t else 0
        denom=plus[i]+minus[i]
        dx[i]=100*abs(plus[i]-minus[i])/denom if denom else 0.0
        if i==2*period-1:
            adx[i]=sum(x for x in dx[period:i+1] if x is not None)/period
        elif i>2*period-1:
            adx[i]=(adx[i-1]*(period-1)+dx[i])/period
    return adx,plus,minus

def h1_closed_ema(bars, period=H1_EMA_PERIOD):
    """For each bar i, H1 signal only from PREVIOUS completed hour."""
    out=[None]*len(bars)
    last_hour=None
    hour_close=None
    completed=0
    recent=[]
    ema=None
    closed_close=None
    smooth=2/(period+1)
    for i,b in enumerate(bars):
        hour=b["time"].replace(minute=0,second=0)
        if last_hour is not None and hour!=last_hour:
            completed+=1
            recent.append(hour_close)
            if completed==period:
                ema=sum(recent[-period:])/period
            elif completed>period:
                ema=hour_close*smooth+ema*(1-smooth)
            closed_close=hour_close
        out[i]=(closed_close,ema) if ema is not None else None
        last_hour=hour
        hour_close=b["bid_close"]
    return out

def sma(values,i,period):
    # Close of bar i-1 is most recent information at bar i open.
    if i<period: return None
    return sum(values[i-period:i])/period

def wilson_interval(wins,total,z=1.96):
    if not total: return None
    p=wins/total
    d=1+z*z/total
    mid=(p+z*z/(2*total))/d
    half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
    return [round(max(0,mid-half),4),round(min(1,mid+half),4)]

def evaluate(bars,mode="baseline",slippage=0.15,initial_equity=10000):
    if mode not in ("baseline","regime"): raise ValueError("invalid strategy")
    if slippage<0 or initial_equity<=0: raise ValueError("invalid cost/capital")
    atr=atr_wilder(bars)
    adx,plus,minus=directional_wilder(bars) if mode=="regime" else (None,None,None)
    h1=h1_closed_ema(bars) if mode=="regime" else None
    closes=[b["bid_close"] for b in bars]
    equity=initial_equity
    peak=equity
    max_dd=0
    locked=False
    day=None
    daystart=equity
    position=None
    trades=[]
    rejected=Counter()
    for i,b in enumerate(bars):
        current_day=b["time"].date()
        if current_day!=day:
            day=current_day
            daystart=equity
        held_at_open=(position is not None)
        if position is not None:
            pos=position
            if pos["side"]==1:
                stop_hit=b["bid_low"]<=pos["stop"]
                target_hit=b["bid_high"]>=pos["target"]
                price=min(pos["stop"],b["bid_open"]) if stop_hit else pos["target"]
                if target_hit and not stop_hit: price=max(pos["target"],b["bid_open"])
                exit_quote=price-slippage
            else:
                stop_hit=b["ask_high"]>=pos["stop"]
                target_hit=b["ask_low"]<=pos["target"]
                price=max(pos["stop"],b["ask_open"]) if stop_hit else pos["target"]
                if target_hit and not stop_hit: price=min(pos["target"],b["ask_open"])
                exit_quote=price+slippage
            if stop_hit or target_hit:
                pnl=(exit_quote-pos["entry"])*CONTRACT_UNITS*pos["lots"]*pos["side"]
                equity+=pnl
                trades.append({"entry":pos["time"],"exit":b["time"].isoformat(),
                               "side":pos["side"],"lots":pos["lots"],"pnl":round(pnl,6),
                               "stop_first":bool(stop_hit)})
                position=None
                peak=max(peak,equity)
                max_dd=max(max_dd,1-equity/peak)
        # A position open at the start of this M5 candle cannot be re-entered
        # at the start after an intrabar stop: no intrabar timeline lookahead.
        if held_at_open: continue
        if locked or equity<=daystart*(1-MAX_DAILY_LOSS) or equity<=peak*(1-MAX_EQUITY_DRAWDOWN):
            locked=True
            rejected["kill_switch"]+=1
            continue
        if atr[i-1] is None if i>0 else True: continue
        if i<max(FAST,SLOW)+2: continue
        f0=sma(closes,i-1,FAST)
        f1=sma(closes,i,FAST)
        s0=sma(closes,i-1,SLOW)
        s1=sma(closes,i,SLOW)
        side=(1 if f0<=s0 and f1>s1 else
             -1 if f0>=s0 and f1<s1 else 0)
        if not side: continue
        rejected["crossover_signals"]+=1
        if i>0 and (b["time"]-bars[i-1]["time"]).total_seconds()>1800:
            rejected["gap_first_bar"]+=1
            continue
        spread=b["ask_open"]-b["bid_open"]
        if spread>MAX_SPREAD_PRICE:
            rejected["spread_cap"]+=1
            continue
        if mode=="regime":
            h=h1[i]
            if h is None:
                rejected["h1_warmup"]+=1
                continue
            higher_close,higher_ema=h
            if (side==1 and higher_close<=higher_ema) or (side==-1 and higher_close>=higher_ema):
                rejected["h1_trend"]+=1
                continue
            if adx[i-1] is None:
                rejected["adx_warmup"]+=1
                continue
            if adx[i-1]<MIN_ADX or (side==1 and plus[i-1]<=minus[i-1]) or (side==-1 and minus[i-1]<=plus[i-1]):
                rejected["adx_direction"]+=1
                continue
            if spread/atr[i-1]>MAX_SPREAD_ATR:
                rejected["cost_to_atr"]+=1
                continue
        risk_distance=atr[i-1]*SL_ATR
        if risk_distance<=0: continue
        entry=(b["ask_open"]+slippage) if side==1 else (b["bid_open"]-slippage)
        stop=(math.floor((entry-risk_distance)/TICK_SIZE)*TICK_SIZE if side==1 else
              math.ceil((entry+risk_distance)/TICK_SIZE)*TICK_SIZE)
        target=(math.ceil((entry+risk_distance*REWARD_RISK)/TICK_SIZE)*TICK_SIZE if side==1 else
                math.floor((entry-risk_distance*REWARD_RISK)/TICK_SIZE)*TICK_SIZE)
        # Realized loss can exceed budget on price gaps/illiquidity. This
        # estimate adds two adverse slippage allowances per lot.
        loss_per_lot=(abs(entry-stop)+2*slippage)*CONTRACT_UNITS
        lots=math.floor((equity*RISK_FRACTION/loss_per_lot+1e-9)/LOT_STEP)*LOT_STEP
        lots=round(lots,8)
        if lots<MIN_LOT:
            rejected["min_lot"]+=1
            continue
        position={"time":b["time"].isoformat(),"side":side,"entry":entry,
                  "stop":stop,"target":target,"lots":lots}
        rejected["entry_attempts"]+=1
        # Entry is at first quote of bar i; conservative intrabar stop check.
        if side==1:
            stop_hit=b["bid_low"]<=stop
            target_hit=b["bid_high"]>=target
            if stop_hit or target_hit:
                price=min(stop,b["bid_open"]) if stop_hit else max(target,b["bid_open"])
                pnl=(price-slippage-entry)*CONTRACT_UNITS*lots
        else:
            stop_hit=b["ask_high"]>=stop
            target_hit=b["ask_low"]<=target
            if stop_hit or target_hit:
                price=max(stop,b["ask_open"]) if stop_hit else min(target,b["ask_open"])
                pnl=(entry-(price+slippage))*CONTRACT_UNITS*lots
        if stop_hit or target_hit:
            equity+=pnl
            trades.append({"entry":position["time"],"exit":b["time"].isoformat(),
                           "side":side,"lots":lots,"pnl":round(pnl,6),"stop_first":bool(stop_hit)})
            position=None
            peak=max(peak,equity)
            max_dd=max(max_dd,1-equity/peak)
    if position:
        b=bars[-1]
        exit_quote=b["bid_close"]-slippage if position["side"]==1 else b["ask_close"]+slippage
        pnl=(exit_quote-position["entry"])*CONTRACT_UNITS*position["lots"]*position["side"]
        equity+=pnl
        trades.append({"entry":position["time"],"exit":b["time"].isoformat(),
                       "side":position["side"],"lots":position["lots"],"pnl":round(pnl,6),
                       "stop_first":False,"forced_end_of_data":True})
        peak=max(peak,equity)
        max_dd=max(max_dd,1-equity/peak)
    wins=sum(t["pnl"]>0 for t in trades)
    profits=sum(max(0,t["pnl"]) for t in trades)
    losses=-sum(min(0,t["pnl"]) for t in trades)
    years=["2026"] # report uses chronological segments, never fitted to price outcomes
    i1=bars[len(bars)*3//5]["time"]
    i2=bars[len(bars)*4//5]["time"]
    split={"analysis":[],"validation":[],"holdout":[]}
    for t in trades:
        stamp=dt.datetime.fromisoformat(t["entry"])
        name="analysis" if stamp<i1 else "validation" if stamp<i2 else "holdout"
        split[name].append(t["pnl"])
    return {
        "mode":mode,"slippage_usd_per_oz_per_side":slippage,
        "source":"independent public Dukascopy-derived M5 bid/ask aggregation, not broker fills",
        "approximation":"M5 candle stop/target path ambiguous; stop-first, not tick-exact; no margin/swap modelling",
        "initial_equity":initial_equity,
        "ending_equity":round(equity,2),
        "net_pnl":round(equity-initial_equity,2),
        "number_of_closed_trades":len(trades),
        "win_rate":round(wins/len(trades),4) if trades else None,
        "win_rate_wilson_95_interval":wilson_interval(wins,len(trades)),
        "profit_factor":round(profits/losses,4) if losses else None,
        "max_closed_equity_drawdown_fraction":round(max_dd,5),
        "gross_profit":round(profits,2),"gross_loss":round(losses,2),
        "rejections":dict(rejected),
        "split_60_20_20":[{"name":name,"start_boundary":(None if name=="analysis" else
             i1.isoformat() if name=="validation" else i2.isoformat()),
             "trades":len(values),"net_pnl":round(sum(values),2)} for name,values in split.items()],
        "min_sample_reached":len(trades)>=100,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--m5",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    bars=read_bars(Path(a.m5))
    results=[]
    for mode in ("baseline","regime"):
        for slip in (0.00,0.15,0.50):
            results.append(evaluate(bars,mode,slip))
    data={"status":"exploratory_not_MT5_or_Exness_verified",
          "m5_bars":len(bars),
          "first":bars[0]["time"].isoformat(),
          "last":bars[-1]["time"].isoformat(),
          "results":results}
    Path(a.output).write_text(json.dumps(data,indent=2),encoding="utf-8")
    for r in results:
        print(f"{r['mode']} slippage={r['slippage_usd_per_oz_per_side']:.2f} "
              f"trades={r['number_of_closed_trades']} net={r['net_pnl']:.2f} "
              f"PF={r['profit_factor']} min100={r['min_sample_reached']}")

if __name__=="__main__":
    main()
