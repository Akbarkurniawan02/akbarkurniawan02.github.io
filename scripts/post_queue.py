"""Post due items from automations/techrooz-queue.json to the Telegram channel.

Runs in GitHub Actions. Needs the TELEGRAM_BOT_TOKEN secret.
Each queue item: {"at": "2026-11-02T08:30:00Z", "photo": "<url or empty>", "caption": "<HTML>", "source": "<url>", "posted": false}
Optional: "photos" (list of 2-10 image URLs = album), "poll" ({"question", "options"}), "silent" (no notification sound), "video" (direct mp4 URL, posted with sendVideo) and "link" (text post shows its preview, e.g. YouTube).
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

QUEUE = "queue.json"
CHAT = "@techrooz_fa"
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SHARE_TEXT = urllib.parse.quote("ابزارها و ترفندهای هوش مصنوعی به فارسی 🤖⚡")
# share button under every post, so readers can send the channel to friends in one tap
BUTTONS = {"inline_keyboard": [[
    {"text": "📤 ارسال برای دوستان", "url": f"https://t.me/share/url?url=https%3A%2F%2Ft.me%2Ftechrooz_fa&text={SHARE_TEXT}"},
]]}


def call(method, payload):
    if method.startswith("send"):
        if method != "sendMediaGroup":  # albums can't carry buttons
            payload = {**payload, "reply_markup": BUTTONS}
        if SILENT and method.startswith("send"):  # minor posts go out without a notification sound, so fewer people mute the channel
            payload["disable_notification"] = True
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        return json.load(e)


SILENT = False
WAIT_LIMIT = 30  # seconds; the daemon loop checks every 20s, then waits for the exact second


def send(item):
    global SILENT
    SILENT = bool(item.get("silent"))
    if item.get("poll"):  # {"question": "...", "options": ["..", ".."]}
        return call("sendPoll", {"chat_id": CHAT, "question": item["poll"]["question"],
                                 "options": [{"text": o} for o in item["poll"]["options"]], "is_anonymous": True})
    if len(item.get("photos") or []) > 1:  # album: several photos, caption on the first
        media = [{"type": "photo", "media": u} for u in item["photos"][:10]]
        media[0].update(caption=item["caption"], parse_mode="HTML")
        r = call("sendMediaGroup", {"chat_id": CHAT, "media": media})
        if r.get("ok"):
            return r
        print("sendMediaGroup failed:", r.get("description"))
        item.setdefault("photo", item["photos"][0])
    if item.get("video"):
        r = call("sendVideo", {"chat_id": CHAT, "video": item["video"], "caption": item["caption"], "parse_mode": "HTML", "supports_streaming": True})
        if r.get("ok"):
            return r
        print("sendVideo failed:", r.get("description"))
    if item.get("photo"):
        r = call("sendPhoto", {"chat_id": CHAT, "photo": item["photo"], "caption": item["caption"], "parse_mode": "HTML"})
        if r.get("ok"):
            return r
        print("sendPhoto failed, sending text only:", r.get("description"))
    # a text post with a "link" (e.g. a YouTube video) shows that link's preview
    return call("sendMessage", {"chat_id": CHAT, "text": item["caption"], "parse_mode": "HTML",
                                "disable_web_page_preview": not item.get("link")})


def one_pass():
    with open(QUEUE, encoding="utf-8") as f:
        queue = json.load(f)
    # The workflow starts a few minutes before each slot; wait here so the
    # next post goes out exactly on time (to the second).
    when = lambda i: datetime.fromisoformat(i["at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    upcoming = [when(i) for i in queue if not i.get("posted") and not i.get("hold") and when(i) > now]
    if upcoming:
        wait = (min(upcoming) - now).total_seconds()
        if wait <= WAIT_LIMIT:
            print(f"waiting {int(wait)}s for the next slot")
            time.sleep(wait)
    now = datetime.now(timezone.utc)
    changed = False
    for item in queue:
        if item.get("posted") or item.get("hold"):
            continue
        if datetime.fromisoformat(item["at"].replace("Z", "+00:00")) > now:
            continue
        r = send(item)
        print(item["at"], "ok" if r.get("ok") else r.get("description"))
        if r.get("ok"):
            item["posted"] = True
            changed = True
    # keep only the last 50 posted items so the file stays small
    posted = [i for i in queue if i.get("posted")][-50:]
    queue = posted + [i for i in queue if not i.get("posted")]
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=1)
    print("changed" if changed else "nothing due")
    return "changed" if changed else ""


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


TEH = timezone(timedelta(hours=3, minutes=30))
OWNER, BOT = "mohammadsafari2222", "TechRooz_fa_bot"


def daily_stats():
    """Once a day: member count + admin check, saved to stats.json (read by the daily Claude run,
    so Claude never needs the bot token)."""
    today = datetime.now(TEH).strftime("%Y-%m-%d")
    try:
        old = json.load(open("stats.json", encoding="utf-8"))
    except (OSError, ValueError):
        old = []
    if old and old[-1].get("date") == today:
        return False
    members = call("getChatMemberCount", {"chat_id": CHAT}).get("result")
    admins = [a["user"].get("username", a["user"].get("first_name")) for a in call("getChatAdministrators", {"chat_id": CHAT}).get("result", [])]
    chat = call("getChat", {"chat_id": CHAT}).get("result", {})
    # average views of the last ~20 public posts (no token needed, public preview page)
    views = []
    try:
        page = urllib.request.urlopen(urllib.request.Request("https://t.me/s/techrooz_fa", headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode()
        import re
        for v in re.findall(r'tgme_widget_message_views">([^<]+)', page)[-20:]:
            v = v.strip()
            views.append(int(float(v[:-1]) * 1000) if v.endswith("K") else int(float(v)))
    except Exception as e:  # stats are best-effort
        print("views fetch failed:", e)
    avg = round(sum(views) / len(views)) if views else 0
    old.append({"date": today, "members": members, "admins": admins,
                "admins_ok": sorted(admins) == sorted([OWNER, BOT]), "title": chat.get("title"),
                "avg_views": avg, "reach_pct": round(100 * avg / members, 1) if members else 0})
    json.dump(old[-120:], open("stats.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return True


def daemon(hours):
    """Stay up for `hours`: pull new queue items, post each one exactly on time,
    save the queue and rebuild the website after every post."""
    end = time.time() + hours * 3600
    while time.time() < end:
        git("pull", "-q", "--rebase", "origin", "main")
        changed = one_pass() == "changed"
        if datetime.now(TEH).hour >= 6 and daily_stats():
            changed = True
        if changed:
            subprocess.run([sys.executable, "scripts/build_site.py", QUEUE, "."], check=False)
            git("add", "-A")
            git("commit", "-qm", "Post TechRooz items and update site")
            for _ in range(3):
                if git("push", "-q", "origin", "HEAD:main").returncode == 0:
                    break
                git("pull", "-q", "--rebase", "origin", "main")
        time.sleep(20)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--daemon":
        daemon(float(sys.argv[2]))
    else:
        one_pass()
