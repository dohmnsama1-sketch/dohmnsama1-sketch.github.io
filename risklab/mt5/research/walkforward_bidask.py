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
import random
from collections import Counter
from pathlib import Path
from news_event_gate import event_embargo, load_events, UTC

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
DONCHIAN_LOOKBACK=36  # fixed, prespecified 3-hour M5 breakout window
BREAKOUT_BUFFER_ATR=0.10  # requires last CLOSED bar to clear range by 0.1 ATR
ASSUMED_COMMISSION_USD_PER_LOT_ROUND_TURN=7.0 # research cost shock; NOT verified Exness Standard fee

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
            if b["bid_open"]>b["ask_open"] or b["bid_high"]>b["ask_high"] or b["bid_low"]>b["ask_low"]:
                raise ValueError("crossed or inconsistent BID/ASK data")
            for s in ("bid","ask"):
                if not (b[s+"_low"]<=min(b[s+"_open"],b[s+"_close"])
                        <=max(b[s+"_open"],b[s+"_close"])<=b[s+"_high"]):
                    raise ValueError("invalid OHLC price range")
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

def weekly_resampling_stress(trades, bars, repetitions=2000, seed=20261124):
    """Deterministic exploratory whole-week P/L block bootstrap.

    Calendar-week blocks retain clustered trade results and weeks with ZERO
    trades. This assumes weeks are exchangeable, which is not generally true
    for gold market regimes. NOT a formally calibrated statistical CI, not a
    forecast, and not a substitute for genuinely new out-of-sample data.
    """
    if repetitions<100 or not bars:
        raise ValueError("invalid weekly stress bootstrap configuration")
    weekly={}
    for b in bars:
        iso=b["time"].isocalendar()
        weekly.setdefault((iso.year,iso.week),0.0)
    trades_per_week=set()
    for t in trades:
        when=dt.datetime.fromisoformat(t["exit"]).isocalendar()
        key=(when.year,when.week)
        if key not in weekly:
            raise ValueError("trade exit outside documented market data")
        weekly[key]+=t["pnl"]
        trades_per_week.add(key)
    values=list(weekly.values())
    n=len(values)
    output={"bootstrap_week_count":n,
            "bootstrap_weeks_with_trades":len(trades_per_week),
            "bootstrap_repetitions":repetitions,
            "bootstrap_seed":seed,
            "bootstrap_interpretation":"exploratory resampling of exit-attributed weekly P/L; not a calibrated confidence interval or future profit forecast"}
    if n<26:
        return {**output,"bootstrap_status":"INSUFFICIENT_WEEKS",
                "bootstrap_net_pnl_p2p5":None,
                "bootstrap_net_pnl_p97p5":None,
                "bootstrap_positive_fraction":None}
    rng=random.Random(seed)
    totals=[]
    for _ in range(repetitions):
        totals.append(sum(values[rng.randrange(n)] for _ in range(n)))
    totals.sort()
    return {**output,"bootstrap_status":"EXPLORATORY",
            "bootstrap_net_pnl_p2p5":round(totals[int(0.025*repetitions)],2),
            "bootstrap_net_pnl_p97p5":round(totals[min(repetitions-1,math.ceil(0.975*repetitions)-1)],2),
            "bootstrap_positive_fraction":round(sum(v>0 for v in totals)/repetitions,4)}


def partition_closed_trades(trades, boundary_1, boundary_2):
    """Exclude positions crossing a research/validation/holdout boundary.

    Entry-period attribution alone leaks a future outcome into the older
    segment if its exit occurred in a later segment. Such trades remain
    in TOTAL account P/L but cannot support per-split profitability.
    """
    def segment(t):
        if t < boundary_1:
            return "analysis"
        return "validation" if t < boundary_2 else "holdout"

    buckets = {"analysis": [], "validation": [], "holdout": []}
    contaminated = []
    for trade in trades:
        start = dt.datetime.fromisoformat(trade["entry"])
        finish = dt.datetime.fromisoformat(trade["exit"])
        if finish < start:
            raise ValueError("trade exit precedes trade entry")
        first, last = segment(start), segment(finish)
        if first != last:
            contaminated.append(trade)
        else:
            buckets[first].append(trade["pnl"])
    return buckets, contaminated


