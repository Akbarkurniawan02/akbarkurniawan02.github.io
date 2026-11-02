"""Build the public TechRooz website from posts that are already on the channel.

Usage: python3 scripts/build_site.py <queue.json> <site_dir>
Only posts marked "posted" are published, so the site never shows anything
that isn't already public on the channel. No secrets are ever written.
"""
import html, json, os, re, sys
from datetime import datetime, timedelta, timezone

SITE_URL = "https://techrooz.github.io"
CHANNEL = "https://t.me/techrooz_fa"
ADMIN_TG = "mohammadsafari2222"
EMAIL = "mohammadsfh11@gmail.com"
CONTACT = (f'<div class="box contact"><h4>📩 تماس و تبلیغات</h4>'
           f'<a href="https://t.me/{ADMIN_TG}">💬 تلگرام ادمین: @{ADMIN_TG}</a>'
           f'<a href="mailto:{EMAIL}">✉️ ایمیل: {EMAIL}</a>'
           f'<a href="{CHANNEL}">📲 کانال: @techrooz_fa</a></div>')
TEH = timezone(timedelta(hours=3, minutes=30))
ALLOWED = re.compile(r"</?(b|i|code)>")


MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]


def fa_digits(t):
    return str(t).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def jalali(d):
    """Gregorian datetime -> '۱۱ آبان ۱۴۰۵ · ۰۸:۰۰'."""
    gy, gm, gd = d.year, d.month, d.day
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    jm = 1 + days // 31 if days < 186 else 7 + (days - 186) // 30
    jd = 1 + (days % 31 if days < 186 else (days - 186) % 30)
    return fa_digits(f"{jd} {MONTHS[jm - 1]} {jy} · {d:%H:%M}")


def clean(caption):
    # keep only the simple tags Telegram posts use; escape everything else
    parts, last = [], 0
    for m in ALLOWED.finditer(caption):
        parts.append(html.escape(caption[last:m.start()], quote=False))
        parts.append(m.group(0))
        last = m.end()
    parts.append(html.escape(caption[last:], quote=False))
    body = "".join(parts).replace("📲 @techrooz_fa", "").replace("⚡ تک‌روز | @techrooz_fa", "").strip()
    return body.replace("\n", "<br>")


def title_of(caption):
    m = re.search(r"<b>(.*?)</b>", caption)
    return re.sub(r"<[^>]+>", "", m.group(1) if m else caption.split("\n")[0]).strip()


def plain(caption, n=155):
    t = re.sub(r"<[^>]+>", "", caption).replace("\n", " ")
    return re.sub(r"\s+", " ", t).strip()[:n]


CATS = [  # Tehran posting time -> category (matches the daily slot table)
    ("0800", "news", "خبر", "📰"), ("0930", "tools", "ابزار AI", "🤖"), ("1100", "tricks", "ترفند", "📱"),
    ("1230", "prompts", "پرامپت", "✍️"), ("1400", "gadgets", "گجت", "📲"), ("1530", "news", "خبر", "📰"),
    ("1700", "learn", "آموزش", "🎓"), ("1830", "apps", "سایت و اپ", "🌐"), ("2000", "money", "درآمد با AI", "💰"),
    ("2130", "fun", "دانستنی", "💡"),
]
NAV = [("news", "اخبار"), ("tools", "ابزار AI"), ("prompts", "پرامپت"), ("learn", "آموزش"), ("tricks", "ترفند"), ("money", "درآمد با AI")]


COLORS = {"news": "#e11d48", "tools": "#7c3aed", "tricks": "#0891b2", "prompts": "#d97706", "gadgets": "#2563eb",
          "learn": "#059669", "apps": "#0d9488", "money": "#16a34a", "fun": "#db2777"}


def cat_of(slug):
    hm = slug.split("-")[1]
    for t, key, name, emo in CATS:
        if t == hm:
            return key, name, emo
    return "news", "خبر", "📰"


def excerpt(caption, n=140):
    lines = [l for l in caption.split("\n") if l.strip()][1:]
    return plain("\n".join(lines), n)


