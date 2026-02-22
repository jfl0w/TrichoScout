#!/usr/bin/env python3
"""
Tricho Scout — Sales Subreddit Monitor
Monitors r/sanpedrocactusforsale for keyword matches and sends email digests.

Setup:
    pip install requests

Usage:
    python trichoscout.py                  # run once
    python trichoscout.py --watch          # run every N minutes continuously

Cron example (every 5 minutes):
    */5 * * * * /usr/bin/python3 /path/to/trichoscout.py >> /path/to/trichoscout.log 2>&1
"""

import argparse
import json
import os
import re
import smtplib
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

# ── Configuration ─────────────────────────────────────────────────────────────

SUBREDDIT = "sanpedrocactusforsale"

# Change keywords below to match terms when monitoring
KEYWORDS = [
    "pachanoi",
    "bridgesii",
    "peruvianus",
    "trichocereus",
    "san pedro",
    "crest",
    "variegata",
]

FILTER_SOLD = True          # Skip posts with "sold" in title or body

# Email settings (Gmail example — see SMTP SETUP below)
EMAIL_ENABLED   = True
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587
SMTP_USER       = "your_email@gmail.com"      # your Gmail address
SMTP_PASSWORD   = "your_app_password_here"    # Gmail App Password (not your login password)
EMAIL_FROM      = "your_email@gmail.com"
EMAIL_TO        = "your_email@gmail.com"      # where to send alerts (can be same)
EMAIL_SUBJECT   = "🌵 Tricho Scout: {count} new match(es)!"

# State file — tracks which post IDs have already been seen
STATE_FILE = Path(__file__).parent / "cactus_seen.json"

# ── SMTP SETUP GUIDE ──────────────────────────────────────────────────────────
#
#  Gmail:
#    1. Enable 2-Step Verification on your Google account
#    2. Go to: myaccount.google.com/apppasswords
#    3. Create an App Password for "Mail"
#    4. Paste the 16-character password into SMTP_PASSWORD above
#    5. Set SMTP_HOST = "smtp.gmail.com", SMTP_PORT = 587
#
#  Other providers:
#    Outlook/Hotmail: smtp-mail.outlook.com  port 587
#    Yahoo:           smtp.mail.yahoo.com    port 587
#
# ─────────────────────────────────────────────────────────────────────────────


# ── State management ──────────────────────────────────────────────────────────

def load_seen_ids() -> set:
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text()))
        except Exception:
            pass
    return set()


def save_seen_ids(seen: set):
    # Keep at most 2000 IDs to prevent unbounded growth
    ids = list(seen)[-2000:]
    STATE_FILE.write_text(json.dumps(ids))


# ── Reddit fetch ──────────────────────────────────────────────────────────────

RSS_URL = f"https://www.reddit.com/r/{SUBREDDIT}/new.rss?limit=25"
HEADERS = {"User-Agent": "CactusScout/1.0 (keyword monitor)"}


def fetch_posts(after: str = None) -> list[dict]:
    """Fetch up to 25 posts from the subreddit RSS feed."""
    url = RSS_URL + (f"&after={after}" if after else "")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return parse_rss(resp.text)
    except Exception as e:
        print(f"[{now()}] Fetch error: {e}")
        return []


def fetch_comment_counts(post_ids: list[str]) -> dict[str, int]:
    """Fetch comment counts for a batch of post IDs via Reddit JSON API."""
    if not post_ids:
        return {}
    fullnames = ",".join(f"t3_{pid}" for pid in post_ids)
    url = f"https://www.reddit.com/by_id/{fullnames}.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {
            child["data"]["id"]: child["data"]["num_comments"]
            for child in data.get("data", {}).get("children", [])
            if "data" in child
        }
    except Exception as e:
        print(f"[{now()}] Comment count fetch error: {e}")
        return {}


