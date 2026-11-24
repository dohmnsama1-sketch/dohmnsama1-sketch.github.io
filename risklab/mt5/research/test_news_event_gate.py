#!/usr/bin/env python3
"""Offline point-in-time news embargo regression checks; NO real event claims."""
import csv
import datetime as dt
import importlib.util
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location("zalah_news",ROOT/"news_event_gate.py")
news=importlib.util.module_from_spec(sp)
import sys
sys.modules[sp.name]=news
sp.loader.exec_module(news)

def utc(s):
    return news.parse_utc(s)

class NewsRiskGateTests(unittest.TestCase):
    def csv(self,folder,rows):
        p=pathlib.Path(folder)/"events.csv"
        with p.open("w",encoding="utf-8",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=news.FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return p

    def item(self,kind="scheduled_economic",event="2026-11-25T13:30:00Z",
             known="2026-11-20T12:00:00Z",key="test-event"):
        return {"id":key,"kind":kind,"event_at_utc":event,
                "known_at_utc":known,"importance":"high",
                "source_url":"https://example.org/verifiable-original-source"}

    def test_scheduled_known_release_blocks_pre_and_post_only(self):
        with tempfile.TemporaryDirectory() as folder:
            events=news.load_events(self.csv(folder,[self.item()]))
            self.assertEqual(news.event_embargo(utc("2026-11-25T13:00:00Z"),events),["test-event"])
            self.assertEqual(news.event_embargo(utc("2026-11-25T14:15:00Z"),events),["test-event"])
            self.assertEqual(news.event_embargo(utc("2026-11-25T12:40:00Z"),events),[])
            self.assertEqual(news.event_embargo(utc("2026-11-25T14:16:00Z"),events),[])

    def test_never_use_future_announcement_for_old_backtest(self):
        with tempfile.TemporaryDirectory() as folder:
            rows=[self.item(known="2026-11-25T13:25:00Z")]
            events=news.load_events(self.csv(folder,rows))
            self.assertEqual(news.event_embargo(utc("2026-11-25T13:10:00Z"),events),[])
            self.assertEqual(news.event_embargo(utc("2026-11-25T13:25:00Z"),events),["test-event"])

    def test_unscheduled_shock_cannot_be_previously_known(self):
        with tempfile.TemporaryDirectory() as folder:
            rows=[self.item(kind="unscheduled_geopolitical",
                            known="2026-11-25T13:40:00Z")]
            events=news.load_events(self.csv(folder,rows))
            self.assertEqual(news.event_embargo(utc("2026-11-25T13:39:00Z"),events),[])
            self.assertEqual(news.event_embargo(utc("2026-11-25T13:40:00Z"),events),["test-event"])
            self.assertEqual(news.event_embargo(utc("2026-11-25T14:26:00Z"),events),[])

    def test_unannounced_event_must_not_be_falsely_predicted(self):
        with tempfile.TemporaryDirectory() as folder:
            rows=[self.item(kind="unscheduled_geopolitical",
                            known="2026-11-20T12:00:00Z")]
            with self.assertRaisesRegex(ValueError,"cannot be used as a prediction"):
                news.load_events(self.csv(folder,rows))

    def test_schedule_cannot_be_created_after_its_published_time(self):
        with tempfile.TemporaryDirectory() as folder:
            rows=[self.item(known="2026-11-25T13:31:00Z")]
            with self.assertRaisesRegex(ValueError,"cannot be announced after release"):
                news.load_events(self.csv(folder,rows))

    def test_missing_unverified_future_and_expired_feed_all_fail_closed(self):
        now=utc("2026-11-25T13:00:00Z")
        good=news.Event("x","scheduled_economic",now,utc("2026-11-20T12:00:00Z"),
                        "high","https://example.org")
        self.assertFalse(news.feed_is_valid(now,now,now,[]))
        self.assertFalse(news.feed_is_valid(now,utc("2026-11-25T13:01:00Z"),now,[good]))
        self.assertFalse(news.feed_is_valid(now,now,utc("2026-11-25T12:59:00Z"),[good]))
        self.assertTrue(news.feed_is_valid(now,now,now,[good]))

    def test_reject_duplicate_event_and_missing_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            row=self.item()
            with self.assertRaisesRegex(ValueError,"duplicate"):
                news.load_events(self.csv(folder,[row,row]))
            row["source_url"]="none"
            with self.assertRaisesRegex(ValueError,"provenance"):
                news.load_events(self.csv(folder,[row]))

    def test_refuse_local_time_ambiguity(self):
        for s in ("2026-11-25 13:30","2026-11-25T13:30:00+03:00",""):
            with self.subTest(s=s),self.assertRaises(ValueError):
                news.parse_utc(s)
        with self.assertRaisesRegex(ValueError,"UTC-aware"):
            news.event_embargo(dt.datetime(2026,11,25,13,30),[])

if __name__=="__main__":
    unittest.main()
