"""Main entry point - orchestrate auth, scrape, store, notify."""

import argparse
import sys

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from fuckzuck.auth import get_authenticated_context
from fuckzuck.birthdays import fetch_all_birthdays, fetch_today_birthdays
from fuckzuck.notify import notify_user
from fuckzuck.store import get_birthday_count, get_last_scraped, load_todays_birthdays, save_birthdays


def _cmd_scrape(args: argparse.Namespace) -> int:
    """One-time scrape: fetch all birthdays from Facebook and store locally."""
    with sync_playwright() as p:
        headless = args.headless
        if args.manual_login:
            headless = False

        try:
            context = get_authenticated_context(
                p, headless=headless, manual_login_only=args.manual_login,
            )
        except Exception as e:
            print(f"Authentication failed: {e}")
            return 1

        try:
            print("Scraping all birthdays from Facebook...")
            birthdays = fetch_all_birthdays(context)
            if not birthdays:
                print("No birthdays found. Facebook may have changed their page structure.")
                print("Try the manual HTML fallback (see README).")
                return 1

            total = save_birthdays(birthdays)
            print(f"Scraped {len(birthdays)} birthdays. Total stored: {total}")
            return 0
        except Exception as e:
            print(f"Scrape failed: {e}")
            return 1
        finally:
            context.close()


def _cmd_check(args: argparse.Namespace) -> int:
    """Check stored birthdays for today and notify."""
    last = get_last_scraped()
    count = get_birthday_count()
    if last is None or count == 0:
        print("No stored birthdays. Run 'fuckzuck scrape' first.")
        return 1

    print(f"Using stored data ({count} birthdays, last scraped: {last})")
    birthdays = load_todays_birthdays()

    if not birthdays:
        print("No birthdays today.")
        return 0

    print(f"Today's birthdays ({len(birthdays)}):")
    for b in birthdays:
        print(f"  - {b.name} ({b.month}/{b.day}) {b.profile_url or ''}")

    if args.dry_run:
        return 0

    email_ok, sms_ok = notify_user(birthdays)
    if email_ok:
        print("Email notification sent.")
    if sms_ok:
        print("SMS notification sent.")

    return 0


def _cmd_live(args: argparse.Namespace) -> int:
    """Live scrape today's birthdays from Facebook and notify."""
    with sync_playwright() as p:
        headless = args.headless
        if args.manual_login:
            headless = False

        try:
            context = get_authenticated_context(
                p, headless=headless, manual_login_only=args.manual_login,
            )
        except Exception as e:
            print(f"Authentication failed: {e}")
            return 1

        try:
            birthdays = fetch_today_birthdays(context)
            if not birthdays:
                print("No birthdays today.")
                return 0

            print(f"Today's birthdays ({len(birthdays)}):")
            for b in birthdays:
                print(f"  - {b.name} ({b.month}/{b.day}) {b.profile_url or ''}")

            # Also save to local store for future use
            save_birthdays(birthdays)

            if args.dry_run:
                return 0

            email_ok, sms_ok = notify_user(birthdays)
            if email_ok:
                print("Email notification sent.")
            if sms_ok:
                print("SMS notification sent.")

            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1
        finally:
            context.close()


def _cmd_status(_args: argparse.Namespace) -> int:
    """Show status of stored birthday data."""
    last = get_last_scraped()
    count = get_birthday_count()
    todays = load_todays_birthdays()

    if last is None:
        print("No birthday data stored. Run 'fuckzuck scrape' to populate.")
    else:
        print(f"Stored birthdays: {count}")
        print(f"Last scraped: {last}")
        if todays:
            print(f"Today's birthdays ({len(todays)}):")
            for b in todays:
                print(f"  - {b.name} ({b.month}/{b.day})")
        else:
            print("No birthdays today.")
    return 0


def main() -> int:
    """Run the birthday bot."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="FuckZuck - Facebook birthday scraper and notifier",
    )
    subparsers = parser.add_subparsers(dest="command")

    # scrape - one-time full scrape
    scrape_p = subparsers.add_parser("scrape", help="Scrape all birthdays from Facebook and store locally")
    scrape_p.add_argument("--manual-login", action="store_true", help="Use manual browser login")
    scrape_p.add_argument("--headless", action="store_true", default=True)
    scrape_p.add_argument("--no-headless", action="store_false", dest="headless")

    # check - notify from stored data (for daily cron)
    check_p = subparsers.add_parser("check", help="Check stored birthdays for today and notify")
    check_p.add_argument("--dry-run", action="store_true", help="Print birthdays only, don't notify")

    # live - scrape today + notify (fallback if store is empty)
    live_p = subparsers.add_parser("live", help="Live scrape today's birthdays from Facebook and notify")
    live_p.add_argument("--manual-login", action="store_true", help="Use manual browser login")
    live_p.add_argument("--headless", action="store_true", default=True)
    live_p.add_argument("--no-headless", action="store_false", dest="headless")
    live_p.add_argument("--dry-run", action="store_true", help="Print birthdays only, don't notify")

    # status - show stored data info
    subparsers.add_parser("status", help="Show status of stored birthday data")

    args = parser.parse_args()

    if args.command == "scrape":
        return _cmd_scrape(args)
    elif args.command == "check":
        return _cmd_check(args)
    elif args.command == "live":
        return _cmd_live(args)
    elif args.command == "status":
        return _cmd_status(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
