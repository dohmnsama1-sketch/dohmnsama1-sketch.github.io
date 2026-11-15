#!/usr/bin/env python3
"""Build mobile-first product landing pages at /p/<key>/ from pinterest/products.json.

Each page shows, above the fold on a phone: the benefit headline, the price,
a Buy / Download button (Gumroad checkout) and the product cover image.
Incoming utm_* parameters (e.g. from Pinterest RSS pins) are copied onto the
Gumroad links so sales stay attributable. No third-party dependencies.

Run:  python .github/scripts/build_product_pages.py
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = "https://dohmnsama1-sketch.github.io"
GUM = "https://dodiabak.gumroad.com/l/"
FORBIDDEN = re.compile(r"lifetime|free updates?|forever", re.I)

CSS = """
:root{--ink:#14213d;--pri:#d9542b;--pri2:#0b7a5b;--mut:#5d6882;--line:#e6e8ef;--bg:#faf6f1}
*{box-sizing:border-box}body{margin:0;font:16px/1.6 system-ui,-apple-system,"Segoe UI",Tahoma,"Noto Sans Arabic",Arial,sans-serif;color:var(--ink);background:#fff;padding-bottom:84px}
a{color:var(--pri2)}.wrap{max-width:760px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid var(--line);padding:8px 0;font-size:13px}header .wrap{display:flex;justify-content:space-between;align-items:center}
header b{letter-spacing:.06em;text-transform:uppercase;font-size:12px}header a{text-decoration:none}
.kick{margin:14px 0 4px;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--pri)}
h1{font-size:25px;line-height:1.25;margin:0 0 8px}
.sub{margin:0 0 12px;color:var(--mut);font-size:15px}
.buy{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;margin:0 0 12px}
.price{font-size:24px;font-weight:800}.price s{color:var(--mut);font-weight:500;font-size:17px;margin-inline-end:6px}
.btn{display:inline-block;background:var(--pri);color:#fff;font-weight:800;font-size:17px;text-decoration:none;padding:13px 22px;border-radius:12px;box-shadow:0 3px 10px #d9542b44}
.btn.free{background:var(--pri2);box-shadow:0 3px 10px #0b7a5b44}
.fine{font-size:12.5px;color:var(--mut);margin:-4px 0 12px}
.cover{width:100%;height:auto;aspect-ratio:1005/565;border-radius:12px;border:1px solid var(--line);display:block;background:var(--bg)}
ul.b{padding:0;margin:16px 0;list-style:none}ul.b li{padding-block:6px;padding-inline:28px 0;position:relative;border-bottom:1px solid var(--line)}
ul.b li:before{content:"✓";position:absolute;inset-inline-start:4px;color:var(--pri2);font-weight:800}
.note{font-size:13px;color:var(--mut)}
.more{margin:22px 0;padding:14px;border-radius:12px;background:var(--bg)}.more h2{font-size:17px;margin:0 0 8px}
.card{display:flex;gap:12px;align-items:center;text-decoration:none;color:var(--ink);padding:8px 0;border-top:1px solid var(--line)}
.card img{width:110px;height:auto;border-radius:8px;flex:none}.card b{display:block;font-size:15px}.card span{font-size:13px;color:var(--mut)}
.sticky{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--line);padding:10px 16px;display:flex;gap:10px;align-items:center;justify-content:space-between;z-index:9}
.sticky span{font-size:14px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.sticky .btn{padding:10px 16px;font-size:15px;flex:none}
footer{margin-top:24px;padding:18px 0;background:var(--bg);font-size:13px;color:var(--mut)}
@media(min-width:760px){h1{font-size:32px}.sticky{display:none}body{padding-bottom:0}}
"""

JS = """<script>(function(){try{var q=new URLSearchParams(location.search),u={};['utm_source','utm_medium','utm_campaign','utm_content','utm_term'].forEach(function(k){if(q.get(k))u[k]=q.get(k)});if(!u.utm_source)return;document.querySelectorAll('a[data-g]').forEach(function(a){var x=new URL(a.href);Object.keys(u).forEach(function(k){x.searchParams.set(k,u[k])});a.href=x.toString()})}catch(e){}})();</script>"""


def e(s: str) -> str:
    return html.escape(s or "", quote=True)


def money(v: float) -> str:
    return f"${v:.0f}" if float(v).is_integer() else f"${v:.2f}"


def gum(p: dict, key: str, code: str | None, checkout: bool, medium: str = "landing") -> str:
    url = GUM + p["slug"]
    if code and p["price"] > 0:
        url += "/" + code
    q = f"utm_source=site&utm_medium={medium}&utm_campaign={key}"
    if checkout:
        q = "wanted=true&" + q
    return url + "?" + q


def build(data: dict) -> list[str]:
    code, pct = data["discount_code"], data["discount_pct"]
    prods = data["products"]
    out = []
    for key, p in prods.items():
        blob = json.dumps(p, ensure_ascii=False)
        if FORBIDDEN.search(blob):
            raise SystemExit(f"forbidden wording in {key}")
        ar = p.get("lang") == "ar"
        free = p["price"] == 0
        disc = round(p["price"] * (100 - pct) / 100, 2)
        img = f"/img/p/{p['img']}"
        url = f"{SITE}/p/{key}/"
        buy = gum(p, key, code, True)
        if free:
            kick = "مجاني" if ar else "Free download · Excel + Google Sheets" if "demo" not in key else "Free demo · works offline"
            price_html = f'<span class="price">{"مجاني" if ar else "Free"}</span>'
            btn = f'<a class="btn free" data-g href="{e(buy)}" rel="noopener">{"حمّل مجانًا" if ar else "Download free"}</a>'
            fine = "Gumroad asks for your email to send the file." if not ar else "يطلب Gumroad بريدك لإرسال الملف."
            sticky_btn = f'<a class="btn free" data-g href="{e(buy)}" rel="noopener">{"حمّل مجانًا" if ar else "Get it free"}</a>'
        else:
            kick = ("تحميل فوري · " if ar else "Instant download · ") + money(p["price"])
            price_html = f'<span class="price"><s>{money(p["price"])}</s>{money(disc)}</span>'
            label = f"اشترِ الآن" if ar else "Buy now"
            btn = f'<a class="btn" data-g href="{e(buy)}" rel="noopener">{label} – {money(disc)}</a>'
            fine = (f"الرمز {code} (خصم {pct}%) يُطبَّق تلقائيًا عبر هذا الزر. الدفع عبر Gumroad." if ar else
                    f"Code {code} ({pct}% off) is applied by this button. Secure checkout on Gumroad.")
            sticky_btn = f'<a class="btn" data-g href="{e(buy)}" rel="noopener">{label} – {money(disc)}</a>'
        bullets = "".join(f"<li>{e(b)}</li>" for b in p["bullets"])
        rel = ""
        for rk in p.get("related", []):
            r = prods.get(rk)
            if not r:
                continue
            rp = "Free" if r["price"] == 0 else f"{money(r['price'])} ({money(round(r['price']*(100-pct)/100,2))} with {code})"
            rel += (f'<a class="card" href="/p/{rk}/"><img src="/img/p/{r["img"]}" alt="" width="110" height="62" loading="lazy">'
                    f'<div><b>{e(r["name"])}</b><span>{e(rp)}</span></div></a>')
        more_h = ("خطوتك التالية" if ar else ("Next step after the free file" if free else "Also useful"))
        more = f'<div class="more"><h2>{more_h}</h2>{rel}</div>' if rel else ""
        details = gum(p, key, None, False, "landing-details")
        title = f"{p['name']} – {'Free' if free else money(p['price'])}"
        ld = {"@context": "https://schema.org", "@type": "Product", "name": p["name"], "image": SITE + img,
              "description": p["sub"], "brand": {"@type": "Brand", "name": "Solo & Co."},
              "offers": {"@type": "Offer", "price": f"{p['price']:.2f}", "priceCurrency": "USD",
                         "availability": "https://schema.org/InStock", "url": GUM + p["slug"]}}
        page = f"""<!doctype html>
<html lang="{'ar' if ar else 'en'}" dir="{'rtl' if ar else 'ltr'}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(p['sub'])}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="product"><meta property="og:site_name" content="Solo &amp; Co.">
<meta property="og:url" content="{url}"><meta property="og:title" content="{e(p['h1'])}">
<meta property="og:description" content="{e(p['sub'])}"><meta property="og:image" content="{SITE}{img}">
<meta property="product:price:amount" content="{p['price']:.2f}"><meta property="product:price:currency" content="USD">
<meta property="og:price:amount" content="{p['price']:.2f}"><meta property="og:price:currency" content="USD">
<meta property="og:availability" content="instock">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style>
</head><body>
<header><div class="wrap"><b>Solo &amp; Co. · Dodiabak</b><a href="/tools/">{'كل الأدوات' if ar else 'All tools'}</a></div></header>
<main class="wrap">
<p class="kick">{e(kick)}</p>
<h1>{e(p['h1'])}</h1>
<p class="sub">{e(p['sub'])}</p>
<div class="buy">{price_html}{btn}</div>
<p class="fine">{e(fine)}</p>
<a data-g href="{e(buy)}" rel="noopener"><img class="cover" src="{img}" alt="{e(p['name'])} preview" width="1005" height="565" fetchpriority="high"></a>
<ul class="b">{bullets}</ul>
<p class="note">{e(p['note'])} <a data-g href="{e(details)}" rel="noopener">{'التفاصيل الكاملة على Gumroad' if ar else 'Full details on Gumroad'}</a></p>
{more}
</main>
<div class="sticky"><span>{e(p['name'])}</span>{sticky_btn}</div>
<footer><div class="wrap"><a href="/tools/">Tools</a> · <a href="/free/">Free</a> · <a href="/books/">Books</a> · <a href="/guides/">Guides</a> · Solo &amp; Co. Files you download and fill in; not tax, legal or financial advice.</div></footer>
{JS}
</body></html>
"""
        d = ROOT / "p" / key
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page, encoding="utf-8")
        out.append(key)
    return out


GRID_ORDER = ["demo", "budget-lite", "rate", "maker", "vat-free", "habit", "job", "toolkit", "prompts",
              "calendar", "budget-full", "crm", "crm-ar", "vat-books", "fcc", "mega", "homevault", "pantry", "stayready"]


def tools_grid(data: dict) -> None:
    """Insert/refresh a picture grid of every product at the top of /tools/."""
    prods, pct, code = data["products"], data["discount_pct"], data["discount_code"]
    cards = []
    for k in GRID_ORDER:
        p = prods[k]
        pr = "Free" if p["price"] == 0 else f"{money(p['price'])} · {money(round(p['price']*(100-pct)/100,2))} with {code}"
        cards.append(f'<a href="/p/{k}/" style="display:block;text-decoration:none;color:inherit;border:1px solid #e3e7f0;border-radius:12px;overflow:hidden;background:#fff">'
                     f'<img src="/img/p/{p["img"]}" alt="" width="1005" height="565" loading="lazy" style="width:100%;height:auto;display:block">'
                     f'<span style="display:block;padding:8px 10px;font-size:14px;line-height:1.35"><b>{e(p["name"])}</b><br>'
                     f'<span style="color:{"#0b7a5b" if p["price"]==0 else "#d9542b"};font-weight:700">{e(pr)}</span></span></a>')
    block = ('<!--tool-grid--><section style="padding:18px 0"><div class="wrap"><h1 style="font-size:22px;line-height:1.3;margin:0 0 12px">Freelancer tools and templates: tap one for preview, price and download</h1>'
             '<div style="display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(160px,1fr))">' + "".join(cards) +
             '</div></div></section><!--/tool-grid-->')
    f = ROOT / "tools" / "index.html"
    t = f.read_text(encoding="utf-8")
    t = re.sub(r"<!--tool-grid-->.*?<!--/tool-grid-->\n?", "", t, flags=re.S)
    m = re.search(r"</nav>\n+", t)
    if not m:
        raise SystemExit("tools/index.html: </nav> not found")
    t = t[:m.start()] + "</nav>\n" + block + "\n\n" + t[m.end():]
    f.write_text(t, encoding="utf-8")


if __name__ == "__main__":
    data = json.loads((ROOT / "pinterest" / "products.json").read_text(encoding="utf-8"))
    keys = build(data)
    tools_grid(data)
    print("built", len(keys), "pages:", ", ".join(keys))
