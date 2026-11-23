#!/usr/bin/env python3
"""Unit tests for independent tick ingestion; no network required."""
import gzip
import importlib.util
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("zalah_ticks",ROOT/"public_xauusd_ingest.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class QualityGateTests(unittest.TestCase):
    def make(self, root, lines):
        p=pathlib.Path(root)/"week.csv.gz"
        with gzip.open(p,"wt",encoding="utf-8") as w:
            w.write(",".join(mod.HEADER)+"\n")
            for line in lines:
                w.write(line+"\n")
        return p

    def test_week_ranges(self):
        self.assertEqual(mod.week_numbers("1,2,4-6"),[1,2,4,5,6])
        for bad in ("0","48","5-1",""):
            with self.assertRaises(ValueError):
                mod.week_numbers(bad)

    def test_bidask_aggregation_and_spread(self):
        with tempfile.TemporaryDirectory() as root:
            p=self.make(root,[
                "2026-01-02 10:00:00.001,4401.000,4400.000,0,0",
                "2026-01-02 10:00:01.001,4403.000,4399.000,0,0",
                "2026-01-02 10:05:00.001,4398.000,4397.000,0,0"])
            bars=[]
            report,last=mod.summarize_gz(p,1,bars,None)
            self.assertEqual(report["rows"],3)
            self.assertEqual(last,"2026-01-02 10:05:00.001")
            self.assertEqual(len(bars),2)
            self.assertEqual(bars[0]["bid_open"],4400.)
            self.assertEqual(bars[0]["bid_high"],4400.)
            self.assertEqual(bars[0]["bid_low"],4399.)
            self.assertEqual(bars[0]["ask_high"],4403.)
            self.assertEqual(bars[0]["ticks"],2)
            self.assertAlmostEqual(bars[0]["spread_sum"]/2,2.5)
            self.assertEqual(bars[1]["time"],"2026-01-02 10:05:00")
            out=pathlib.Path(root)/"m5.csv"
            mod.write_m5(out,bars)
            self.assertIn("avg_spread",out.read_text())
            self.assertIn("2.5",out.read_text())

    def test_same_timestamp_is_permitted(self):
        with tempfile.TemporaryDirectory() as root:
            p=self.make(root,[
                "2026-01-02 10:00:00.001,4401,4400,0,0",
                "2026-01-02 10:00:00.001,4402,4400,0,0"])
            bars=[]
            res,_=mod.summarize_gz(p,1,bars,None)
            self.assertEqual(res["rows"],2)

    def test_reject_backwards_time(self):
        with tempfile.TemporaryDirectory() as root:
            p=self.make(root,[
                "2026-01-02 10:05:00.001,4401,4400,0,0",
                "2026-01-02 10:00:00.001,4401,4400,0,0"])
            with self.assertRaisesRegex(ValueError,"non-monotonic"):
                mod.summarize_gz(p,1,[],None)

    def test_reject_invalid_quotes(self):
        for quote in ("4399,4400","NaN,4400","4400,-2","4400,inf"):
            with self.subTest(quote=quote):
                with self.assertRaises(ValueError):
                    mod.parse_tick_row(("2026-01-02 10:05:00.000,"+quote+",0,0").split(","))

    def test_bad_calendar_timestamp(self):
        with self.assertRaises(ValueError):
            mod.parse_tick_row(["2026-13-40 10:05:00.000","4401","4400","0","0"])

    def test_catalog_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"tick count differs"):
            mod.validate_source_week({"week":1,"rows":1,"first_tick_utc":"a","last_tick_utc":"b"},
                                     {"rows":2,"first_tick_utc":"a","last_tick_utc":"b"})

if __name__=="__main__":
    unittest.main()
