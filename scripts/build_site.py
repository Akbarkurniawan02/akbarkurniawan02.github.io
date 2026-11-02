"""Build the TechRooz website (https://techrooz.github.io) from posts already on the channel.

Usage: python3 scripts/build_site.py <queue.json> <site_dir>
Only posted items are published. Pages: home, one page per category, one page per
post, search (client-side over posts.json), sitemap. No secrets, no forms, no logins.
"""
import html, json, os, re, sys
from datetime import datetime, timedelta, timezone

SITE_URL = "https://techrooz.github.io"
CHANNEL = "https://t.me/techrooz_fa"
ADMIN_TG = "mohammadsafari2222"
EMAIL = "mohammadsfh11@gmail.com"
TEH = timezone(timedelta(hours=3, minutes=30))

# key, name, emoji, accent colour, hashtags that map to it
CATS = [
    ("news", "اخبار", "🔥", "#ff3b5c", ["#خبر"]),
    ("games", "گیم", "🎮", "#7c5cff", ["#گیم", "#بازی"]),
    ("ai", "هوش مصنوعی", "🤖", "#00c2ff", ["#هوش_مصنوعی", "#ابزار_روز", "#آموزش", "#درآمد_با_AI"]),
    ("mobile", "موبایل و گجت", "📱", "#ff8a00", ["#موبایل", "#گجت", "#ترفند"]),
    ("stories", "داستان برندها", "📖", "#e3b341", ["#داستان_برندها", "#داستان"]),
    ("viral", "جالب", "🎬", "#ff4fd8", ["#جالب", "#ویدیو"]),
    ("iran", "تک ایران", "🇮🇷", "#22c55e", ["#ایران", "#تک_ایران"]),
    ("free", "رایگان", "🆓", "#14b8a6", ["#رایگان"]),
    ("prompts", "پرامپت", "✍️", "#f59e0b", ["#پرامپت"]),
    ("nostalgia", "نوستالژی", "📼", "#a3a3a3", ["#نوستالژی"]),
    ("digest", "خلاصه روز", "🗞", "#94a3b8", ["#خلاصه_روز"]),
]
CAT = {c[0]: c for c in CATS}
MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
ALLOWED = re.compile(r"</?(b|i|code)>")
E = lambda t: html.escape(str(t), quote=True)


