# 🌵 TrichoScout

A keyword monitor for [r/sanpedrocactusforsale](https://www.reddit.com/r/sanpedrocactusforsale/) that alerts you when new listings match your search terms. Available as a **browser-based web app** for casual use, and a **Python script** for always-on server or VPS deployment.

---

## Contents

| File | Description |
|------|-------------|
| `trichoScout.html` | Self-contained browser app in a single HTML file. Run locally, no install needed |
| `TrichoScout.py` | Python script for headless/server use |

---

## trichoScout.html — Browser Web App

### Overview
<img width="1424" height="901" alt="image" src="https://github.com/user-attachments/assets/25d52396-cd72-48e8-b9de-f50717b5af27" />

A single HTML file you can open directly in any browser. No server, no install, no dependencies. Monitors Reddit's public RSS feed for new posts matching your keywords and displays them in a live feed.

### Features

- **Keyword matching** — add/remove keywords at any time; posts matching any keyword are highlighted (OR logic)
- **Live feed** — all posts and matched posts in separate tabs with badge counts
- **Lookback on start** — optionally scan historical posts (8h, 24h, 3 days, 1 week, 1 month) when monitoring begins
- **Comment counts** — fetched live from Reddit's JSON API and displayed per post
- **Hide sold posts** — filters out posts containing the "sold" falir
- **Email digests** — sends a styled HTML email via [EmailJS](https://www.emailjs.com) when matches are found (free tier: 200 emails/month)
- **Sound alerts** — optional chime on match
- **Browser notifications** — native desktop notifications for matches
- **Persistent state** — keywords and seen post IDs saved to `localStorage` across sessions

### Usage

1. Download `trichoScout.html`
2. Open it in any modern browser (Chrome, Firefox, Safari, Edge)
3. Add your keywords, choose your check intervals and optional lookback period, then click **Start Monitoring**

That's all there is to it!

### Check Intervals

| Option | Value |
|--------|-------|
| Every 5 minutes | default |
| Every 15 minutes | |
| Every 30 minutes | |
| Every 1 hour | |
| Every 3 hours | |
| Every 6 hours | |
| Every 12 hours | |
| Every 24 hours | |

### Email Setup (EmailJS)

The browser app uses [EmailJS](https://www.emailjs.com) to send emails directly from the browser without a backend.

1. Create a free account at [emailjs.com](https://www.emailjs.com)
2. Add an **Email Service** (Gmail, Outlook, etc.) → copy the **Service ID**
3. Create an **Email Template** using these variables:
   - `{{count}}` — number of matches found
   - `{{matches}}` — formatted list of matching posts (title, keywords, comment count, link)
4. Go to **Account → General** → copy your **Public Key**
5. In the app, expand **📧 Email Notifications** in the sidebar, paste all three values plus your email address, and click **Save Email Config**

Emails are sent as a digest with one email per check cycle summarising all matches found, including lookback results.

### Limitations

- The local web app will pause monitoring when the browser tab is inactive or if the laptop sleeps. Use `TrichoScout.py` hosted on a VPS or always-on server host (e.g. Raspberry Pi) for continuous monitoring
- Requires CORS proxies to fetch Reddit RSS from the browser (three proxies with automatic failover are built in)
- EmailJS free tier is limited to 200 emails/month

---

## TrichoScout.py — Python Script

### Overview

A headless Python script for continuous monitoring. Runs independently of a browser, works on any machine or VPS, and sends emails directly via SMTP. Ideal for running on a server, Raspberry Pi, or any always-on machine.

### Requirements

- Python 3.10+
- `requests` library

```bash
pip install requests
```

No other dependencies are needed. All other modules (`smtplib`, `xml`, `json`, etc.) are part of the Python standard library.

### Configuration

Edit the configuration block at the top of `TrichoScout.py`:

```python
SUBREDDIT   = "sanpedrocactusforsale"

KEYWORDS    = [
    "pachanoi",
    "bridgesii",
    "peruvianus",
    "trichocereus",
    "san pedro",
    "crest",
    "variegata",
]

FILTER_SOLD = True   # Skip posts containing "sold"

SMTP_USER     = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"    # Gmail App Password (remove spaces!) — NOT your login password
EMAIL_TO      = "your_email@gmail.com"
```

### Gmail App Password Setup

1. Enable **2-Step Verification** on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create an App Password for **Mail**
4. Paste the 16-character password into `SMTP_PASSWORD` — **remove any spaces**

> Other providers: Outlook uses `smtp-mail.outlook.com` port 587, Yahoo uses `smtp.mail.yahoo.com` port 587.

### Usage

```bash
# Run once and exit
python TrichoScout.py

# Run once with a 24-hour lookback (scans historical posts on first run)
python TrichoScout.py --lookback 24

# Run continuously, checking every 5 minutes (default)
python TrichoScout.py --watch

# Run continuously with a custom interval
python TrichoScout.py --watch --interval 10    # every 10 minutes
python TrichoScout.py --watch --interval 180   # every 3 hours

# Run continuously with lookback on first check
python TrichoScout.py --watch --interval 10 --lookback 24
```
#### Sample Output
```bash
python "TrichoScout.py" --watch --interval 2 --lookback 72
[2026-02-21 16:52:03] 🌵 Tricho Scout started — checking every 2 min.
[2026-02-21 16:52:03] Running with 72.0h lookback…
[2026-02-21 16:52:16] 50 new post(s) to check.
[2026-02-21 16:52:16] ✅ Match: cv. Cali. Peaches. 2 bundle boxes A$90 4lb B. $100 ~5lb SHIPPED. Never (kw: bridgesii)
[2026-02-21 16:52:16] ✅ Match: $38 + shipping (kw: bridgesii)
[2026-02-21 16:52:16] ✅ Match: single source bulk bulk TPM over 9’ $125 (kw: pachanoi, trichocereus, crest)
[2026-02-21 16:52:16] ✅ Match: SKIPS BRIDGESII(Shulgin genetics). Rooted graft pushing new growth. (kw: bridgesii, shulgin)
[2026-02-21 16:52:16] ✅ Match: single source bulk box - JS350b pachanoi over 9 feet $125 (kw: pachanoi, trichocereus)
[2026-02-21 16:52:16] ✅ Match: February Bundle C Relist. $50 free 🚢 (kw: bridgesii, ss02, trichocereus)
[2026-02-21 16:52:16] ✅ Match: Trichocereus hyb. Monstrose Grafts. (kw: trichocereus)
[2026-02-21 16:52:16] ✅ Match: a Tom Juuls Giant and eight ugly bridgesii $133 (kw: bridgesii, pachanoi, trichocereus)
[2026-02-21 16:52:16] ✅ Match: six big cacs for $116 (kw: bridgesii, pachanoi, trichocereus)
[2026-02-21 16:52:16] ✅ Match: Siegfried Ikaros Landrace Matucana Peruvianus 12” tip for 65 plus ship (kw: peruvianus)
[2026-02-21 16:52:16] ✅ Match: Ogun 12” tip for 60 or 9” mid for 30 plus shipping (kw: ogun)
[2026-02-21 16:52:16] ✅ Match: Tiger Sharxx 100🚢 (kw: bridgesii)
[2026-02-21 16:52:16] ✅ Match: (44+) 3 to 10" Eileen malo 4, half tray $45, whole tray $70 shipped (kw: eileen)
[2026-02-21 16:52:16] ✅ Match: 3"x4"x3" MB scopulicola x tpm cresty clump $35 (kw: crest)
[2026-02-21 16:52:16] ✅ Match: (2) 12" Nadir $35 eqch or both for $50 shipped (kw: pachanoi)
[2026-02-21 16:52:16] ✅ Match: 12" Trent $40 shipped (kw: peruvianus)
[2026-02-21 16:52:16] ✅ Match: Fat ass 12" seed grown scopulicola $45 shipped (kw: san pedro)
[2026-02-21 16:52:16] ✅ Match: Jiimz Bridgesii Twin Spine 89 to your door (kw: bridgesii, jiimz)
[2026-02-21 16:52:16] ✅ Match: Heavy Chunk of non pc Pachanoi 79 to your door (kw: pachanoi)
[2026-02-21 16:52:16] ✅ Match: Glowing baker5242xSS02 graft bundle free anokxSS02 seeds&FreeTBM-B (kw: ss02)
[2026-02-21 16:52:16] ✅ Match: Jiimz Bridgesii Twin Spine 129 to your door (kw: bridgesii, jiimz)
[2026-02-21 16:52:16] ✅ Match: Jiimz Bridgesii 17” 4lb 12 oz - 99 to your door (kw: bridgesii, jiimz)
[2026-02-21 16:52:17] 22 match(es) found — sending email…
[2026-02-21 16:52:19] 📧 Email sent — 22 match(es).
```
#### Stylized Email
<img width="1422" height="682" alt="image" src="https://github.com/user-attachments/assets/7d228cb9-4607-4aaa-8e74-e2f8d021dfc8" />


### CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--watch` | off | Run continuously on a loop |
| `--interval` | `5` | Check interval in minutes (use with `--watch`) |
| `--lookback` | `0` | Hours of history to scan on the first run |

### Running with Cron (Linux/macOS)

To run automatically every 5 minutes without `--watch`, add a cron job:

```bash
crontab -e
```

Add this line (update the paths to match your system):

```
*/5 * * * * /usr/bin/python3 /path/to/TrichoScout.py >> /path/to/trichoscout.log 2>&1
```

Other cron examples:

```
*/10 * * * *   # every 10 minutes
0 * * * *      # every hour
0 */3 * * *    # every 3 hours
```

### State File

The script saves seen post IDs to `trichoscout_seen.json` in the same directory as the script. This prevents re-alerting on posts already processed across runs. The file stores up to 2000 IDs and trims automatically.

### Email Format

Emails are sent as multipart MIME with both a plain text and styled HTML version. Each match in the digest includes:

- Post title (linked)
- Author
- Posted timestamp
- Matched keywords
- Comment count
- Direct Reddit link



---

## Choosing Between the Two

| | `trichoScout.html` | `TrichoScout.py` |
|---|---|---|
| Setup | Open in browser | `pip install requests` |
| Always-on | ❌ Pauses when laptop sleeps | ✅ Runs on server/VPS |
| Email service | EmailJS (free tier) | SMTP / Gmail direct |
| CORS proxies needed | ✅ Yes | ❌ No |
| Customise via UI | ✅ Yes | Edit config in file |
| Best for | Casual / occasional use | Reliable 24/7 monitoring |

---

## Disclaimer

TrichoScout uses Reddit's public RSS feed and JSON API. It does not use the official Reddit API and does not require authentication. Please be respectful of Reddit's rate limits and avoid setting check intervals below 2 minutes.

---

*Built for the trichocereus community. Happy hunting! 🌵*
