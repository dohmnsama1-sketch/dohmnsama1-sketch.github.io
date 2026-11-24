#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location("zalah_summary",ROOT/"validate_research_summary.py")
summary=importlib.util.module_from_spec(sp)
sp.loader.exec_module(summary)


def make(mode, equity=10000, news="not_enabled",slip=.15):
    return {"mode":mode,"slippage_usd_per_oz_per_side":slip,
            "initial_equity":equity,
            "news_event_mode":news,
            "number_of_closed_trades":25,
            "net_pnl":-500,
            "bootstrap_week_count":46,
            "bootstrap_status":"EXPLORATORY",
            "bootstrap_net_pnl_p2p5":-1000,
            "bootstrap_positive_fraction":0.01}


class ResearchSummaryTests(unittest.TestCase):
    def report(self):
        rows=[]
        for mode in ("baseline","regime","breakout"):
            rows.extend([make(mode),make(mode,50),make(mode,news="archived_events_point_in_time"),
                         make(mode,slip=.5)])
        return {"status":"exploratory_not_MT5_or_Exness_verified","results":rows}

    def test_only_three_normal_reference_runs_and_keep_negative_pnl(self):
        selected=summary.select_reference_runs(self.report())
        self.assertEqual(len(selected),3)
        self.assertEqual({r["mode"] for r in selected},{"baseline","regime","breakout"})
        self.assertTrue(all(r["net_pnl"]<0 for r in selected))
        self.assertTrue(all(r["initial_equity"]==10000 for r in selected))

    def test_duplicate_or_missing_reference_fails_closed(self):
        report=self.report()
        report["results"].append(make("baseline"))
        with self.assertRaisesRegex(ValueError,"expected one"):
            summary.select_reference_runs(report)
        report=self.report()
        report["results"]=[r for r in report["results"] if r["mode"]!="regime"]
        with self.assertRaisesRegex(ValueError,"expected one"):
            summary.select_reference_runs(report)

    def test_insufficient_week_stress_fails(self):
        report=self.report()
        report["results"][0]["bootstrap_week_count"]=3
        with self.assertRaisesRegex(ValueError,"insufficient"):
            summary.select_reference_runs(report)

    def test_source_mismatch_fails(self):
        report=self.report()
        report["status"]="MT5_EXNESS_LIVE_CONFIRMED"
        with self.assertRaisesRegex(ValueError,"unrecognized"):
            summary.select_reference_runs(report)

if __name__=="__main__":
    unittest.main()