def fa(t):
    return str(t).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def jalali(d, with_time=True):
    gy, gm, gd = d.year, d.month, d.day
    g = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g[gm - 1]
    jy = -1595 + 33 * (days // 12053); days %= 12053
    jy += 4 * (days // 1461); days %= 1461
    if days > 365:
        jy += (days - 1) // 365; days = (days - 1) % 365
    jm = 1 + days // 31 if days < 186 else 7 + (days - 186) // 30
    jd = 1 + (days % 31 if days < 186 else (days - 186) % 30)
    return fa(f"{jd} {MONTHS[jm - 1]} {jy}" + (f" · {d:%H:%M}" if with_time else ""))


def strip_sig(c):
    return re.sub(r"\n*(📲 @techrooz_fa|⚡ تک‌روز \| @techrooz_fa)\s*$", "", c.strip())


def clean(caption):
    parts, last = [], 0
    for m in ALLOWED.finditer(caption):
        parts += [html.escape(caption[last:m.start()], quote=False), m.group(0)]
        last = m.end()
    parts.append(html.escape(caption[last:], quote=False))
    return "".join(parts).strip().replace("\n", "<br>")


def plain(c):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()


def title_of(c):
    m = re.search(r"<b>(.*?)</b>", c)
    return plain(m.group(1) if m else c.split("\n")[0])


def body_of(c):
    lines = strip_sig(c).split("\n")
    return "\n".join(lines[1:]).strip() if re.search(r"<b>", lines[0]) else "\n".join(lines)


def cat_of(item):
    if item.get("cat") in CAT:
        return item["cat"]
    for key, *_, tags in CATS:
        if any(t in item["caption"] for t in tags):
            return key
    t = title_of(item["caption"])
    for word, key in [("پرامپت", "prompts"), ("بازی", "games"), ("گیم", "games"), ("ابزار", "ai"), ("آموزش", "ai"),
                      ("هوش مصنوعی", "ai"), ("گوشی", "mobile"), ("ترفند", "mobile"), ("دانستنی", "viral"), ("درآمد", "ai")]:
        if word in t:
            return key
    return "news"


CSS = """:root{--bg:#fff;--bg2:#f5f5f7;--text:#1d1d1f;--muted:#6e6e73;--line:#d2d2d7;--link:#0066cc;--card:#fff}
@media (prefers-color-scheme: dark){:root{--bg:#000;--bg2:#161617;--text:#f5f5f7;--muted:#a1a1a6;--line:#38383a;--link:#2997ff;--card:#1c1c1e}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font-family:Vazirmatn,-apple-system,sans-serif;line-height:1.8;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}img{display:block;max-width:100%}
.wrap{max-width:1024px;margin:0 auto;padding:0 22px}
.top{position:sticky;top:0;z-index:30;background:color-mix(in srgb,var(--bg) 80%,transparent);backdrop-filter:saturate(180%) blur(20px);border-bottom:1px solid color-mix(in srgb,var(--line) 60%,transparent)}
.bar{display:flex;align-items:center;gap:18px;height:48px;font-size:13px}
.logo{font-size:17px;font-weight:700;white-space:nowrap}.logo span{color:inherit}
.date{display:none}.sp{flex:1}
.icon{color:var(--muted)}.tg{color:var(--link);white-space:nowrap}
nav.cats{display:flex;gap:22px;overflow-x:auto;scrollbar-width:none;height:40px;align-items:center;font-size:13px;border-top:1px solid color-mix(in srgb,var(--line) 40%,transparent)}
nav.cats::-webkit-scrollbar{display:none}nav.cats a{white-space:nowrap;color:var(--muted)}nav.cats a:hover,nav.cats a.on{color:var(--text)}
.ticker{display:none}
.intro{text-align:center;padding:64px 0 28px}.intro h1{font-size:48px;line-height:1.3;margin:0;font-weight:700;letter-spacing:-.5px}
.intro p{font-size:21px;color:var(--muted);margin:10px 0 18px}.intro a{color:var(--link);font-size:17px}
.lead{display:grid;gap:12px;margin:0 0 12px}
.big,.side a{position:relative;display:block;border-radius:18px;overflow:hidden;background:var(--bg2)}
.big{text-align:center;padding:44px 24px 24px;display:flex;flex-direction:column-reverse}.big img{width:100%;max-height:430px;object-fit:cover;border-radius:12px;margin-top:22px}
.big .over,.side .over{position:static;padding:0;color:inherit}
.big h2{font-size:34px;line-height:1.45;margin:6px 0 0;font-weight:700}
.side{display:grid;grid-template-columns:1fr 1fr;gap:12px}.side a{text-align:center;padding:32px 20px 20px;display:flex;flex-direction:column-reverse}
.side img{width:100%;height:220px;object-fit:cover;border-radius:12px;margin-top:18px}.side h3{font-size:22px;line-height:1.5;margin:6px 0 0;font-weight:700}
.big:after,.side a:after{display:none}
.kicker{font-size:13px;color:var(--muted);font-weight:600}.over .kicker{background:none;color:var(--muted);padding:0}
.noimg{display:block;font-size:0}.noimg.big,.side a.noimg{padding-bottom:40px}
.sec{display:flex;align-items:baseline;justify-content:space-between;margin:56px 0 18px}
.sec h2{margin:0;font-size:28px;font-weight:700}.sec a{color:var(--link);font-size:15px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
.card{display:flex;flex-direction:column;gap:10px;background:var(--card);border-radius:18px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);transition:transform .25s,box-shadow .25s}
.card:hover{transform:scale(1.015);box-shadow:0 8px 28px rgba(0,0,0,.1)}
.card .ph{aspect-ratio:16/10;background:var(--bg2);overflow:hidden}.card .ph img{width:100%;height:100%;object-fit:cover}
.card .ph.noimg{display:grid;place-items:center;font-size:44px;background:var(--bg2)!important}
.card>div:last-child{padding:4px 18px 18px}.card h3{margin:2px 0 6px;font-size:17px;line-height:1.65;font-weight:700}
.time{font-size:12px;color:var(--muted)}
.join{margin:60px 0;text-align:center;background:var(--bg2);border-radius:18px;padding:44px 22px}
.join h2{margin:0;font-size:30px;font-weight:700}.join p{margin:8px 0 18px;color:var(--muted);font-size:17px}
.join a{display:inline-block;background:var(--link);color:#fff;padding:12px 26px;border-radius:999px;font-size:16px}
article.post{max-width:680px;margin:48px auto}
article.post h1{font-size:38px;line-height:1.45;margin:8px 0 10px;font-weight:700;letter-spacing:-.3px}
article.post .cover{border-radius:18px;margin:26px 0;width:100%}
.body{font-size:18px;line-height:2.1}
code{display:block;white-space:pre-wrap;background:var(--bg2);padding:16px;border-radius:14px;font-family:inherit;font-size:15px}
.btn{display:inline-block;border:0;background:var(--bg2);color:var(--text);font:inherit;font-size:14px;padding:9px 16px;border-radius:999px;cursor:pointer;margin:8px 0 0 6px}
.btn.copy{background:var(--link);color:#fff}
.src{color:var(--muted);font-size:14px;margin-top:16px}.src a{color:var(--link)}
.search{width:100%;padding:14px 20px;border-radius:14px;border:1px solid var(--line);background:var(--bg2);color:var(--text);font:inherit;font-size:17px;margin:36px 0}
.empty{color:var(--muted);text-align:center;padding:48px}
footer{background:var(--bg2);margin-top:60px;padding:22px 0;color:var(--muted);font-size:12px}
footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px}footer a{color:var(--link)}
.mbar{display:none}
@media (max-width:820px){.grid{grid-template-columns:1fr 1fr}.side{grid-template-columns:1fr}.intro h1{font-size:36px}.big h2{font-size:26px}}
@media (max-width:560px){.grid{grid-template-columns:1fr}.intro{padding:40px 0 18px}.intro h1{font-size:30px}.intro p{font-size:17px}
.big{padding:30px 18px 0}.big h2{font-size:22px}.side h3{font-size:19px}article.post h1{font-size:27px}.sec h2{font-size:23px}
.mbar{display:block;position:fixed;bottom:14px;left:50%;transform:translateX(-50%);z-index:40;background:var(--link);color:#fff;padding:12px 22px;border-radius:999px;font-size:15px;white-space:nowrap;box-shadow:0 8px 24px rgba(0,0,0,.2)}body{padding-bottom:70px}}"""

HEAD = """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#ffffff">
<title>{title}</title><meta name="description" content="{desc}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">{og}
<link rel="canonical" href="{url}"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}style.css"></head><body>"""


def header(root, on, today):
    cats = "".join(f'<a href="{root}c/{k}.html"' + (' class="on"' if k == on else "") + f">{n}</a>" for k, n, e, *_ in CATS)
    return (f'<header class="top"><div class="wrap"><div class="bar"><a class="logo" href="{root}index.html">تک‌روز</a>'
            f'<span class="date">{today}</span><span class="sp"></span><a class="icon" href="{root}search.html" aria-label="جست‌وجو">🔍</a>'
            f'<a class="tg" href="{CHANNEL}">کانال تلگرام ↖</a></div><nav class="cats">{cats}</nav></div></header>')


FOOT = f"""<footer><div class="wrap"><div>⚡ تک‌روز · همه‌ی دنیای تکنولوژی، به زبون ساده</div>
<div>📩 تبلیغات و ارتباط: <a href="https://t.me/{ADMIN_TG}">@{ADMIN_TG}</a> · <a href="mailto:{EMAIL}">{EMAIL}</a></div>
<div>📲 <a href="{CHANNEL}">@techrooz_fa</a></div></div></footer>
<a class="mbar" href="{CHANNEL}">عضویت در کانال تلگرام</a>
<script>
document.querySelectorAll('code').forEach(c=>{{const b=document.createElement('button');b.className='btn copy';b.textContent='📋 کپی';
b.onclick=()=>navigator.clipboard.writeText(c.innerText).then(()=>b.textContent='✅ کپی شد');c.after(b)}});
const cl=document.querySelector('.copylink');if(cl)cl.onclick=()=>navigator.clipboard.writeText(location.href).then(()=>cl.textContent='✅ کپی شد');
</script></body></html>"""

JOIN = f"""<section class="join"><h2>هر روز، داغ‌ترین‌ها.</h2><p>گیم، هوش مصنوعی، گجت و داستان‌های عجیب تکنولوژی.</p>
<a href="{CHANNEL}">عضویت رایگان</a></section>"""


def media(p, root, cls=""):
    k = p["cat"]
    if p.get("photo"):
        return f'<img src="{E(p["photo"])}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display=\'none\'">'
    return ""


def card(p, root):
    k, n, e, c, _ = CAT[p["cat"]]
    ph = f'<div class="ph">{media(p, root)}</div>' if p.get("photo") else f'<div class="ph noimg" style="--c:{c}">{e}</div>'
    return (f'<a class="card" href="{root}p/{p["slug"]}.html" style="--c:{c}">{ph}<div><div class="kicker">{n}</div>'
            f'<h3>{E(p["title"])}</h3><div class="time">{p["date"]}</div></div></a>')


def overlay(p, root, cls, tag):
    k, n, e, c, _ = CAT[p["cat"]]
    img = media(p, root) if p.get("photo") else ""
    extra = "" if img else " noimg"
    inner = "" if img else e
    return (f'<a class="{cls}{extra}" href="{root}p/{p["slug"]}.html" style="--c:{c}">{img}{inner}<div class="over">'
            f'<span class="kicker">{n}</span><{tag}>{E(p["title"])}</{tag}></div></a>')


def page(title, desc, url, root, on, today, body, og=""):
    return HEAD.format(title=E(title), desc=E(desc), url=url, root=root, og=og) + header(root, on, today) + body + FOOT


def main(queue_path, site):
    for d in ("p", "c"):
        os.makedirs(os.path.join(site, d), exist_ok=True)
    posts = []
    for it in json.load(open(queue_path, encoding="utf-8")):
        if not it.get("posted"):
            continue
        d = datetime.fromisoformat(it["at"].replace("Z", "+00:00")).astimezone(TEH)
        photo = it.get("photo") or (it.get("photos") or [""])[0]
        posts.append({"at": it["at"], "slug": d.strftime("%Y%m%d-%H%M"), "date": jalali(d), "photo": photo,
                      "caption": it["caption"], "source": it.get("source", ""), "cat": cat_of(it),
                      "title": title_of(it["caption"])})
    posts.sort(key=lambda p: p["at"], reverse=True)
    today = jalali(datetime.now(TEH), False)
    open(os.path.join(site, "style.css"), "w").write(CSS)
    json.dump([{k: p[k] for k in ("slug", "title", "date", "cat", "photo")} for p in posts],
              open(os.path.join(site, "posts.json"), "w", encoding="utf-8"), ensure_ascii=False)

    for p in posts:
        k, n, e, c, _ = CAT[p["cat"]]
        og = f'<meta property="og:image" content="{E(p["photo"])}">' if p["photo"] else ""
        cover = f'<img class="cover" src="{E(p["photo"])}" alt="" referrerpolicy="no-referrer" onerror="this.remove()">' if p["photo"] else ""
        src = f'<div class="src">منبع: <a href="{E(p["source"])}" rel="nofollow noopener">{E(p["source"].split("/")[2])}</a></div>' if p["source"].startswith("http") else ""
        rel = [q for q in posts if q is not p and q["cat"] == p["cat"]][:4] or [q for q in posts if q is not p][:4]
        body = (f'<main class="wrap"><article class="post" style="--c:{c}"><div class="kicker">{e} {n}</div><h1>{E(p["title"])}</h1>'
                f'<div class="time">{p["date"]}</div>{cover}<div class="body">{clean(body_of(p["caption"]))}</div>{src}'
                f'<div><a class="btn" href="https://t.me/share/url?url={SITE_URL}/p/{p["slug"]}.html">📤 ارسال در تلگرام</a>'
                f'<button class="btn copylink">🔗 کپی لینک</button></div></article>{JOIN}'
                f'<div class="sec"><h2>بیشتر از {n}</h2><a href="../c/{k}.html">همه ←</a></div><div class="grid">'
                + "".join(card(q, "../") for q in rel) + "</div></main>")
        open(os.path.join(site, "p", p["slug"] + ".html"), "w", encoding="utf-8").write(
            page(p["title"] + " | تک‌روز", plain(body_of(p["caption"]))[:155], f"{SITE_URL}/p/{p['slug']}.html", "../", k, today, body, og))

    for k, n, e, c, _ in CATS:
        group = [p for p in posts if p["cat"] == k]
        inner = "".join(card(p, "../") for p in group) or '<div class="empty">به‌زودی مطالب این بخش اینجا میاد 👀</div>'
        body = f'<main class="wrap"><div class="sec" style="--c:{c}"><h2>{e} {n}</h2><span class="time">{fa(len(group))} مطلب</span></div><div class="grid">{inner}</div>{JOIN}</main>'
        open(os.path.join(site, "c", k + ".html"), "w", encoding="utf-8").write(
            page(f"{n} | تک‌روز", f"جدیدترین مطالب {n} در تک‌روز", f"{SITE_URL}/c/{k}.html", "../", k, today, body))

    with_img = [p for p in posts if p["photo"]] or posts
    lead = ""
    if posts:
        main_p = with_img[0]
        sides = [p for p in with_img[1:3]] or [p for p in posts if p is not main_p][:2]
        lead = ('<section class="lead">' + overlay(main_p, "", "big", "h2") + '<div class="side">'
                + "".join(overlay(p, "", "", "h3") for p in sides) + "</div></section>")
    shown = {p["slug"] for p in [] }
    tick = " ".join(f'<span><b>{CAT[p["cat"]][2]}</b> {E(p["title"])}</span>' for p in posts[:8])
    intro = ('<section class="intro"><h1>تک‌روز</h1><p>همه‌ی دنیای تکنولوژی، به زبون ساده.</p>'
             f'<a href="{CHANNEL}">عضویت در کانال تلگرام ‹</a></section>')
    body = f'<div class="wrap">{intro}{lead}'
    body += '<div class="sec"><h2>تازه‌ترین‌ها</h2><a href="search.html">همه‌ی مطالب ←</a></div><div class="grid">' + "".join(card(p, "") for p in posts[:8]) + "</div>" + JOIN
    for k, n, e, c, _ in CATS:
        group = [p for p in posts if p["cat"] == k][:4]
        if group:
            body += f'<div class="sec"><h2>{e} {n}</h2><a href="c/{k}.html">همه ←</a></div><div class="grid">' + "".join(card(p, "") for p in group) + "</div>"
    body += "</div>"
    open(os.path.join(site, "index.html"), "w", encoding="utf-8").write(
        page("تک‌روز | اخبار تکنولوژی، گیم و هوش مصنوعی به فارسی", "گیم، هوش مصنوعی، موبایل و داستان‌های عجیب تکنولوژی؛ کوتاه و به زبون ساده.",
             SITE_URL + "/", "", "", today, body))

    search = ('<main class="wrap"><input class="search" type="search" placeholder="🔍 دنبال چی می‌گردی؟ (مثلاً: بازی، ChatGPT، گوشی)" autofocus>'
              '<div class="grid" id="res"></div><div class="empty" id="none" hidden>چیزی پیدا نشد 🤷</div></main>'
              '<script>const C=' + json.dumps({k: [n, e, c] for k, n, e, c, _ in CATS}, ensure_ascii=False) + ''';
fetch('posts.json').then(r=>r.json()).then(P=>{const q=document.querySelector('.search'),R=document.getElementById('res'),N=document.getElementById('none');
const esc=s=>s.replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
function show(){const t=q.value.trim();const L=P.filter(p=>!t||p.title.includes(t));N.hidden=L.length>0;
R.innerHTML=L.map(p=>{const c=C[p.cat];return `<a class="card" href="p/${p.slug}.html" style="--c:${c[2]}"><div class="ph${p.photo?'':' noimg'}">${p.photo?`<img src="${esc(p.photo)}" alt="" loading="lazy" referrerpolicy="no-referrer">`:c[1]}</div><div><div class="kicker">${c[0]}</div><h3>${esc(p.title)}</h3><div class="time">${p.date}</div></div></a>`}).join('')}
q.oninput=show;show()});</script>''')
    open(os.path.join(site, "search.html"), "w", encoding="utf-8").write(
        page("جست‌وجو | تک‌روز", "جست‌وجو در مطالب تک‌روز", SITE_URL + "/search.html", "", "", today, search))

    urls = [SITE_URL + "/", SITE_URL + "/search.html"] + [f"{SITE_URL}/c/{k}.html" for k, *_ in CATS] + [f"{SITE_URL}/p/{p['slug']}.html" for p in posts]
    open(os.path.join(site, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                                       + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    open(os.path.join(site, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    print(len(posts), "posts")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
