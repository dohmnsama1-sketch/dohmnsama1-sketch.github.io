#!/usr/bin/env python3
"""Zero-network tests for the independent quote-based research engine."""
import csv
import datetime as dt
import importlib.util
import math
import pathlib
import tempfile
import unittest

HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("zalah_wf",HERE/"walkforward_bidask.py")
wf=importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)

def synthetic(count=360,spread=.25):
    first=dt.datetime(2026,1,2,0,0)
    bars=[]
    for i in range(count):
        level=4400.0+10.0*math.sin(i/12.0)+0.03*i
        o=level
        c=level+0.6*math.sin(i/3)
        lo=min(o,c)-1.0
        hi=max(o,c)+1.0
        bars.append({"time":first+dt.timedelta(minutes=5*i),
                     "bid_open":o,"bid_high":hi,"bid_low":lo,"bid_close":c,
                     "ask_open":o+spread,"ask_high":hi+spread,
                     "ask_low":lo+spread,"ask_close":c+spread,"ticks":4})
    return bars

class ResearchTests(unittest.TestCase):
    def test_all_models_parse_and_return_metrics(self):
        bars=synthetic()
        for mode in ("baseline","regime","breakout"):
            for slip in (0.0,.15,.5):
                with self.subTest(mode=mode,slip=slip):
                    r=wf.evaluate(bars,mode,slip)
                    self.assertGreater(r["ending_equity"],0)
                    self.assertEqual(len(r["split_60_20_20"]),3)
                    self.assertEqual(r["number_of_closed_trades"],
                                     sum(x["trades"] for x in r["split_60_20_20"])
                                     +r["boundary_crossing_trades"])
                    self.assertLessEqual(r["max_closed_equity_drawdown_fraction"],1.0)

    def test_insufficient_sample_is_not_proven_profitability(self):
        r=wf.evaluate(synthetic(65),"regime")
        self.assertEqual(r["number_of_closed_trades"],0)
        self.assertFalse(r["min_sample_reached"])
        self.assertIsNone(r["win_rate"])

    def test_wilson_bounds_and_no_guess_with_zero_trades(self):
        self.assertEqual(wf.wilson_interval(0,0),None)
        self.assertEqual(wf.wilson_interval(10,10)[1],1.0)
        interval=wf.wilson_interval(8,25)
        self.assertTrue(0<=interval[0]<8/25<interval[1]<=1)

    def test_breakout_signal_does_not_read_future_or_forming_candle(self):
        bars=synthetic(90)
        atr=wf.atr_wilder(bars)
        i=wf.DONCHIAN_LOOKBACK+8
        before=wf.closed_bar_breakout_signal(bars,i,atr)
        altered=[dict(b) for b in bars]
        for k in ("bid_open","bid_high","bid_low","bid_close"):
            altered[i][k]*=1.35
        after=wf.closed_bar_breakout_signal(altered,i,atr)
        self.assertEqual(before,after)

    def test_breakout_requires_confirmed_prior_close_above_history(self):
        bars=synthetic(90)
        atr=wf.atr_wilder(bars)
        i=wf.DONCHIAN_LOOKBACK+8
        altered=[dict(b) for b in bars]
        window=altered[i-wf.DONCHIAN_LOOKBACK-1:i-1]
        prior=max(x["bid_high"] for x in window)
        altered[i-1]["bid_close"]=prior+2+0.1*atr[i-1]
        self.assertEqual(wf.closed_bar_breakout_signal(altered,i,atr),1)

    def test_breakout_is_one_shot_until_price_returns_inside(self):
        bars=synthetic(100)
        for j in range(100):
            bars[j].update({"bid_open":100.0,"bid_high":101.0,
                            "bid_low":99.0,"bid_close":100.0,
                            "ask_open":100.2,"ask_high":101.2,
                            "ask_low":99.2,"ask_close":100.2})
        for idx,level in [(43,105.0),(44,107.0)]:
            bars[idx]["bid_close"]=level
            bars[idx]["bid_high"]=level+0.2
            bars[idx]["ask_close"]=level+0.2
            bars[idx]["ask_high"]=level+0.4
        atr=wf.atr_wilder(bars)
        self.assertEqual(wf.closed_bar_breakout_signal(bars,44,atr),1)
        self.assertEqual(wf.closed_bar_breakout_signal(bars,45,atr),0)

    def test_commission_research_cost_is_nonnegative_and_explicit(self):
        bars=synthetic(360)
        with self.assertRaisesRegex(ValueError,"invalid cost"):
            wf.evaluate(bars,"baseline",commission_per_lot_round_turn=-1)
        r=wf.evaluate(bars,"baseline",commission_per_lot_round_turn=7.0)
        self.assertEqual(r["assumed_commission_usd_per_lot_round_turn"],7.0)
        self.assertIn("generic research assumption",r["approximation"])

    def test_calendar_months_include_no_trade_months_and_reconcile_realized_pl(self):
        bars=synthetic(900) # crosses Jan and Feb, with no assumption of daily trading
        r=wf.evaluate(bars,"regime",0.15)
        months=r["calendar_month_performance_exit_attributed"]
        self.assertEqual(r["months_with_data"],len(months))
        self.assertEqual(r["months_with_trades"],sum(x["trades"]>0 for x in months))
        self.assertEqual(r["number_of_closed_trades"],sum(x["trades"] for x in months))
        self.assertAlmostEqual(r["net_pnl"],sum(x["net_pnl"] for x in months),places=2)
        self.assertEqual(r["positive_month_share_active"] is None, r["months_with_trades"]==0)
        self.assertLessEqual(r["positive_months_with_trades"],r["months_with_trades"])

    def test_no_unbounded_or_negative_slippage(self):
        with self.assertRaises(ValueError):
            wf.evaluate(synthetic(),"baseline",-.1)

    def test_import_bidask_csv(self):
        rows=synthetic(4)
        with tempfile.TemporaryDirectory() as temp:
            p=pathlib.Path(temp)/"test.csv"
            fields=["time","bid_open","bid_high","bid_low","bid_close",
                    "ask_open","ask_high","ask_low","ask_close","ticks"]
            with p.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=fields)
                w.writeheader()
                for b in rows:
                    w.writerow({k:b[k].isoformat(sep=" ") if k=="time" else b[k] for k in fields})
            loaded=wf.read_bars(p)
            self.assertEqual(len(loaded),4)
            self.assertEqual(loaded[0]["bid_open"],rows[0]["bid_open"])

    def test_temporal_boundary_crossers_never_count_as_holdout_or_training_profit(self):
        base=dt.datetime(2026,1,2,0,0)
        one=base+dt.timedelta(days=1)
        two=base+dt.timedelta(days=2)
        def t(start,finish,pnl):
            return {"entry":start.isoformat(),"exit":finish.isoformat(),"pnl":pnl}
        trades=[t(base,base+dt.timedelta(hours=1),-10),
                t(base,one+dt.timedelta(minutes=1),5000),
                t(one+dt.timedelta(hours=1),one+dt.timedelta(hours=2),25),
                t(two,two+dt.timedelta(minutes=5),35)]
        splits,excluded=wf.partition_closed_trades(trades,one,two)
        self.assertEqual(splits,{"analysis":[-10],"validation":[25],"holdout":[35]})
        self.assertEqual(len(excluded),1)
        self.assertEqual(excluded[0]["pnl"],5000)
        with self.assertRaisesRegex(ValueError,"exit precedes"):
            wf.partition_closed_trades([t(two,one,12)],one,two)

    def test_take_profit_does_not_grant_unverifiable_favorable_gap(self):
        b={"bid_open":102.0,"bid_low":101.0,"bid_high":104.0,
           "ask_open":98.0,"ask_low":96.0,"ask_high":99.0}
        self.assertEqual(wf.conservative_exit_fill(1,95,100,b,0.2),(99.8,False))
        self.assertEqual(wf.conservative_exit_fill(-1,105,100,b,0.2),(100.2,False))

    def test_adverse_gap_and_both_levels_hit_choose_stop(self):
        gap={"bid_open":92.0,"bid_low":90.0,"bid_high":100.0,
             "ask_open":107.0,"ask_low":96.0,"ask_high":110.0}
        self.assertEqual(wf.conservative_exit_fill(1,95,105,gap,0.2),(91.8,True))
        self.assertEqual(wf.conservative_exit_fill(-1,105,95,gap,0.2),(107.2,True))
        both={"bid_open":100.0,"bid_low":94.0,"bid_high":107.0,
              "ask_open":101.0,"ask_low":93.0,"ask_high":108.0}
        self.assertEqual(wf.conservative_exit_fill(1,95,105,both,0.0),(95.0,True))
        self.assertEqual(wf.conservative_exit_fill(-1,105,95,both,0.0),(105.0,True))

    def test_crossed_bidask_fails_closed(self):
        bars=synthetic(3)
        with tempfile.TemporaryDirectory() as temp:
            p=pathlib.Path(temp)/"bad.csv"
            fields=["time","bid_open","bid_high","bid_low","bid_close",
                    "ask_open","ask_high","ask_low","ask_close","ticks"]
            with p.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=fields)
                w.writeheader()
                for i,b in enumerate(bars):
                    d={k:b[k].isoformat(sep=" ") if k=="time" else b[k] for k in fields}
                    if i==1: d["ask_open"]=d["bid_open"]-1
                    w.writerow(d)
            with self.assertRaisesRegex(ValueError,"crossed"):
                wf.read_bars(p)

if __name__=="__main__":
    unittest.main()
