# FuckZuck

Access Facebook for specific information/updates without generating advertising revenue for that asshole.

**Birthday Bot**: Automatically identifies when it's a contact's birthday, posts "Happy Birthday" on their Facebook wall, and notifies you via email and SMS for personal follow-up.

## Features

- Scrapes birthdays from Facebook's events page (no Meta API needed)
- Posts "Happy Birthday! [Name]" on each friend's wall
- Sends you email and SMS with today's birthday list
- Automated login with manual fallback (2FA, captcha)
- Session persistence to avoid repeated logins

## Setup

### 1. Install

```bash
cd FuckZuck
pip install -e .
playwright install chromium
```

### 2. Configure

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

**Facebook** (for automated login; optional if using manual login):

- `FB_EMAIL` – your Facebook email
- `FB_PASSWORD` – your Facebook password

**Email** (SMTP, e.g. Gmail):

- `NOTIFY_EMAIL` – where to send the birthday reminder
- `NOTIFY_EMAIL_ENABLED` – `true` or `false`
- `SMTP_HOST` – e.g. `smtp.gmail.com`
- `SMTP_PORT` – e.g. `587`
- `SMTP_USER` – your email
- `SMTP_PASS` – app password (for Gmail, use an [App Password](https://support.google.com/accounts/answer/185833))

**SMS** (Twilio):

- `NOTIFY_PHONE` – your phone number (e.g. `+1234567890`)
- `NOTIFY_SMS_ENABLED` – `true` or `false`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM` – from [Twilio Console](https://console.twilio.com/)

### 3. First run (login)

On first run, you'll need to log in. If automated login fails (2FA, captcha), the bot will open a visible browser for you to log in manually. The session is saved in `.auth/state.json` for future runs.

```bash
fuckzuck --manual-login
```

Or with credentials in `.env`:

```bash
fuckzuck --no-headless
```

## Usage

**Dry run** (fetch and print birthdays only; no posts, no notifications):

```bash
fuckzuck --dry-run
```

**Full run** (post + notify):

```bash
fuckzuck
```

**Limit posts** (for testing):

```bash
fuckzuck --limit 2
```

**Manual login** (skip automated login):

```bash
fuckzuck --manual-login
```

## Scheduling

### Option A: cron (Linux/macOS)

Run daily at 8 AM:

```bash
crontab -e
```

Add:

```
0 8 * * * cd /path/to/FuckZuck && /path/to/python -m fuckzuck.main
```

Replace `/path/to/FuckZuck` and `/path/to/python` with your actual paths.

### Option B: schedule (in-process)

```python
import schedule
import time
from fuckzuck.main import main

schedule.every().day.at("08:00").do(main)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Fallback: manual HTML paste

If scraping fails:

1. Visit [Facebook birthdays](https://www.facebook.com/events/birthdays/)
2. Scroll to load all birthdays
3. Right-click the birthdays content div → Inspect → Copy element
4. Paste into `birthdays_html.html` in the project root
5. Run the bot again (it will parse from the file)

## Project structure

```
FuckZuck/
├── src/fuckzuck/
│   ├── auth.py       # login, session persistence
│   ├── birthdays.py  # scrape & parse birthdays
│   ├── main.py       # entry point
│   ├── notify.py     # email + SMS
│   └── post.py       # post to friend wall
├── .auth/            # session state (gitignored)
├── .env.example
├── pyproject.toml
└── README.md
```

## License

MIT
