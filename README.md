# FuckZuck

Access Facebook for specific information/updates without generating advertising revenue for that asshole.

**Birthday Bot**: Scrapes your Facebook friends' birthdays, stores them locally, and notifies you via email and SMS so you can follow up personally.

## Features

- Scrapes birthdays from Facebook's events page (no Meta API needed)
- **Scrape once, notify daily** — one-time scrape stores all birthdays locally; daily cron checks the store and notifies without touching Facebook
- Sends you email and SMS with today's birthday list
- Automated login with manual fallback (2FA, captcha)
- Persistent browser profile to avoid repeated logins
- Anti-detection stealth (playwright-stealth, human-like timing, realistic fingerprints)
- Fallback: paste HTML manually if scraping fails

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

### 3. First run (login + scrape)

On first run, log in and scrape all birthdays:

```bash
# Manual login (opens browser for you to log in)
fuckzuck scrape --manual-login

# Or with credentials in .env
fuckzuck scrape --no-headless
```

This stores all your friends' birthdays in `.data/birthdays.json`. You only need to do this once (or periodically to pick up new friends).

## Usage

### Commands

**`scrape`** — One-time scrape of all birthdays from Facebook, stored locally:

```bash
fuckzuck scrape
fuckzuck scrape --manual-login     # manual browser login
fuckzuck scrape --no-headless      # visible browser window
```

**`check`** — Check stored birthdays for today and send notifications (no Facebook access):

```bash
fuckzuck check                     # notify via email + SMS
fuckzuck check --dry-run           # just print, don't notify
```

**`live`** — Live scrape today's birthdays from Facebook and notify (also saves to store):

```bash
fuckzuck live                      # scrape + notify
fuckzuck live --dry-run            # scrape + print only
fuckzuck live --manual-login       # manual login
```

**`status`** — Show stored birthday data info:

```bash
fuckzuck status
```

### Recommended workflow

1. **Once**: `fuckzuck scrape --manual-login` (scrape all birthdays)
2. **Daily cron**: `fuckzuck check` (notify from stored data, no Facebook access)
3. **Periodically**: `fuckzuck scrape` (refresh to pick up new friends)

## Scheduling

### cron (Linux/macOS)

Run daily check at 8 AM (no Facebook access needed):

```bash
crontab -e
```

Add:

```
0 8 * * * cd /path/to/FuckZuck && /path/to/python -m fuckzuck.main check
```

Monthly re-scrape at 3 AM on the 1st:

```
0 3 1 * * cd /path/to/FuckZuck && /path/to/python -m fuckzuck.main scrape
```

## Fallback: manual HTML paste

If scraping fails:

1. Visit [Facebook birthdays](https://www.facebook.com/events/birthdays/)
2. Scroll to load all birthdays
3. Right-click the birthdays content div → Inspect → Copy element
4. Paste into `birthdays_html.html` in the project root
5. Run `fuckzuck live` (it will parse from the file)

## Project structure

```
FuckZuck/
├── src/fuckzuck/
│   ├── auth.py       # stealth login, persistent browser profile
│   ├── birthdays.py  # scrape & parse birthdays
│   ├── main.py       # CLI entry point (scrape/check/live/status)
│   ├── notify.py     # email + SMS notifications
│   └── store.py      # local birthday JSON storage
├── .auth/            # browser profile (gitignored)
├── .data/            # birthday database (gitignored)
├── .env.example
├── pyproject.toml
└── README.md
```

## License

MIT
