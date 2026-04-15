"""Main entry point - orchestrate auth, fetch, post, notify."""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from fuckzuck.auth import get_authenticated_context
from fuckzuck.birthdays import Birthday, fetch_today_birthdays
from fuckzuck.notify import notify_user
from fuckzuck.post import post_to_all


def main() -> int:
    """Run the birthday bot."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="FuckZuck - Birthday bot for Meta/Facebook")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and print birthdays only; no posts, no notifications",
    )
    parser.add_argument(
        "--manual-login",
        action="store_true",
        help="Skip automated login, go straight to manual login",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of birthday posts (for testing)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser headless (default: True)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser with visible window",
    )
    args = parser.parse_args()

    headless = args.headless
    if args.manual_login:
        headless = False  # Must show browser for manual login

    with sync_playwright() as p:
        try:
            browser, context = get_authenticated_context(
                p,
                headless=headless,
                manual_login_only=args.manual_login,
            )
        except Exception as e:
            print(f"Authentication failed: {e}")
            return 1

        try:
            birthdays = fetch_today_birthdays(context)
            if not birthdays:
                print("No birthdays today.")
                context.close()
                browser.close()
                return 0

            print(f"Today's birthdays ({len(birthdays)}): {', '.join(b.name for b in birthdays)}")

            if args.dry_run:
                for b in birthdays:
                    print(f"  - {b.name} ({b.month}/{b.day}) {b.profile_url or '(no profile URL)'}")
                context.close()
                browser.close()
                return 0

            success, fail, errors = post_to_all(
                context,
                birthdays,
                delay_seconds=3.0,
                limit=args.limit,
            )
            print(f"Posted: {success} success, {fail} failed")
            for err in errors:
                print(f"  Error: {err}")

            email_ok, sms_ok = notify_user(birthdays, post_success=success, post_fail=fail, errors=errors)
            if email_ok:
                print("Email notification sent.")
            if sms_ok:
                print("SMS notification sent.")

            context.close()
            browser.close()
            return 0
        except Exception as e:
            print(f"Error: {e}")
            context.close()
            browser.close()
            return 1


if __name__ == "__main__":
    sys.exit(main())