CSS = """:root{--bg:#f3f4f8;--card:#fff;--text:#1a1d29;--muted:#6b7080;--line:#e6e8ef;--brand:#e11d48;--brand2:#7c3aed;--chip:#fde7ec}
@media (prefers-color-scheme: dark){:root{--bg:#0e1017;--card:#171a24;--text:#eceef5;--muted:#9097aa;--line:#262a38;--chip:#3a1622}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font-family:Shabnam,Tahoma,sans-serif;line-height:1.85;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:inherit;text-decoration:none}img{display:block;max-width:100%}
.top{position:sticky;top:0;z-index:9;background:var(--card);border-bottom:1px solid var(--line);box-shadow:0 2px 10px rgba(0,0,0,.04)}
.bar{max-width:1180px;margin:0 auto;padding:10px 16px;display:flex;align-items:center;gap:18px}
.logo{font-weight:700;font-size:24px;display:flex;align-items:center;gap:6px;white-space:nowrap}
.logo b{background:linear-gradient(135deg,var(--brand),var(--brand2));-webkit-background-clip:text;color:transparent}
nav{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;flex:1}nav::-webkit-scrollbar{display:none}
nav a{padding:6px 12px;border-radius:999px;font-size:14px;color:var(--muted);white-space:nowrap}
nav a:hover,nav a.on{background:var(--chip);color:var(--brand)}
.tg{background:var(--brand);color:#fff;font-weight:800;font-size:14px;padding:8px 16px;border-radius:999px;white-space:nowrap}
.wrap{max-width:1180px;margin:0 auto;padding:20px 16px}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:24px}.layout>*{min-width:0}
@media (max-width:900px){.layout{grid-template-columns:minmax(0,1fr)}.tg{display:none}.bar{gap:10px}}
.hero{position:relative;border-radius:20px;overflow:hidden;background:#111;min-height:360px;display:flex;align-items:flex-end;margin-bottom:24px}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.85}
.hero:after{content:"";position:absolute;inset:0;background:linear-gradient(rgba(0,0,0,.15),rgba(0,0,0,.92) 70%)}
.hero .in{position:relative;z-index:2;padding:24px;color:#fff}.hero h1{margin:8px 0;font-size:27px;line-height:1.6;font-weight:700}
.hero p{margin:0;opacity:.85}
.chip{display:inline-block;background:var(--chip);color:var(--brand);font-size:11.5px;font-weight:700;padding:3px 10px;border-radius:999px}
.hero .chip{background:var(--brand);color:#fff}
.sec{display:flex;align-items:center;justify-content:space-between;margin:8px 0 14px}
.sec h2{margin:0;font-size:20px;border-right:4px solid var(--brand);padding-right:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:18px}
.card{background:var(--card);border-radius:16px;overflow:hidden;border:1px solid var(--line);transition:transform .15s,box-shadow .15s;display:flex;flex-direction:column}
.card:hover{transform:translateY(-3px);box-shadow:0 10px 24px rgba(0,0,0,.08)}
.thumb{aspect-ratio:16/9;background:linear-gradient(135deg,var(--brand2),var(--brand));display:flex;align-items:center;justify-content:center;font-size:52px;overflow:hidden}
.thumb img{width:100%;height:100%;object-fit:cover}
.card .in{padding:14px}.card h3{margin:8px 0 6px;font-size:15.5px;line-height:1.75;font-weight:700}
.card p{margin:0;color:var(--muted);font-size:13px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.time{color:var(--muted);font-size:12px;margin-top:8px}
aside .box{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin-bottom:18px}
aside h4{margin:0 0 10px;font-size:16px}
.list a{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:14px}
.list a:last-child{border:0}.list span{color:var(--brand);font-weight:900;font-size:20px;min-width:24px}
aside .join,.band{background:linear-gradient(135deg,var(--brand),var(--brand2));color:#fff;text-align:center;border:0}
.join h4{font-size:18px}.join p{opacity:.9;font-size:14px;margin:0 0 12px}
.join a,.band a{display:inline-block;background:#fff;color:var(--brand);font-weight:900;padding:10px 22px;border-radius:999px}
article.post{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:24px}
.crumb{font-size:13px;color:var(--muted)}.crumb a{color:var(--brand)}
article.post h1{font-size:25px;line-height:1.7;margin:10px 0;font-weight:700}
article.post .cover{border-radius:14px;margin:16px 0;width:100%}
.body{font-size:16px;line-height:2.1;color:var(--text)}
code{display:block;white-space:pre-wrap;background:var(--bg);border:1px dashed var(--line);padding:12px;border-radius:12px;font-family:inherit;font-size:14.5px}
.src{margin-top:14px;font-size:13px;color:var(--muted)}.src a{color:var(--brand)}
.band{display:flex;align-items:center;justify-content:space-between;gap:12px;border-radius:16px;padding:14px 18px;margin:0 0 24px;text-align:right}
.band b{font-size:16px}.band a{white-space:nowrap}
@media (max-width:600px){.card{flex-direction:row}.thumb{width:120px;min-width:120px;aspect-ratio:auto;font-size:36px}
.card .in{padding:10px 12px}.card h3{font-size:14px;margin:4px 0}.card p{display:none}.hero{min-height:300px}.hero h1{font-size:21px}}
.contact a{display:block;padding:8px 0;border-bottom:1px solid var(--line);font-size:14px;color:var(--brand);overflow-wrap:anywhere}.contact a:last-child{border:0}
.card .chip{background:color-mix(in srgb,var(--c) 14%,transparent);color:var(--c)}
.card .thumb{background:linear-gradient(135deg,var(--c),var(--brand2))}
.intro{position:relative;overflow:hidden;border-radius:24px;padding:28px 22px;margin-bottom:22px;color:#fff;
background:radial-gradient(circle at 15% 20%,rgba(255,255,255,.18),transparent 40%),linear-gradient(135deg,#1e1b4b,#7c3aed 55%,#e11d48)}
.intro h1{margin:0 0 6px;font-size:30px;font-weight:700}.intro p{margin:0 0 16px;opacity:.9}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}.stats span{background:rgba(255,255,255,.14);padding:6px 12px;border-radius:999px;font-size:13px}
.intro .cta{display:inline-block;background:#fff;color:#7c3aed;font-weight:700;padding:11px 22px;border-radius:999px}
.search{width:100%;padding:12px 16px;border-radius:14px;border:1px solid var(--line);background:var(--card);color:var(--text);font:inherit;margin-bottom:18px}
.pills{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;margin-bottom:18px}.pills::-webkit-scrollbar{display:none}
.pills button{border:1px solid var(--line);background:var(--card);color:var(--text);font:inherit;font-size:14px;padding:7px 14px;border-radius:999px;white-space:nowrap;cursor:pointer}
.pills button.on{background:var(--brand);border-color:var(--brand);color:#fff}
.copy{display:inline-block;margin:8px 0;border:0;background:var(--brand2);color:#fff;font:inherit;font-size:13px;padding:6px 14px;border-radius:999px;cursor:pointer}
.share{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}.share a,.share button{border:1px solid var(--line);background:var(--bg);color:var(--text);font:inherit;font-size:13px;padding:7px 14px;border-radius:999px;cursor:pointer}
.mbar{display:none}
@media (max-width:900px){.mbar{display:flex;position:fixed;bottom:12px;left:12px;right:12px;z-index:20;justify-content:center;background:linear-gradient(135deg,var(--brand),var(--brand2));color:#fff;font-weight:700;padding:13px;border-radius:16px;box-shadow:0 10px 30px rgba(124,58,237,.45)}body{padding-bottom:70px}}
.empty{display:none;color:var(--muted);text-align:center;padding:30px}
footer{background:var(--card);border-top:1px solid var(--line);margin-top:30px}
footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;color:var(--muted);font-size:14px}
footer a{color:var(--brand)}"""

