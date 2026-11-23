#!/usr/bin/env python3
"""Offline validation of fail-closed evidence decisions."""
import importlib.util
import pathlib
import unittest

p=pathlib.Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location("readiness_gate",p/"readiness_gate.py")
gate=importlib.util.module_from_spec(s)
s.loader.exec_module(gate)

def case(mode="regime",trades=150,holdout=40,net=1200,holdout_net=240,pf=1.6,dd=.06,slip=.15):
    return {"mode":mode,"slippage_usd_per_oz_per_side":slip,
            "assumed_commission_usd_per_lot_round_turn":7.0,
            "initial_equity":10000,"number_of_closed_trades":trades,
            "net_pnl":net,"profit_factor":pf,
            "max_closed_equity_drawdown_fraction":dd,
            "split_60_20_20":[{"name":"analysis","trades":80,"net_pnl":600},
                             {"name":"validation","trades":30,"net_pnl":360},
                             {"name":"holdout","trades":holdout,"net_pnl":holdout_net}]}

class ReadinessChecks(unittest.TestCase):
    def test_zero_trades_never_pass(self):
        a=case(trades=0,holdout=0,net=0,pf=None,holdout_net=0)
        d=gate.judge_one(a,case(slip=.5,trades=0,net=0))
        self.assertEqual(d["decision"],"INSUFFICIENT_EVIDENCE")

    def test_loss_cannot_be_overridden_by_high_win_rate(self):
        a=case(net=-50,holdout_net=-10)
        a["win_rate"]=.99
        d=gate.judge_one(a,case(slip=.5,net=-100))
        self.assertEqual(d["decision"],"INSUFFICIENT_EVIDENCE")

    def test_missing_commission_assumption_blocks_approval(self):
        reference=case()
        del reference["assumed_commission_usd_per_lot_round_turn"]
        d=gate.judge_one(reference,case(slip=.5))
        self.assertEqual(d["decision"],"INSUFFICIENT_EVIDENCE")
        self.assertIn("commission", " ".join(d["reasons"]))

    def test_cost_stress_must_pass(self):
        d=gate.judge_one(case(),case(slip=.5,net=-0.01))
        self.assertIn("adverse execution-cost stress", " ".join(d["reasons"]))

    def test_boundary_crossing_trade_blocks_approval(self):
        a=case()
        a["boundary_crossing_trades"]=1
        s=case(slip=.5)
        d=gate.judge_one(a,s)
        self.assertEqual(d["decision"],"INSUFFICIENT_EVIDENCE")
        self.assertIn("cross-partition", " ".join(d["reasons"]))

    def test_holdout_must_be_large_and_profitable(self):
        d=gate.judge_one(case(holdout=5,holdout_net=-20),case(slip=.5))
        self.assertEqual(d["decision"],"INSUFFICIENT_EVIDENCE")
        self.assertGreaterEqual(len(d["reasons"]),2)

    def test_positive_is_still_demo_only(self):
        d=gate.judge_one(case(),case(slip=.5))
        self.assertEqual(d["decision"],"SUPERVISED_DEMO_CANDIDATE_ONLY")
        report={"results":[case(mode="baseline"),case(mode="baseline",slip=.5),
                           case(mode="regime"),case(mode="regime",slip=.5)],
                "m5_bars":20000,"status":"external_feeds_only"}
        full=gate.readiness(report)
        self.assertFalse(full["real_money_release_permitted"])
        self.assertEqual(len(full["candidate_checks"]),3)

    def test_missing_or_ambiguous_cost_results_fail_closed(self):
        self.assertEqual(gate.judge_one(None,None)["decision"],"INSUFFICIENT_EVIDENCE")
        d=gate.readiness({"results":[case(),case(),case(slip=.5)]})
        x=next(q for q in d["candidate_checks"] if q["mode"]=="regime")
        self.assertEqual(x["decision"],"INSUFFICIENT_EVIDENCE")

if __name__=="__main__":
    unittest.main()