def conservative_exit_fill(side, stop, target, bar, slippage):
    """Return (executable exit quote, stop_hit) or None.

    Broker-side stop orders can gap through their intended price.
    Take-profit orders are credited at the limit price, *not* with a
    favorable price improvement inferred from a 5-minute bar open.
    Ambiguous intrabar path always chooses the stop (pessimistic).
    """
    if side not in (-1, 1) or slippage < 0:
        raise ValueError("invalid side or slippage")
    if side == 1:
        if bar["bid_low"] <= stop:
            return min(stop, bar["bid_open"]) - slippage, True
        if bar["bid_high"] >= target:
            return target - slippage, False
    else:
        if bar["ask_high"] >= stop:
            return max(stop, bar["ask_open"]) + slippage, True
        if bar["ask_low"] <= target:
            return target + slippage, False
    return None

def adverse_ohlc_equity_proxy(realized_equity, position, bar, slippage,
                              commission_round_turn=ASSUMED_COMMISSION_USD_PER_LOT_ROUND_TURN):
    """Stress estimate of intrabar open equity at the worst M5 BID/ASK extreme.

    Not tick-accurate and NOT a true time-ordered floating-equity series.
    The low/high may occur before entry or after exit in this same bar.
    This deliberately pessimistic diagnostic exposes risk hidden by reports
    that only compute drawdown from closed trade balances.
    """
    if slippage<0 or commission_round_turn<0 or position["lots"]<=0:
        raise ValueError("invalid adverse valuation inputs")
    side=position["side"]
    if side not in (-1,1):
        raise ValueError("invalid position side")
    adverse_quote=(bar["bid_low"]-slippage if side==1
                   else bar["ask_high"]+slippage)
    unrealized=(adverse_quote-position["entry"])*CONTRACT_UNITS*position["lots"]*side
    unrealized-=commission_round_turn*position["lots"]
    return realized_equity+unrealized,unrealized

def closed_bar_breakout_signal(bars,i,atr):
    """Fire only on a *new* confirmed Donchian break, not every bar outside.

    At the open of candle i, only candles up through i-1 are available.
    A prior break confirmed on i-2 is an already-consumed signal.
    Both current and prior ranges EXCLUDE their confirming candles.
    """
    if i<DONCHIAN_LOOKBACK+3 or atr[i-1] is None or atr[i-2] is None:
        return 0
    recent=bars[i-1]
    previous=bars[i-2]
    history=bars[i-DONCHIAN_LOOKBACK-1:i-1]
    prev_history=bars[i-DONCHIAN_LOOKBACK-2:i-2]
    high=max(x["bid_high"] for x in history)
    low=min(x["bid_low"] for x in history)
    previous_high=max(x["bid_high"] for x in prev_history)
    previous_low=min(x["bid_low"] for x in prev_history)
    threshold=BREAKOUT_BUFFER_ATR*atr[i-1]
    prev_threshold=BREAKOUT_BUFFER_ATR*atr[i-2]
    buy=recent["bid_close"]>high+threshold
    sell=recent["bid_close"]<low-threshold
    if buy and previous["bid_close"]<=previous_high+prev_threshold:
        return 1
    if sell and previous["bid_close"]>=previous_low-prev_threshold:
        return -1
    return 0