HEAD = """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">{og}
<link rel="canonical" href="{url}">
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@v5.0.1/dist/font-face.css" rel="stylesheet">
<link rel="stylesheet" href="{root}style.css"></head><body>"""


def topbar(root, on=""):
    links = "".join(f'<a href="{root}index.html?c={k}"' + (' class="on"' if k == on else "") + f">{n}</a>" for k, n in NAV)
    return (f'<header class="top"><div class="bar"><a class="logo" href="{root}index.html">⚡<b>تک‌روز</b></a>'
            f'<nav>{links}</nav><a class="tg" href="{CHANNEL}">📲 کانال تلگرام</a></div></header>')


JS = """<script>
document.querySelectorAll('code').forEach(c=>{const b=document.createElement('button');b.className='copy';b.textContent='📋 کپی پرامپت';
b.onclick=e=>{e.preventDefault();navigator.clipboard.writeText(c.innerText).then(()=>{b.textContent='✅ کپی شد'})};c.after(b)});
const q=document.querySelector('.search'),cards=[...document.querySelectorAll('.feed .card')],empty=document.querySelector('.empty');let cat='all';
function f(){let n=0;const t=(q?q.value:'').trim();cards.forEach(c=>{const ok=(cat=='all'||c.dataset.cat==cat)&&(!t||c.innerText.includes(t));c.style.display=ok?'':'none';n+=ok});if(empty)empty.style.display=n?'none':'block'}
if(q)q.oninput=f;document.querySelectorAll('.pills button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.pills button').forEach(x=>x.classList.remove('on'));b.classList.add('on');cat=b.dataset.cat;f()});
const pc=new URLSearchParams(location.search).get('c');if(pc){const b=document.querySelector(`.pills button[data-cat="${pc}"]`);if(b)b.click()}
const sh=document.querySelector('.copylink');if(sh)sh.onclick=()=>navigator.clipboard.writeText(location.href).then(()=>sh.textContent='✅ لینک کپی شد');
</script>"""

