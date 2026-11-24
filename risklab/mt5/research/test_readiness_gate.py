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
            "months_with_trades":8,"positive_month_share_active":0.75,
            "largest_trade_loss_usd":-52,
            "net_pnl":net,"ending_equity":10000+net,
            "gross_profit":max(0,net)+500,"gross_loss":max(0,-net)+500,
            "profit_factor":pf,
            "max_closed_equity_drawdown_fraction":dd,
            "max_adverse_intrabar_equity_proxy_fraction":dd,
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

    def test_forged_net_and_missing_fill_accounting_rejected(self):
        reference=case()
        reference["net_pnl"]=999999
        result=gate.judge_one(reference,case(slip=.5))
        self.assertEqual(result["decision"],"INSUFFICIENT_EVIDENCE")
        self.assertIn("do not reconcile"," ".join(result["reasons"]))
        reference=case()
        del reference["gross_loss"]
        result=gate.judge_one(reference,case(slip=.5))
        self.assertIn("auditable P/L"," ".join(result["reasons"]))

    def test_partition_counts_must_reconcile(self):
        reference=case()
        reference["split_60_20_20"][0]["trades"]=800
        result=gate.judge_one(reference,case(slip=.5))
        self.assertIn("trade counts do not reconcile"," ".join(result["reasons"]))

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

    def test_profitability_requires_multiple_profitable_months(self):
        reference=case()
        reference["months_with_trades"]=1
        reference["positive_month_share_active"]=1.0
        decision=gate.judge_one(reference,case(slip=.5))
        self.assertEqual(decision["decision"],"INSUFFICIENT_EVIDENCE")
        self.assertIn("six distinct active months"," ".join(decision["reasons"]))
        reference["months_with_trades"]=8
        reference["positive_month_share_active"]=0.50
        decision=gate.judge_one(reference,case(slip=.5))
        self.assertIn("60% of active calendar months"," ".join(decision["reasons"]))

    def test_large_single_trade_loss_rejects_candidate(self):
        reference=case()
        reference["largest_trade_loss_usd"]=-300
        decision=gate.judge_one(reference,case(slip=.5))
        self.assertEqual(decision["decision"],"INSUFFICIENT_EVIDENCE")
        self.assertIn("largest individual realized loss"," ".join(decision["reasons"]))

    def test_intrabar_stress_cannot_be_hidden_by_small_closed_drawdown(self):
        baseline=case(dd=0.01)
        baseline["max_adverse_intrabar_equity_proxy_fraction"]=0.12
        d=gate.judge_one(baseline,case(slip=.5))
        self.assertEqual(d["decision"],"INSUFFICIENT_EVIDENCE")
        self.assertIn("intrabar adverse-equity", " ".join(d["reasons"]))
        baseline.pop("max_adverse_intrabar_equity_proxy_fraction")
        d=gate.judge_one(baseline,case(slip=.5))
        self.assertEqual(d["decision"],"INSUFFICIENT_EVIDENCE")

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
