#!/usr/bin/env python3
import gzip
import pathlib
import tempfile
import unittest
from tick_exact_sma_replay import actual_tick_exit,crossover_from_closed_bars,replay_week,replay_files,next_wilder_atr
from public_xauusd_ingest import HEADER

class TickExactReplayTests(unittest.TestCase):
    def gz(self,root,rows):
        p=pathlib.Path(root)/"quote_fixture.gz"
        with gzip.open(p,"wt",encoding="utf-8") as f:
            f.write(",".join(HEADER)+"\n")
            for x in rows:f.write(x+"\n")
        return p

    def test_actual_tick_stop_gap_and_target_use_correct_bid_ask(self):
        long={"side":1,"stop":99.0,"target":106.0}
        short={"side":-1,"stop":106.0,"target":99.0}
        self.assertEqual(actual_tick_exit(long,98.0,98.2,0.2),(97.8,"stop"))
        self.assertEqual(actual_tick_exit(long,106.8,107.0,0.2),(105.8,"target"))
        self.assertEqual(actual_tick_exit(short,108.0,108.3,0.2),(108.5,"stop"))
        self.assertEqual(actual_tick_exit(short,98.0,98.5,0.2),(99.2,"target"))
        self.assertIsNone(actual_tick_exit(long,103.0,103.2,0.2))

    def test_crossover_uses_last_two_fully_closed_candles(self):
        bars=[{"bid_close":100.0} for _ in range(31)]
        self.assertEqual(crossover_from_closed_bars(bars),0)
        bars[-1]["bid_close"]=105.0
        self.assertEqual(crossover_from_closed_bars(bars),1)
        bars=[{"bid_close":100.0} for _ in range(31)]
        bars[-1]["bid_close"]=95.0
        self.assertEqual(crossover_from_closed_bars(bars),-1)
        self.assertEqual(crossover_from_closed_bars(bars[:25]),0)

    def test_streaming_closed_bar_atr_matches_reference_wilder(self):
        import datetime as dt
        from walkforward_bidask import atr_wilder
        completed=[]
        state=(0,0.0,None)
        for i in range(80):
            current=4400+((i*13)%19)
            bar={"time":dt.datetime(2026,1,1)+dt.timedelta(minutes=5*i),
                 "bid_high":current+1.5,
                 "bid_low":current-2.0,
                 "bid_close":current+0.3}
            previous=completed[-1]["bid_close"] if completed else None
            state=next_wilder_atr(state,bar,previous)
            completed.append(bar)
            reference=atr_wilder(completed)[-1]
            if reference is None:self.assertIsNone(state[2])
            else:self.assertAlmostEqual(state[2],reference,places=10)

    def test_short_tick_sample_no_future_data_or_pnl(self):
        rows=[
            "2026-01-02 10:00:00.000,100.2,100.0,1,1",
            "2026-01-02 10:00:00.100,100.4,100.2,1,1",
            "2026-01-02 10:05:00.000,100.3,100.1,1,1",
            "2026-01-02 10:05:01.000,100.5,100.3,1,1"]
        with tempfile.TemporaryDirectory() as root:
            result=replay_week(self.gz(root,rows))
            self.assertEqual(result["m5_bars"],2)
            self.assertEqual(result["ticks"],4)
            self.assertEqual(result["closed_trades"],0)
            self.assertEqual(result["net_profit_usd"],0)
            self.assertFalse(result["real_money_release_permitted"])
            self.assertIsNone(result["profit_factor"])

    def test_50_dollar_account_refuses_minimum_gold_lot(self):
        # Synthetic quote changes generate crossovers, but risk budget is
        # just USD 0.25. Do not force an unsafe 0.01 lot trade.
        import datetime as dt,math
        base=dt.datetime(2026,1,2,0,0)
        rows=[]
        for i in range(100):
            price=100+3*math.sin(i/7.0)
            when=(base+dt.timedelta(minutes=5*i)).strftime("%Y-%m-%d %H:%M:%S")
            rows.append(f"{when}.000,{price+0.2:.6f},{price:.6f},1,1")
        with tempfile.TemporaryDirectory() as root:
            result=replay_week(self.gz(root,rows),initial_equity=50)
            self.assertGreater(result["rejections"].get("crossover_signals",0),0)
            self.assertGreater(result["rejections"].get("risk_reject_min_lot",0),0)
            self.assertEqual(result["closed_trades"],0)
            self.assertEqual(result["final_equity_usd"],50)
            self.assertFalse(result["real_money_release_permitted"])

    def test_nonmonotonic_and_invalid_price_rejected(self):
        rows=["2026-01-02 10:00:01.000,100.2,100.0,1,1",
              "2026-01-02 10:00:00.000,100.2,100.0,1,1"]
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,"nonmonotonic"):
                replay_week(self.gz(root,rows))
            with self.assertRaises(ValueError):
                replay_week(self.gz(root,["2026-01-02 10:00:00.000,99,100,1,1"]))

    def test_split_input_files_preserve_exact_portfolio_and_indicators(self):
        # A file boundary MUST NOT close a trade, reset equity/drawdown,
        # restart ATR, or create a new artificial five-minute candle.
        import datetime as dt, math
        base=dt.datetime(2026,1,2)
        rows=[]
        for i in range(175):
            price=4400+12*math.sin(i/9.0)
            t=base+dt.timedelta(minutes=5*i)
            for milliseconds,delta in ((0,0.0),(100,0.3)):
                stamp=t.strftime("%Y-%m-%d %H:%M:%S")+f".{milliseconds:03d}"
                rows.append(f"{stamp},{price+0.25+delta:.6f},{price+delta:.6f},1,1")
        with tempfile.TemporaryDirectory() as root:
            a=pathlib.Path(root)/"a"
            b=pathlib.Path(root)/"b"
            joined=pathlib.Path(root)/"joined"
            for folder in (a,b,joined):folder.mkdir()
            p1=self.gz(a,rows[:141])  # Deliberately split within an M5 bar
            p2=self.gz(b,rows[141:])
            p3=self.gz(joined,rows)
            chunked=replay_files([p1,p2])
            continuous=replay_week(p3)
            for key in ("net_profit_usd","closed_trades",
                        "tick_order_max_marked_equity_drawdown_fraction",
                        "rejections","m5_bars","first_tick_utc","last_tick_utc",
                        "most_recent_5_trades"):
                self.assertEqual(chunked[key],continuous[key],key)
            self.assertEqual(chunked["input_gzip_file_count"],2)
            self.assertEqual(continuous["input_gzip_file_count"],1)

    def test_cross_file_time_reversal_and_invalid_headers_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            a=pathlib.Path(root)/"a"
            b=pathlib.Path(root)/"b"
            a.mkdir();b.mkdir()
            earlier=self.gz(a,["2026-01-02 10:00:00.000,100.2,100.0,1,1"])
            later=self.gz(b,["2026-01-02 10:05:00.000,100.2,100.0,1,1"])
            with self.assertRaisesRegex(ValueError,"nonmonotonic"):
                replay_files([later,earlier])
            with self.assertRaisesRegex(ValueError,"at least one"):
                replay_files([])
            broken=b/"broken.gz"
            with gzip.open(broken,"wt") as handle:
                handle.write("time,close\\n2026-01-02 10:10:00.000,100\\n")
            with self.assertRaisesRegex(ValueError,"source columns"):
                replay_files([earlier,broken])

    def test_reject_risk_increasing_inputs(self):
        with tempfile.TemporaryDirectory() as root:
            p=self.gz(root,["2026-01-02 10:00:00.000,100.2,100.0,1,1"])
            for kwargs in ({"slippage":-0.1},{"commission_per_lot":-7},{"initial_equity":0}):
                with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                    replay_week(p,**kwargs)

if __name__=="__main__":
    unittest.main()