FOOT = f"""<a class="mbar" href="{CHANNEL}">📲 عضویت رایگان در کانال تلگرام تک‌روز</a><footer><div class="wrap"><div>⚡ تک‌روز | ابزارها و ترفندهای هوش مصنوعی به زبان ساده</div>
<div>هر روز ۱۰ مطلب تازه در <a href="{CHANNEL}">کانال تلگرام @techrooz_fa</a></div>
<div>📩 تماس و تبلیغات: <a href="https://t.me/{ADMIN_TG}">@{ADMIN_TG}</a> · <a href="mailto:{EMAIL}">{EMAIL}</a></div></div></footer>""" + JS + "</body></html>"

JOIN = f"""<div class="box join"><h4>📲 تک‌روز در تلگرام</h4><p>هر روز ابزار، پرامپت و خبرای داغ AI رو زودتر از همه ببین</p>
<a href="{CHANNEL}">عضویت رایگان</a></div>"""


def thumb(p, root):
    _, _, emo = cat_of(p["slug"])
    if p.get("photo"):
        return f'<div class="thumb"><img src="{html.escape(p["photo"])}" alt="" loading="lazy" referrerpolicy="no-referrer"></div>'
    return f'<div class="thumb">{emo}</div>'


def card(p, root=""):
    key, name, _ = cat_of(p["slug"])
    return (f'<a class="card" data-cat="{key}" href="{root}p/{p["slug"]}.html" style="--c:{COLORS.get(key)}">{thumb(p, root)}<div class="in"><span class="chip">{name}</span>'
            f'<h3>{html.escape(title_of(p["caption"]))}</h3><p>{html.escape(excerpt(p["caption"]))}</p>'
            f'<div class="time">🕒 {p["date"]}</div></div></a>')


def sidebar(posts, root):
    items = "".join(f'<a href="{root}p/{p["slug"]}.html"><span>{i}</span>{html.escape(title_of(p["caption"]))}</a>'
                    for i, p in enumerate(posts[:6], 1))
    return f'<aside>{JOIN}<div class="box list"><h4>🔥 تازه‌ترین‌ها</h4>{items}</div>{CONTACT}</aside>'