def evaluate(bars,mode="baseline",slippage=0.15,initial_equity=10000,commission_per_lot_round_turn=ASSUMED_COMMISSION_USD_PER_LOT_ROUND_TURN,news_events=None):
    if mode not in ("baseline","regime","breakout"): raise ValueError("invalid strategy")
    if slippage<0 or initial_equity<=0 or commission_per_lot_round_turn<0: raise ValueError("invalid cost/capital")
    if news_events is not None and not news_events: raise ValueError("news-aware replay requires a verified nonempty event feed")
    atr=atr_wilder(bars)
    adx,plus,minus=directional_wilder(bars) if mode=="regime" else (None,None,None)
    h1=h1_closed_ema(bars) if mode in ("regime","breakout") else None
    closes=[b["bid_close"] for b in bars]
    equity=initial_equity
    peak=equity
    max_dd=0
    max_adverse_intrabar_dd=0.0
    max_open_position_adverse_loss=0.0
    bars_with_open_position=0
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
            bars_with_open_position+=1
            marked_equity,unrealized=adverse_ohlc_equity_proxy(
                equity,pos,b,slippage,commission_per_lot_round_turn)
            max_open_position_adverse_loss=max(max_open_position_adverse_loss,-unrealized)
            if peak>0:
                max_adverse_intrabar_dd=max(
                    max_adverse_intrabar_dd,max(0.0,1.0-marked_equity/peak))
            fill=conservative_exit_fill(pos["side"],pos["stop"],pos["target"],b,slippage)
            if fill is not None:
                exit_quote,stop_hit=fill
                pnl=(exit_quote-pos["entry"])*CONTRACT_UNITS*pos["lots"]*pos["side"]-commission_per_lot_round_turn*pos["lots"]
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
        if mode=="breakout":
            side=closed_bar_breakout_signal(bars,i,atr)
        else:
            f0=sma(closes,i-1,FAST)
            f1=sma(closes,i,FAST)
            s0=sma(closes,i-1,SLOW)
            s1=sma(closes,i,SLOW)
            side=(1 if f0<=s0 and f1>s1 else
                 -1 if f0>=s0 and f1<s1 else 0)
        if not side: continue
        rejected["breakout_signals" if mode=="breakout" else "crossover_signals"]+=1
        if news_events is not None and event_embargo(b["time"].replace(tzinfo=UTC),news_events):
            rejected["point_in_time_news_embargo"]+=1
            continue
        if i>0 and (b["time"]-bars[i-1]["time"]).total_seconds()>1800:
            rejected["gap_first_bar"]+=1
            continue
        spread=b["ask_open"]-b["bid_open"]
        if spread>MAX_SPREAD_PRICE:
            rejected["spread_cap"]+=1
            continue
        if mode in ("regime","breakout"):
            h=h1[i]
            if h is None:
                rejected["h1_warmup"]+=1
                continue
            higher_close,higher_ema=h
            if (side==1 and higher_close<=higher_ema) or (side==-1 and higher_close>=higher_ema):
                rejected["h1_trend"]+=1
                continue
            if mode=="regime":
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
        loss_per_lot=(abs(entry-stop)+2*slippage)*CONTRACT_UNITS+commission_per_lot_round_turn
        lots=math.floor((equity*RISK_FRACTION/loss_per_lot+1e-9)/LOT_STEP)*LOT_STEP
        lots=round(lots,8)
        if lots<MIN_LOT:
            rejected["min_lot"]+=1
            continue
        position={"time":b["time"].isoformat(),"side":side,"entry":entry,
                  "stop":stop,"target":target,"lots":lots}
        # Same-bar OHLC ordering is unknown; include pessimistic adverse mark
        # even if the low/high was before the order. Not an actual observed DD.
        bars_with_open_position+=1
        marked_equity,unrealized=adverse_ohlc_equity_proxy(
            equity,position,b,slippage,commission_per_lot_round_turn)
        max_open_position_adverse_loss=max(max_open_position_adverse_loss,-unrealized)
        if peak>0:
            max_adverse_intrabar_dd=max(
                max_adverse_intrabar_dd,max(0.0,1.0-marked_equity/peak))
        rejected["entry_attempts"]+=1
        # Entry at first quote of bar i; OHLC exit path remains pessimistic.
        fill=conservative_exit_fill(side,stop,target,b,slippage)
        if fill is not None:
            exit_quote,stop_hit=fill
            pnl=(exit_quote-entry)*CONTRACT_UNITS*lots*side-commission_per_lot_round_turn*lots
            equity+=pnl
            trades.append({"entry":position["time"],"exit":b["time"].isoformat(),
                           "side":side,"lots":lots,"pnl":round(pnl,6),"stop_first":bool(stop_hit)})
            position=None
            peak=max(peak,equity)
            max_dd=max(max_dd,1-equity/peak)
    if position:
        b=bars[-1]
        exit_quote=b["bid_close"]-slippage if position["side"]==1 else b["ask_close"]+slippage
        pnl=(exit_quote-position["entry"])*CONTRACT_UNITS*position["lots"]*position["side"]-commission_per_lot_round_turn*position["lots"]
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
    split, boundary_crossers = partition_closed_trades(trades,i1,i2)
    # Calendar-month attribution uses EXIT timestamps only (realized P/L).
    # A trade crossing a month boundary is reported in its EXIT month.
    months={}
    for bar in bars:
        months.setdefault(bar["time"].strftime("%Y-%m"),{"trades":0,"net_pnl":0.0})
    for trade in trades:
        key=dt.datetime.fromisoformat(trade["exit"]).strftime("%Y-%m")
        months[key]["trades"]+=1
        months[key]["net_pnl"]+=trade["pnl"]
    monthly=[{"month":key,"trades":val["trades"],
              "net_pnl":round(val["net_pnl"],2)} for key,val in sorted(months.items())]
    active_months=sum(item["trades"]>0 for item in monthly)
    positive_months=sum(item["trades"]>0 and item["net_pnl"]>0 for item in monthly)
    losing_months=sum(item["trades"]>0 and item["net_pnl"]<0 for item in monthly)
    weekly_stress=weekly_resampling_stress(trades,bars)
    return {
        **weekly_stress,
        "mode":mode,"slippage_usd_per_oz_per_side":slippage,
        "news_event_mode":"archived_events_point_in_time" if news_events is not None else "not_enabled",
        "assumed_commission_usd_per_lot_round_turn":commission_per_lot_round_turn,
        "source":"independent public Dukascopy-derived M5 bid/ask aggregation, not broker fills",
        "approximation":"M5 candle stop/target path ambiguous; stop-first, not tick-exact; no margin/swap modelling; commission is a generic research assumption, not a verified Exness Standard account fee; adverse intrabar equity proxy uses full candle extremes without tick order and is NOT a true observed floating-equity drawdown",
        "initial_equity":initial_equity,
        "ending_equity":round(equity,2),
        "net_pnl":round(equity-initial_equity,2),
        "number_of_closed_trades":len(trades),
        "win_rate":round(wins/len(trades),4) if trades else None,
        "win_rate_wilson_95_interval":wilson_interval(wins,len(trades)),
        "profit_factor":round(profits/losses,4) if losses else None,
        "max_closed_equity_drawdown_fraction":round(max_dd,5),
        "max_adverse_intrabar_equity_proxy_fraction":round(max_adverse_intrabar_dd,5),
        "max_open_position_adverse_loss_proxy_usd":round(max_open_position_adverse_loss,2),
        "bars_with_open_position":bars_with_open_position,
        "gross_profit":round(profits,2),"gross_loss":round(losses,2),
        "rejections":dict(rejected),
        "split_60_20_20":[{"name":name,"start_boundary":(None if name=="analysis" else
             i1.isoformat() if name=="validation" else i2.isoformat()),
             "trades":len(values),"net_pnl":round(sum(values),2)} for name,values in split.items()],
        "calendar_month_performance_exit_attributed":monthly,
        "months_with_data":len(monthly),
        "months_with_trades":active_months,
        "positive_months_with_trades":positive_months,
        "negative_months_with_trades":losing_months,
        "positive_month_share_active":round(positive_months/active_months,4) if active_months else None,
        "largest_trade_loss_usd":round(min([0]+[t["pnl"] for t in trades]),2),
        "boundary_crossing_trades":len(boundary_crossers),
        "cross_partition_pnl_excluded_from_split":round(sum(t["pnl"] for t in boundary_crossers),2),
        "min_sample_reached":len(trades)>=100,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--m5",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--news-events-csv",default=None,
                   help="Optional independently sourced ISO-UTC point-in-time event CSV; otherwise NO news embargo")
    a=p.parse_args()
    bars=read_bars(Path(a.m5))
    news_events=load_events(Path(a.news_events_csv)) if a.news_events_csv else None
    results=[]
    for mode in ("baseline","regime","breakout"):
        for slip in (0.00,0.15,0.50):
            results.append(evaluate(bars,mode,slip,news_events=news_events))
        # Actual owner target capital is 50 USD. Refuse to round up to an
        # unsafe broker minimum lot merely to force a trade.
        results.append(evaluate(bars,mode,0.15,initial_equity=50,news_events=news_events))
    data={"status":"exploratory_not_MT5_or_Exness_verified",
          "point_in_time_news_filter":"enabled_from_supplied_file" if news_events is not None else "NOT_ENABLED_no_event_feed",
          "news_event_count":len(news_events) if news_events is not None else 0,
          "real_money_release_permitted":False,
          "real_money_blockers":["external feed is not Exness fills",
             "historical 5-minute OHLC cannot reconstruct intrabar tick order",
             "no verified broker margin/swap/fill model",
             "must demonstrate positive independent forward-test and risk feasibility"],
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
