#!/usr/bin/env python3
"""Regenerate per-board Pinterest RSS 2.0 feeds from the committed schedule.

Intended to run daily on GitHub Actions (and locally). No third-party
dependencies, no secrets.

Behaviour:
  * "Today" is the calendar date in Asia/Riyadh.
  * Each board feed includes only items whose schedule date is <= today.
  * At most FEED_LIMIT (25) most-recent items, oldest first in the XML
    (Pinterest publishes oldest unseen items first).
  * After the last planned date (2028-12-31), items cycle yearly: the same
    month-and-day from two years earlier is re-issued with a new guid, so
    the feeds (and the daily commit) keep moving without further work.
  * Writes are skipped when the item set is unchanged (lastBuildDate is
    derived from content, not the clock), so the Action only commits real
    changes. Because at least one new item appears on every planned day,
    a commit is expected every day through 2028-12-31, and on the cycle
    after that. Those commits on `main` are repository activity and reset
    GitHub's 60-day scheduled-workflow inactivity timer
    (docs: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-a-workflow).

Pinterest rules this script honours
  (https://help.pinterest.com/en/business/article/auto-publish-pins-from-your-rss-feed):
  * RSS 2.0 (not Atom).
  * Every item <link> is on the claimed domain (dohmnsama1-sketch.github.io).
  * Title and description come from <title> and <description>.
  * The pin image is in both <enclosure> and <media:content>.
  * 200 pins/day is Pinterest's account cap; this plan is 2–3/day.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RIYADH = ZoneInfo("Asia/Riyadh")
SITE = "https://dohmnsama1-sketch.github.io"
FEED_LIMIT = 25
SCHEDULE_END = date(2028, 12, 31)
CYCLE_YEARS = 2
FORBIDDEN = re.compile(
    r"\$99\b|lifetime updates?|free updates?|lifetime access",
    re.I,
)
GUMROAD = re.compile(r"gumroad\.com", re.I)

# Script lives at .github/scripts/generate_pinterest_feeds.py in the site repo.
# Locally it also lives under shop/pinterest/_src/rss_autopilot/.
def find_repo_root(start: Path) -> Path:
    p = start.resolve()
    for cand in [p, *p.parents]:
        if (cand / "pinterest" / "schedule.csv").is_file() and (cand / "feeds").is_dir() or (
            cand / "pinterest" / "schedule.csv"
        ).is_file():
            return cand
        if (cand / ".git").exists() and (cand / "pinterest").exists():
            return cand
    # fallback: site-clone if schedule already copied
    return start.resolve().parents[2] if (start.resolve().parents[0].name == "scripts") else start.resolve().parent


def today_riyadh(as_of: str | None = None) -> date:
    if as_of:
        return date.fromisoformat(as_of)
    return datetime.now(RIYADH).date()


def esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def rfc822(d: date, hh: int = 14, mm: int = 0) -> str:
    # 14:00 UTC = 17:00 Asia/Riyadh, matching the usual pin time.
    dt = datetime(d.year, d.month, d.day, hh, mm, 0, tzinfo=timezone.utc)
    return format_datetime(dt, usegmt=False)


def load_boards(root: Path) -> list[dict]:
    path = root / "pinterest" / "boards.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["boards"]


def load_schedule(root: Path) -> list[dict]:
    path = root / "pinterest" / "schedule.csv"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows


def is_eligible(row: dict) -> bool:
    if (row.get("rss_eligible") or "1").strip() in {"0", "false", "False", "no"}:
        return False
    link = row.get("link") or ""
    if GUMROAD.search(link):
        return False
    if not link.startswith(SITE):
        return False
    blob = " ".join(row.get(k) or "" for k in ("title", "description", "alt_text"))
    if FORBIDDEN.search(blob):
        return False
    return True


def shift_year_in_title(title: str, src_year: int, dst_year: int) -> str:
    """Replace a year only when it is a calendar label, not a product edition.

    Never rewrite 'Content Calendar 2027' / 'Etsy Content Calendar 2027' —
    that product is the 2027 edition. Seasonal 'New Year … 2027' labels
    may move forward.
    """
    if src_year == dst_year or str(src_year) not in title:
        # Still make the cycled title distinct.
        return title
    if re.search(r"(Content Calendar|Marketing Calendar)\s+" + str(src_year), title):
        return title
    # Ramadan expected-date phrases stay as written (they name a past window).
    if re.search(r"Expected[^.]{0,40}" + str(src_year), title):
        return title
    return title.replace(str(src_year), str(dst_year))


def cycle_row(row: dict, new_date: date, src_date: date) -> dict:
    out = dict(row)
    out["date"] = new_date.isoformat()
    out["day"] = ""
    out["weekday"] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][new_date.weekday()]
    src_year, dst_year = src_date.year, new_date.year
    out["title"] = shift_year_in_title(row["title"], src_year, dst_year)
    # Ensure uniqueness vs the original without inventing claims.
    tail = f" — {new_date.strftime('%B %Y')}"
    if tail.strip(" —") not in out["title"] and len(out["title"]) + len(tail) <= 100:
        out["title"] = out["title"] + tail
    elif len(out["title"]) + 8 <= 100:
        out["title"] = out["title"] + f" — {new_date.year}"
    out["pin_id"] = f"{row['pin_id']}-c{new_date.year}"
    # Keep the same image and the same link (UTM content stays the original
    # pin_id so analytics can group cycles). Guid is the new pin_id.
    return out


def items_for_today(rows: list[dict], today: date) -> list[dict]:
    planned = [r for r in rows if is_eligible(r)]
    if not planned:
        return []
    # Index planned items by date.
    by_date: dict[str, list[dict]] = defaultdict(list)
    for r in planned:
        by_date[r["date"]].append(r)

    out: list[dict] = []
    if today <= SCHEDULE_END:
        for r in planned:
            if date.fromisoformat(r["date"]) <= today:
                out.append(r)
        return out

    # After the plan: include the full plan, then one cycled day at a time
    # from 2029-01-01 through today.
    out.extend(planned)
    d = SCHEDULE_END + timedelta(days=1)
    while d <= today:
        src = date(d.year - CYCLE_YEARS, d.month, d.day)
        # 29 Feb: fall back to 28 Feb of the source year.
        try:
            src = date(d.year - CYCLE_YEARS, d.month, d.day)
        except ValueError:
            src = date(d.year - CYCLE_YEARS, d.month, 28)
        src_rows = by_date.get(src.isoformat()) or []
        if not src_rows:
            # Walk back up to 6 days to avoid a silent gap.
            for k in range(1, 7):
                alt = src - timedelta(days=k)
                src_rows = by_date.get(alt.isoformat()) or []
                if src_rows:
                    src = alt
                    break
        for r in src_rows:
            out.append(cycle_row(r, d, src))
        d += timedelta(days=1)
    return out


def latest_n(items: list[dict], n: int = FEED_LIMIT) -> list[dict]:
    # Sort newest first, take n, then return oldest-first for the XML.
    decorated = sorted(
        items,
        key=lambda r: (r["date"], r.get("time_suggested") or "", r.get("pin_id") or ""),
        reverse=True,
    )
    chosen = decorated[:n]
    chosen.reverse()
    return chosen


def image_url(row: dict) -> str:
    # image_file is repo-relative, e.g. pins/pinterest/{pin_id}.jpg
    rel = (row.get("image_file") or "").lstrip("/")
    return f"{SITE}/{rel}"


def item_link(row: dict) -> str:
    return row["link"]


def write_feed(
    path: Path,
    board: dict,
    items: list[dict],
    image_sizes: dict[str, int],
) -> str:
    slug = board["slug"]
    name = board["name"]
    feed_url = f"{SITE}/feeds/{slug}.xml"
    page_url = f"{SITE}/feeds/"
    last_dates = [date.fromisoformat(r["date"]) for r in items] or [date(2026, 11, 12)]
    last_build = rfc822(max(last_dates), 14, 5)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"',
        '    xmlns:atom="http://www.w3.org/2005/Atom"',
        '    xmlns:media="http://search.yahoo.com/mrss/">',
        "  <channel>",
        f"    <title>{esc(name)} — Dodiabak Studio</title>",
        f"    <link>{esc(page_url)}</link>",
        f"    <description>{esc('New pins for the ' + name + ' board. Tools and books by Dodiabak Studio.')}</description>",
        "    <language>en-us</language>",
        "    <ttl>1440</ttl>",
        f"    <lastBuildDate>{last_build}</lastBuildDate>",
        "    <generator>dohmnsama1-pinterest-rss</generator>",
        f'    <atom:link href="{esc(feed_url)}" rel="self" type="application/rss+xml"/>',
    ]
    for r in items:
        img = image_url(r)
        length = image_sizes.get(r.get("image_file") or "", 0)
        length_attr = f' length="{length}"' if length else ""
        pub = rfc822(date.fromisoformat(r["date"]))
        guid = f"{SITE}/feeds/item/{r['pin_id']}"
        parts += [
            "    <item>",
            f"      <title>{esc(r['title'])}</title>",
            f"      <description>{esc(r['description'])}</description>",
            f"      <link>{esc(item_link(r))}</link>",
            f'      <guid isPermaLink="false">{esc(guid)}</guid>',
            f"      <pubDate>{pub}</pubDate>",
            f'      <enclosure url="{esc(img)}" type="image/jpeg"{length_attr}/>',
            f'      <media:content url="{esc(img)}" type="image/jpeg" medium="image" width="1000" height="1500"/>',
            f"      <media:title>{esc(r['title'])}</media:title>",
            "    </item>",
        ]
    parts += ["  </channel>", "</rss>", ""]
    text = "\n".join(parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == text:
        return "unchanged"
    path.write_text(text, encoding="utf-8")
    return "written"


def validate_xml(path: Path) -> list[str]:
    problems = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        return [f"{path.name}: XML parse error: {e}"]
    root = tree.getroot()
    if root.tag != "rss" or root.attrib.get("version", "").split(".")[0] != "2":
        problems.append(f"{path.name}: not RSS 2.x (root={root.tag} version={root.attrib.get('version')})")
    ch = root.find("channel")
    if ch is None:
        return problems + [f"{path.name}: missing channel"]
    for req in ("title", "link", "description"):
        if ch.find(req) is None or not (ch.find(req).text or "").strip():
            problems.append(f"{path.name}: channel missing {req}")
    items = ch.findall("item")
    if len(items) > FEED_LIMIT:
        problems.append(f"{path.name}: {len(items)} items > {FEED_LIMIT}")
    guids = []
    for i, it in enumerate(items, 1):
        for req in ("title", "description", "link"):
            if it.find(req) is None or not (it.find(req).text or "").strip():
                problems.append(f"{path.name} item {i}: missing {req}")
        link = (it.findtext("link") or "")
        if link and not link.startswith(SITE):
            problems.append(f"{path.name} item {i}: link not on claimed domain: {link}")
        if GUMROAD.search(link):
            problems.append(f"{path.name} item {i}: gumroad link")
        enc = it.find("enclosure")
        if enc is None or not enc.attrib.get("url"):
            problems.append(f"{path.name} item {i}: missing enclosure")
        elif not enc.attrib["url"].startswith(SITE):
            problems.append(f"{path.name} item {i}: enclosure off-domain")
        media = it.find("{http://search.yahoo.com/mrss/}content")
        if media is None:
            problems.append(f"{path.name} item {i}: missing media:content")
        guid = it.findtext("guid")
        if guid:
            guids.append(guid)
        blob = (it.findtext("title") or "") + " " + (it.findtext("description") or "")
        if FORBIDDEN.search(blob):
            problems.append(f"{path.name} item {i}: forbidden wording")
    if len(guids) != len(set(guids)):
        problems.append(f"{path.name}: duplicate guids")
    return problems


def write_index(path: Path, boards: list[dict], counts: dict, today: date, schedule_meta: dict) -> None:
    rows_html = []
    for b in boards:
        slug = b["slug"]
        url = f"{SITE}/feeds/{slug}.xml"
        exists = "Yes — already on the account" if b.get("exists") else "No — create this board first, then connect"
        flag = "" if b.get("exists") else " (create board first)"
        rows_html.append(
            "<tr>"
            f"<td>{esc(b['name'])}{esc(flag)}</td>"
            f"<td><code>{esc(b['name'])}</code></td>"
            f"<td><a href='{esc(url)}'>{esc(url)}</a></td>"
            f"<td>{counts.get(slug, 0)}</td>"
            f"<td>{esc(exists)}</td>"
            "</tr>"
        )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pinterest RSS feeds — Dodiabak Studio</title>
<meta name="description" content="Per-board RSS 2.0 feeds for Pinterest auto-publish. Connect each feed to the matching board.">
<link rel="canonical" href="{SITE}/feeds/">
<style>
body{{font-family:system-ui,sans-serif;max-width:960px;margin:32px auto;padding:0 20px;line-height:1.5;color:#1b1a17}}
h1,h2{{line-height:1.2}}
code,td{{font-size:14px}}
table{{border-collapse:collapse;width:100%;margin:16px 0}}
th,td{{border:1px solid #ddd;padding:8px 10px;text-align:left;vertical-align:top}}
th{{background:#f4f1ea}}
.note{{background:#f4f1ea;padding:12px 16px;border-radius:8px}}
ol li{{margin:6px 0}}
</style>
</head>
<body>
<h1>Pinterest RSS auto-publish feeds</h1>
<p>These feeds power automatic Pins on the <strong>abak1694</strong> Pinterest account.
Each feed belongs to one board. A GitHub Action refreshes them every day
at 08:00 UTC (11:00 Asia/Riyadh). Only items dated on or before
<strong>{today.isoformat()}</strong> (Asia/Riyadh) appear, latest {FEED_LIMIT} per board.</p>
<p>Planned coverage: <strong>{schedule_meta.get('start','2026-11-12')}</strong> through
<strong>{schedule_meta.get('end','2028-12-31')}</strong>
({schedule_meta.get('rows', '?')} dated items). After that, the generator
re-issues earlier items with new ids so the feeds keep moving.</p>

<div class="note">
<p><strong>Before you connect:</strong> in Pinterest, claim this exact website:
<code>{SITE}</code>. Auto-publish is under
Settings → Create Pins in bulk → Auto-publish → Connect RSS feed,
and is only offered on a business account with a claimed site.
Every item link in these feeds is on that domain (Pinterest rejects
off-domain links, including Gumroad).</p>
</div>

<h2>Board-to-feed mapping</h2>
<p>Use the <em>exact</em> board name in the second column. Do not pick
“Freelance Pricing &amp; Profit Tips” — that board does not exist.
The live board is <strong>Freelancer Profit &amp; Scope Management</strong>.</p>
<table>
<thead><tr><th>Feed</th><th>Select this board in Pinterest</th><th>Feed URL</th><th>Items in feed today</th><th>Board exists?</th></tr></thead>
<tbody>
{''.join(rows_html)}
</tbody>
</table>

<h2>How to connect (once)</h2>
<ol>
<li>Open Pinterest on a desktop browser, signed in as <code>abak1694</code>.</li>
<li>Claim <code>{SITE}</code> if it is not already claimed (Settings → Claimed accounts).</li>
<li>Settings → Create Pins in bulk → Auto-publish → Connect RSS feed.</li>
<li>Paste one feed URL, choose the matching board, Save. Repeat for each feed.</li>
<li>Create <strong>Saudi Freelancer &amp; VAT Tools</strong> and
<strong>Large Print Puzzle Books</strong> first if they are still missing,
then connect those two feeds. Until they exist, those Pins will not publish.</li>
</ol>
<p>Pinterest creates Pins from new feed items within 24 hours, oldest first,
up to 200 Pins per day across all feeds. This plan stays well under that cap.</p>
<p>Prices in Pin copy match the live shop as of 12 Nov 2026. The Everything
Bundle is $59 (not $99). Copy does not say “lifetime updates”.</p>
<p><a href="/">Home</a> · <a href="/free/">Free tools</a> · <a href="/tools/">Tools</a> ·
<a href="/books/">Books</a> · <a href="/guides/">Guides</a></p>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == html:
        return
    path.write_text(html, encoding="utf-8")


def image_sizes(root: Path, items: list[dict]) -> dict[str, int]:
    sizes = {}
    for r in items:
        rel = r.get("image_file") or ""
        p = root / rel
        if p.is_file():
            sizes[rel] = p.stat().st_size
    return sizes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=None, help="Site repo root")
    ap.add_argument("--as-of", dest="as_of", default=None, help="YYYY-MM-DD override for 'today' (Riyadh)")
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args(argv)

    if args.root:
        root = Path(args.root).resolve()
    else:
        # Prefer the directory that already has pinterest/schedule.csv
        here = Path(__file__).resolve()
        root = None
        for cand in [Path.cwd(), here.parent.parent.parent, here.parent.parent, here.parent]:
            if (cand / "pinterest" / "schedule.csv").is_file():
                root = cand
                break
        if root is None:
            sys.exit("Cannot find pinterest/schedule.csv — pass --root")

    today = today_riyadh(args.as_of)
    boards = load_boards(root)
    rows = load_schedule(root)
    all_items = items_for_today(rows, today)

    if not rows:
        sys.exit("Empty schedule")

    dates = [r["date"] for r in rows]
    meta = {"start": min(dates), "end": max(dates), "rows": len(rows)}

    # Group by rss_board (exact Pinterest name).
    name_to_board = {b["name"]: b for b in boards}
    grouped: dict[str, list[dict]] = defaultdict(list)
    unknown = set()
    for r in all_items:
        name = (r.get("rss_board") or r.get("board") or "").strip()
        if name not in name_to_board:
            unknown.add(name)
            continue
        grouped[name].append(r)
    if unknown:
        print("WARNING: items on unknown boards (skipped):", sorted(unknown), file=sys.stderr)

    feeds_dir = root / "feeds"
    feeds_dir.mkdir(parents=True, exist_ok=True)

    sizes = image_sizes(root, all_items)
    counts = {}
    changed = 0
    problems = []
    for b in boards:
        items = latest_n(grouped.get(b["name"], []))
        counts[b["slug"]] = len(items)
        path = feeds_dir / f"{b['slug']}.xml"
        if not args.validate_only:
            status = write_feed(path, b, items, sizes)
            if status == "written":
                changed += 1
        if path.exists():
            problems.extend(validate_xml(path))

    if not args.validate_only:
        write_index(feeds_dir / "index.html", boards, counts, today, meta)
        # A small machine-readable summary, also deterministic.
        summary = {
            "today_riyadh": today.isoformat(),
            "feed_limit": FEED_LIMIT,
            "schedule": meta,
            "feeds": {
                b["slug"]: {
                    "board": b["name"],
                    "exists": b.get("exists"),
                    "create_first": bool(b.get("create_first")),
                    "items_in_feed": counts.get(b["slug"], 0),
                    "url": f"{SITE}/feeds/{b['slug']}.xml",
                }
                for b in boards
            },
        }
        summary_path = feeds_dir / "status.json"
        text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        if not summary_path.exists() or summary_path.read_text(encoding="utf-8") != text:
            summary_path.write_text(text, encoding="utf-8")
            changed += 1

    print(f"today (Asia/Riyadh): {today.isoformat()}")
    print(f"schedule rows: {len(rows)}  eligible up to today: {len(all_items)}")
    print(f"feeds written or updated: {changed}")
    for b in boards:
        print(f"  {counts.get(b['slug'],0):3d}  {b['slug']}  ({b['name']})"
              + ("" if b.get("exists") else "  [CREATE BOARD FIRST]"))
    if problems:
        print("VALIDATION ISSUES:")
        for p in problems:
            print(" -", p)
        return 1
    print("VALIDATION: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