def main(queue_path, site):
    os.makedirs(os.path.join(site, "p"), exist_ok=True)
    store = os.path.join(site, "posts.json")
    posts = json.load(open(store, encoding="utf-8")) if os.path.exists(store) else []
    seen = {p["at"] for p in posts}
    for it in json.load(open(queue_path, encoding="utf-8")):
        if it.get("posted") and it["at"] not in seen:
            d = datetime.fromisoformat(it["at"].replace("Z", "+00:00")).astimezone(TEH)
            posts.append({"at": it["at"], "slug": d.strftime("%Y%m%d-%H%M"), "date": jalali(d),
                          "photo": it.get("photo", ""), "caption": it["caption"], "source": it.get("source", "")})
    for p in posts:
        p["date"] = jalali(datetime.fromisoformat(p["at"].replace("Z", "+00:00")).astimezone(TEH))
    posts.sort(key=lambda p: p["at"], reverse=True)
    json.dump(posts, open(store, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(site, "style.css"), "w").write(CSS)

    for p in posts:
        key, name, _ = cat_of(p["slug"])
        t = title_of(p["caption"])
        og = f'<meta property="og:image" content="{html.escape(p["photo"])}">' if p.get("photo") else ""
        cover = f'<img class="cover" src="{html.escape(p["photo"])}" alt="" referrerpolicy="no-referrer">' if p.get("photo") else ""
        src = f'<div class="src">منبع: <a href="{html.escape(p["source"])}" rel="nofollow noopener">{html.escape(p["source"].split("/")[2])}</a></div>' if p.get("source") else ""
        related = [q for q in posts if q is not p and cat_of(q["slug"])[0] == key][:3] or [q for q in posts if q is not p][:3]
        page = (HEAD.format(title=html.escape(t + " | تک‌روز"), desc=html.escape(plain(p["caption"])), og=og,
                            url=f"{SITE_URL}/p/{p['slug']}.html", root="../")
                + topbar("../", key) + '<main class="wrap layout"><div>'
                + f'<article class="post"><div class="crumb"><a href="../index.html">تک‌روز</a> › {name}</div>'
                + f'<h1>{html.escape(t)}</h1><div class="time">🕒 {p["date"]} · ⏱ {max(1, len(plain(p["caption"], 99999).split()) // 180)} دقیقه مطالعه</div>{cover}<div class="body">{clean(chr(10).join(p["caption"].split(chr(10))[1:]))}</div>{src}<div class="share"><a href="https://t.me/share/url?url={SITE_URL}/p/{p['slug']}.html">📤 ارسال در تلگرام</a><button class="copylink">🔗 کپی لینک</button></div></article>'
                + '<div class="sec" style="margin-top:24px"><h2>مطالب مرتبط</h2></div><div class="grid">'
                + "".join(card(q, "../") for q in related) + "</div></div>" + sidebar(posts, "../") + "</main>" + FOOT)
        open(os.path.join(site, "p", p["slug"] + ".html"), "w", encoding="utf-8").write(page)

    hero = next((p for p in posts if p.get("photo")), posts[0] if posts else None)
    body = ""
    if hero:
        himg = f'<img src="{html.escape(hero["photo"])}" alt="" referrerpolicy="no-referrer">' if hero.get("photo") else ""
        body += (f'<a class="hero" href="p/{hero["slug"]}.html">{himg}<div class="in"><span class="chip">{cat_of(hero["slug"])[1]}</span>'
                 f'<h1>{html.escape(title_of(hero["caption"]))}</h1><p>{html.escape(excerpt(hero["caption"], 160))}</p></div></a>')
    intro = (f'<section class="intro"><h1>⚡ تک‌روز</h1><p>همه‌ی دنیای تکنولوژی و هوش مصنوعی، کوتاه و به زبون ساده</p>'
             f'<a class="cta" href="{CHANNEL}">📲 عضویت رایگان در تلگرام</a>'
             '<div class="stats"><span>📰 ۱۰ مطلب تازه در روز</span><span>🤖 ابزار و پرامپت AI</span><span>🆓 کاملاً رایگان</span></div></section>')
    pills = '<div class="pills"><button class="on" data-cat="all">همه</button>' + "".join(f'<button data-cat="{k}">{n}</button>' for k, n in NAV) + "</div>"
    body = intro + body
    body += ('<input class="search" type="search" placeholder="🔍 جست‌وجو در مطالب تک‌روز...">' + pills
             + '<div class="sec"><h2>آخرین مطالب</h2></div><div class="grid feed">'
             + "".join(card(p) for p in [q for q in posts if q is not hero][:40]) + '</div><div class="empty">مطلبی پیدا نشد 🤷</div>')
    index = (HEAD.format(title="تک‌روز | هوش مصنوعی، ChatGPT و تکنولوژی به فارسی",
                         desc="ابزارهای هوش مصنوعی، پرامپت آماده، ترفند موبایل و خبرهای داغ تکنولوژی به زبان ساده.",
                         og="", url=SITE_URL + "/", root="")
             + topbar("") + f'<main class="wrap layout"><div>{body}</div>{sidebar(posts, "")}</main>' + FOOT)
    open(os.path.join(site, "index.html"), "w", encoding="utf-8").write(index)
    urls = [SITE_URL + "/"] + [f"{SITE_URL}/p/{p['slug']}.html" for p in posts]
    open(os.path.join(site, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                                       + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    open(os.path.join(site, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    print(len(posts), "posts")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
