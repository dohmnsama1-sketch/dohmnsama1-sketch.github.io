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
        for mode in ("baseline","regime"):
            for slip in (0.0,.15,.5):
                with self.subTest(mode=mode,slip=slip):
                    r=wf.evaluate(bars,mode,slip)
                    self.assertGreater(r["ending_equity"],0)
                    self.assertEqual(len(r["split_60_20_20"]),3)
                    self.assertEqual(r["number_of_closed_trades"],
                                     sum(x["trades"] for x in r["split_60_20_20"]))
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