def parse_rss(xml_text: str) -> list[dict]:
    """Parse Reddit Atom RSS feed into a list of post dicts."""
    # Strip any junk before XML declaration
    for marker in ("<?xml", "<feed", "<rss"):
        idx = xml_text.find(marker)
        if idx != -1:
            xml_text = xml_text[idx:]
            break

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"[{now()}] RSS parse error: {e}")
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    posts = []

    for entry in root.findall("atom:entry", ns):
        id_raw   = entry.findtext("atom:id", default="", namespaces=ns).strip()
        title    = entry.findtext("atom:title", default="(no title)", namespaces=ns).strip()
        author   = entry.find("atom:author/atom:name", ns)
        author   = (author.text or "unknown").strip().lstrip("u/") if author is not None else "unknown"
        published = entry.findtext("atom:published", default="", namespaces=ns).strip()
        content  = entry.findtext("atom:content", default="", namespaces=ns).strip()

        link_el = entry.find("atom:link[@rel='alternate']", ns) or entry.find("atom:link", ns)
        url = (link_el.get("href") or "").strip() if link_el is not None else ""

        # Extract post ID
        m = re.search(r"t3_([a-z0-9]+)", id_raw) or re.search(r"/comments/([a-z0-9]+)/", url)
        post_id = m.group(1) if m else id_raw[-8:] or str(time.time())

        posts.append({
            "id":        post_id,
            "title":     title,
            "url":       url,
            "author":    author,
            "published": published,
            "content":   content,
            "comments":  None,
        })

    return posts


# ── Matching ──────────────────────────────────────────────────────────────────

def is_sold(post: dict) -> bool:
    if not FILTER_SOLD:
        return False
    text = (post["title"] + " " + post["content"]).lower()
    return bool(re.search(r"\bsold\b", text))


def match_keywords(post: dict) -> list[str]:
    text = (post["title"] + " " + post["content"]).lower()
    return [kw for kw in KEYWORDS if kw.lower() in text]


# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(matches: list[dict]):
    if not EMAIL_ENABLED or not matches:
        return

    subject = EMAIL_SUBJECT.format(count=len(matches))

    # Plain text body
    lines = [f"🌵 Tricho Scout found {len(matches)} new match(es)!\n"]
    for p in matches:
        comment_str = f"💬 {p['comments']} comments" if p.get("comments") is not None else ""
        kw_str = ", ".join(p["matched_kws"])
        pub = format_time(p["published"])
        lines.append(f"• {p['title']}")
        lines.append(f"  Author:   u/{p['author']}")
        lines.append(f"  Posted:   {pub}")
        lines.append(f"  Keywords: {kw_str}")
        if comment_str:
            lines.append(f"  {comment_str}")
        lines.append(f"  Link:     {p['url']}")
        lines.append("")

    body_text = "\n".join(lines)

    # HTML body
    html_rows = ""
    for p in matches:
        comment_str = f"💬 {p['comments']}" if p.get("comments") is not None else ""
        kw_badges = " ".join(f'<span style="background:#1d2e1d;border:1px solid #2a3d2a;padding:2px 8px;border-radius:4px;font-size:12px;color:#5ddf6e">{kw}</span>' for kw in p["matched_kws"])
        pub = format_time(p["published"])
        html_rows += f"""
        <div style="background:#111811;border:1px solid #5ddf6e;border-radius:10px;padding:16px;margin-bottom:12px">
            <div style="font-size:15px;font-weight:600;margin-bottom:6px">
                <a href="{p['url']}" style="color:#ffffff;text-decoration:none">{p['title']}</a>
            </div>
            <div style="font-size:12px;color:#5a7a5c;margin-bottom:8px">
                u/{p['author']} &nbsp;·&nbsp; {pub} &nbsp;·&nbsp; {comment_str}
            </div>
            <div>{kw_badges}</div>
        </div>"""

    body_html = f"""
    <html><body style="background:#0a0f0a;color:#d8f0da;font-family:monospace;padding:24px">
        <h2 style="color:#5ddf6e">🌵 Tricho Scout — {len(matches)} new match(es)</h2>
        {html_rows}
        <p style="color:#5a7a5c;font-size:11px;margin-top:24px">Sent by Tricho Scout · r/{SUBREDDIT}</p>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print(f"[{now()}] 📧 Email sent — {len(matches)} match(es).")
    except Exception as e:
        print(f"[{now()}] Email error: {e}")


# ── Utilities ─────────────────────────────────────────────────────────────────

def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        return iso


# ── Main check cycle ──────────────────────────────────────────────────────────

def check(lookback_hours: float = 0):
    seen = load_seen_ids()
    cutoff = None
    if lookback_hours > 0:
        cutoff = datetime.now(timezone.utc).timestamp() - (lookback_hours * 3600)
        print(f"[{now()}] Running with {lookback_hours}h lookback…")
    else:
        print(f"[{now()}] Checking r/{SUBREDDIT}…")

    all_new_posts = []
    after = None

    while True:
        posts = fetch_posts(after=after)
        if not posts:
            break

        new_posts = [p for p in posts if p["id"] not in seen]

        # If doing lookback, filter by time and paginate
        if cutoff:
            in_window = []
            for p in new_posts:
                try:
                    t = datetime.fromisoformat(p["published"].replace("Z", "+00:00")).timestamp()
                    if t >= cutoff:
                        in_window.append(p)
                except Exception:
                    in_window.append(p)
            all_new_posts.extend(in_window)

            # Stop paginating if oldest post is before cutoff
            try:
                oldest_t = datetime.fromisoformat(
                    posts[-1]["published"].replace("Z", "+00:00")
                ).timestamp()
            except Exception:
                oldest_t = 0

            if oldest_t < cutoff or len(posts) < 25:
                break
            after = "t3_" + posts[-1]["id"]
            time.sleep(0.6)  # be polite to Reddit's API
        else:
            all_new_posts.extend(new_posts)
            break

    # Mark all fetched posts as seen (not just matches)
    all_fetched = fetch_posts()
    for p in all_fetched:
        seen.add(p["id"])
    for p in all_new_posts:
        seen.add(p["id"])
    save_seen_ids(seen)

    print(f"[{now()}] {len(all_new_posts)} new post(s) to check.")

    # Filter sold and find matches
    matches = []
    for p in all_new_posts:
        if is_sold(p):
            print(f"[{now()}] Skipping sold: {p['title'][:60]}")
            continue
        matched_kws = match_keywords(p)
        if matched_kws:
            p["matched_kws"] = matched_kws
            matches.append(p)
            print(f"[{now()}] ✅ Match: {p['title'][:70]} (kw: {', '.join(matched_kws)})")

    if not matches:
        print(f"[{now()}] No matches this cycle.")
        return

    # Fetch comment counts for matches
    counts = fetch_comment_counts([p["id"] for p in matches])
    for p in matches:
        p["comments"] = counts.get(p["id"])

    print(f"[{now()}] {len(matches)} match(es) found — sending email…")
    send_email(matches)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tricho Scout Reddit Monitor")
    parser.add_argument("--watch", action="store_true",
                        help="Run continuously on an interval")
    parser.add_argument("--interval", type=int, default=5,
                        help="Check interval in minutes (default: 5, used with --watch)")
    parser.add_argument("--lookback", type=float, default=0,
                        help="On first run, scan this many hours back (e.g. --lookback 24)")
    args = parser.parse_args()

    if args.watch:
        print(f"[{now()}] 🌵 Tricho Scout started — checking every {args.interval} min.")
        first_run = True
        while True:
            lookback = args.lookback if first_run else 0
            check(lookback_hours=lookback)
            first_run = False
            print(f"[{now()}] Sleeping {args.interval} min…")
            time.sleep(args.interval * 60)
    else:
        check(lookback_hours=args.lookback)
