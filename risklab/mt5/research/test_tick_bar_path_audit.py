#!/usr/bin/env python3
import gzip
import pathlib
import tempfile
import unittest

from tick_bar_path_audit import audit_ticks, first_touch
from public_xauusd_ingest import HEADER


class TickOrderingTests(unittest.TestCase):
    def sample(self,root,lines):
        p=pathlib.Path(root)/"fixture.csv.gz"
        with gzip.open(p,"wt",encoding="utf-8",newline="") as f:
            f.write(",".join(HEADER)+"\n")
            for line in lines:
                f.write(line+"\n")
        return p

    def test_tick_order_reveals_when_stop_first_assumption_was_wrong(self):
        lines=[
          "2026-01-02 10:00:00.000,100.2,100.0,1,1",
          "2026-01-02 10:00:01.000,103.7,103.5,1,1",
          "2026-01-02 10:00:02.000,96.8,96.6,1,1",
          "2026-01-02 10:05:00.000,100.2,100.0,1,1"]
        with tempfile.TemporaryDirectory() as root:
            r=audit_ticks(self.sample(root,lines))
            self.assertEqual(r["ticks"],4)
            self.assertEqual(r["m5_bars"],2)
            self.assertEqual(r["counts"]["long_both_levels_inside_m5"],1)
            self.assertEqual(r["counts"]["short_both_levels_inside_m5"],1)
            self.assertEqual(r["counts"]["long_bar_stop_first_disagrees_with_tick_order"],1)
            self.assertEqual(r["counts"]["short_bar_stop_first_agrees_with_tick_order"],1)
            self.assertEqual(r["counts"]["long_first_target"],1)
            self.assertEqual(r["counts"]["short_first_stop"],1)

    def test_bid_ask_exits_differ(self):
        self.assertEqual(first_touch(1,97.9,98.1,98.0,103.0),"stop")
        self.assertEqual(first_touch(-1,99.0,102.1,102.0,97.0),"stop")
        self.assertIsNone(first_touch(1,101,101.1,98,103))
        with self.assertRaises(ValueError):
            first_touch(0,101,101.1,98,103)

    def test_invalid_quote_and_backwards_clock_fail(self):
        with tempfile.TemporaryDirectory() as root:
            bad=["2026-01-02 10:00:01.000,100,101,1,1"]
            with self.assertRaises(ValueError):
                audit_ticks(self.sample(root,bad))
            bad=["2026-01-02 10:00:02.000,100.2,100.0,1,1",
                 "2026-01-02 10:00:01.000,100.2,100.0,1,1"]
            with self.assertRaisesRegex(ValueError,"nonmonotonic"):
                audit_ticks(self.sample(root,bad))

    def test_empty_data_not_validation(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,"empty"):
                audit_ticks(self.sample(root,[]))
            with self.assertRaisesRegex(ValueError,"positive"):
                audit_ticks(self.sample(root,["2026-01-02 10:00:00.000,100.2,100.0,1,1"]),
                            stop_distance=-1)

if __name__=="__main__":
    unittest.main()
