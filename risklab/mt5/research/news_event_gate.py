#!/usr/bin/env python3
"""Point-in-time scheduled news / sudden-event embargo for research.

Never predicts unexpected geopolitics. Historical information must have a
documented timestamp at which it became available. A missing required feed,
stale coverage, unknown category or malformed UTC timestamp fails closed.
No network calls and no invented events.
"""
from __future__ import annotations
import csv
import datetime as dt
import pathlib
from dataclasses import dataclass
from typing import Sequence

UTC=dt.timezone.utc
FIELDS=("id","kind","event_at_utc","known_at_utc","importance","source_url")
KINDS={"scheduled_economic","unscheduled_geopolitical","exchange_disruption"}
IMPORTANCE={"high","critical"}


def parse_utc(s: str) -> dt.datetime:
    """Require full ISO 8601 with literal Z, never infer local or broker zone."""
    if not isinstance(s,str) or not s.endswith("Z"):
        raise ValueError("timestamp must end in Z for UTC")
    try:
        timestamp=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("invalid UTC event timestamp") from exc
    if timestamp.utcoffset()!=dt.timedelta(0) or timestamp.tzinfo is None:
        raise ValueError("not timezone aware UTC")
    return timestamp


@dataclass(frozen=True)
class Event:
    id: str
    kind: str
    event_at: dt.datetime
    known_at: dt.datetime
    importance: str
    source_url: str


def load_events(path: pathlib.Path) -> list[Event]:
    """Each event includes provenance, timestamp, and when it was publicly known."""
    events=[]
    ids=set()
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if tuple(reader.fieldnames or ())!=FIELDS:
            raise ValueError(f"expected exactly the columns {FIELDS}")
        for row in reader:
            if not all(row.get(k) for k in FIELDS):
                raise ValueError("missing field in event record")
            event=Event(id=row["id"].strip(),kind=row["kind"].strip(),
                        event_at=parse_utc(row["event_at_utc"]),
                        known_at=parse_utc(row["known_at_utc"]),
                        importance=row["importance"].strip(),
                        source_url=row["source_url"].strip())
            if event.id in ids: raise ValueError("duplicate event id")
            if event.kind not in KINDS or event.importance not in IMPORTANCE:
                raise ValueError("unrecognized event classification")
            if not event.source_url.startswith("https://"):
                raise ValueError("event requires an https provenance URL")
            if event.kind=="scheduled_economic" and event.known_at>event.event_at:
                raise ValueError("scheduled event cannot be announced after release")
            if event.kind!="scheduled_economic" and event.known_at<event.event_at:
                raise ValueError("unscheduled event cannot be used as a prediction")
            ids.add(event.id)
            events.append(event)
    if not events: raise ValueError("no reliable event records")
    return sorted(events,key=lambda x:x.event_at)


def event_embargo(decision_time: dt.datetime, events: Sequence[Event],
                  before_minutes=45,after_minutes=45) -> list[str]:
    """Only blocks on info already public by the decision-time candle.

    The blackout before a scheduled release is allowed only if its planned
    release time was publicly known when the decision was made. For a
    surprise/geopolitical event, block can start only AFTER known_at.
    """
    if decision_time.tzinfo is None or decision_time.utcoffset()!=dt.timedelta(0):
        raise ValueError("decision time must be UTC-aware")
    if before_minutes<0 or after_minutes<0:
        raise ValueError("invalid event embargo window")
    found=[]
    for e in events:
        if e.known_at>decision_time:
            continue
        start=e.event_at-dt.timedelta(minutes=before_minutes) if e.kind=="scheduled_economic" else e.known_at
        end=max(e.event_at,e.known_at)+dt.timedelta(minutes=after_minutes)
        if start<=decision_time<=end:
            found.append(e.id)
    return found


def feed_is_valid(decision_time:dt.datetime,source_checked_at:dt.datetime,
                  valid_until:dt.datetime,events:Sequence[Event],required=True)->bool:
    """Expiration is operational coverage, not proof all shocks are foreseeable."""
    if not required: return True
    if not events: return False
    if any(t.tzinfo is None or t.utcoffset()!=dt.timedelta(0)
           for t in (decision_time,source_checked_at,valid_until)):
        return False
    if source_checked_at>decision_time or valid_until<decision_time:
        return False
    return True
