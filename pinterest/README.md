# Pinterest RSS autopilot (Nov 2026 – Dec 2028, then yearly cycle)

This is the mechanism that keeps Pins publishing after any assistant
subscription ends. It uses **Pinterest’s official, free RSS auto-publish**
([help article](https://help.pinterest.com/en/business/article/auto-publish-pins-from-your-rss-feed)):
one RSS 2.0 feed per board, connected once under
Settings → Create Pins in bulk → Auto-publish → Connect RSS feed.

A GitHub Action (`Pinterest RSS daily`) regenerates the feeds every day
at 08:00 UTC (11:00 Asia/Riyadh). Each feed exposes only items whose
date is on or before today (Asia/Riyadh), the latest 25, oldest first.
Pinterest creates Pins from new items within 24 hours, oldest first, with
a 200-Pin daily cap across all feeds. This plan is 2–3 Pins a day.

No paid scheduler, no Pinterest API token, no secrets. The Action uses
the repo’s `GITHUB_TOKEN`.

## What you have to do (once)

1. On a **desktop** browser, signed in as **abak1694** (business account).
2. **Claim** the website `https://dohmnsama1-sketch.github.io` if it is
   not already claimed (Settings → Claimed accounts). Pinterest will
   reject the feeds until the item links are on a claimed domain. The
   feeds only link to this domain (never Gumroad).
3. Create two boards if they still do not exist, with these exact names:
   - **Saudi Freelancer & VAT Tools**
   - **Large Print Puzzle Books**
4. Settings → Create Pins in bulk → Auto-publish → Connect RSS feed.
   Paste each URL below, select the matching board, Save.

After that, nothing else is required. New Pins appear on their scheduled
day, including after this assistant stops running.

## Exact board-to-feed mapping

Use the **exact** board name in the second column. Do **not** select
“Freelance Pricing & Profit Tips” — that board does not exist. The live
board is **Freelancer Profit & Scope Management**.

| Connect this feed | to this exact board | Board on the account? |
|---|---|---|
| https://dohmnsama1-sketch.github.io/feeds/freelance-client-tracker-crm.xml | Freelance Client Tracker & CRM | Yes (posted-log) |
| https://dohmnsama1-sketch.github.io/feeds/freelance-business-systems-templates.xml | Freelance Business Systems & Templates | Yes (posted-log) |
| https://dohmnsama1-sketch.github.io/feeds/freelancer-budget-irregular-income.xml | Freelancer Budget & Irregular Income | Yes (posted-log) |
| https://dohmnsama1-sketch.github.io/feeds/free-templates-spreadsheets.xml | Free Templates & Spreadsheets | Yes (posted-log) |
| https://dohmnsama1-sketch.github.io/feeds/ai-productivity-tools.xml | AI Productivity Tools | Yes (posted-log) |
| https://dohmnsama1-sketch.github.io/feeds/chatgpt-prompts-freelancers-sellers.xml | ChatGPT Prompts for Freelancers & Sellers | Yes (posted-log) |
| https://dohmnsama1-sketch.github.io/feeds/etsy-shopify-marketing-calendar.xml | Etsy & Shopify Marketing Calendar | Yes (posted-log) |
| https://dohmnsama1-sketch.github.io/feeds/job-search-tips-application-tracker.xml | Job Search Tips & Application Tracker | Yes (posted-log) |
| https://dohmnsama1-sketch.github.io/feeds/habit-tracker-ideas.xml | Habit Tracker Ideas | Yes (posted-log) |
| https://dohmnsama1-sketch.github.io/feeds/freelancer-profit-scope-management.xml | Freelancer Profit & Scope Management | Yes (posted-log). Not “Freelance Pricing & Profit Tips”. |
| https://dohmnsama1-sketch.github.io/feeds/pricing-handmade-items-etsy-tips.xml | Pricing Handmade Items & Etsy Tips | Yes (posted-log) |
| https://dohmnsama1-sketch.github.io/feeds/saudi-freelancer-vat-tools.xml | Saudi Freelancer & VAT Tools | **Create first**, then connect |
| https://dohmnsama1-sketch.github.io/feeds/large-print-puzzle-books.xml | Large Print Puzzle Books | **Create first**, then connect |

Three existing boards have **no on-domain product page** (their listings
are Gumroad-only, and Pinterest rejects off-domain item links). Do not
connect these; the feeds exist but stay empty: **Airbnb Host Tips &
Cleaning Checklists** (StayReady), **Home Organization & Inventory**
(HomeVault), **Content Creator Systems** (Content Repurposing Planner).
A live page on this site would be needed before those can auto-publish.

“Meal Planning & Pantry Organization” is also treated as missing; any
PantryPilot row is excluded from RSS for the same off-domain reason.

A human-readable index of the same mapping lives at
https://dohmnsama1-sketch.github.io/feeds/

## Schedule and images

- Plan file: `pinterest/schedule.csv` (dated items 12 Nov 2026 – 31 Dec 2028).
- Images: `pins/pinterest/{pin_id}.jpg`, 1000×1500, roughly 150–250 KB.
- Year 2 (13 Nov 2027 onward) uses the same renderer with a shifted
  theme and a different screenshot/cover so Pins are not pixel-identical
  to year 1. Titles are unique. Seasonal windows cover Ramadan (expected
  8 Feb 2027 and 28 Jan 2028, moon sighting), Christmas through
  mid-December, New Year, VAT quarterly deadlines (31 Jan / 30 Apr /
  31 Jul / 31 Oct), back-to-school (mid-Jul to late Aug), Valentine’s,
  Mother’s Day and Black Friday.
- The 2027 Etsy content calendar is not promoted as a 2028 edition; from
  1 Jan 2028 those slots move to other live products.
- Every item link is on this site (`/free/`, `/tools/`, `/books/`,
  `/guides/…`), with `utm_source=pinterest&utm_medium=rss` before any
  hash. All of those paths returned HTTP 200 when the plan was built.
- Copy is honest: “Free” only for free tools or book sample pages; the
  Command Center pin says it is the free demo, not the full paid app;
  VAT pins say “not tax advice”. The Everything Bundle is $59, not $99,
  and is not mentioned as “lifetime updates”. HomeVault, PantryPilot and
  StayReady are omitted from RSS because they have no page on this
  domain.

After 31 Dec 2028 the generator re-issues earlier items on the same
month-and-day two years later, with a new guid and a “— Month Year”
title suffix, so the feeds (and the daily commit) keep moving with no
further work. Product facts are not rewritten (a “2027 content calendar”
stays a 2027 content calendar).

## Why the Action keeps running (60-day GitHub rule)

GitHub automatically disables **scheduled** workflows on a public
repository after 60 days with no repository activity:

https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-a-workflow

A successful cron run is **not** activity. A **commit on the default
branch (`main`)** is. This workflow has `permissions: contents: write`
and, when a feed changes, commits and pushes with `GITHUB_TOKEN` as
`github-actions[bot]`. Because a new item enters a feed every planned
day, that commit is expected daily. Community confirmation that a bot
commit on the default branch resets the timer is widely used (e.g. the
keepalive-workflow pattern); this repo relies on a *real* content
commit, not an empty keepalive. The commit is only created when the
feed output actually changes (`lastBuildDate` is derived from the
latest item, not the clock).

If Actions were ever disabled, re-enable the workflow once in the
Actions tab; the next daily commit will keep it on.

The weekly IndexNow workflow on this repo does not write a commit, so
it cannot keep the timer running on its own.

## Regenerating feeds locally

```
python3 .github/scripts/generate_pinterest_feeds.py --as-of 2026-11-12
python3 .github/scripts/generate_pinterest_feeds.py --validate-only
```

`--as-of` is the Asia/Riyadh calendar date used as “today”.
