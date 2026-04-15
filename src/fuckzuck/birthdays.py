"""Birthday fetching - scrape from Facebook, parse, filter to today."""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from playwright.sync_api import BrowserContext, Page

FB_BIRTHDAYS_URL = "https://www.facebook.com/events/birthdays/"
FALLBACK_HTML_PATH = Path(__file__).resolve().parent.parent.parent / "birthdays_html.html"


@dataclass
class Birthday:
    """A contact's birthday."""

    name: str
    month: int
    day: int
    profile_url: str | None = None


def _parse_tooltip(tooltip: str) -> tuple[str, int, int] | None:
    """Parse 'Name (month/day)' or 'Name (month/day/year)' from tooltip. Returns (name, month, day) or None."""
    # Match: Name (M/D) or Name (M/D/YYYY)
    match = re.match(r"^(.+?)\s*\((\d{1,2})/(\d{1,2})(?:/\d{4})?\)\s*$", tooltip.strip())
    if match:
        name, month, day = match.group(1).strip(), int(match.group(2)), int(match.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return (name, month, day)
    return None


def _extract_from_page(page: Page) -> list[Birthday]:
    """Extract all birthdays from the birthdays page DOM."""
    results: list[Birthday] = []
    today = date.today()
    today_month, today_day = today.month, today.day

    # Strategy 1: li a with data-tooltip-content (Cory Walker approach)
    links = page.locator('li a[data-tooltip-content]')
    count = links.count()
    for i in range(count):
        el = links.nth(i)
        try:
            tooltip = el.get_attribute("data-tooltip-content")
            href = el.get_attribute("href")
            if tooltip:
                parsed = _parse_tooltip(tooltip)
                if parsed:
                    name, month, day = parsed
                    if month == today_month and day == today_day:
                        profile_url = None
                        if href:
                            profile_url = href if href.startswith("http") else f"https://www.facebook.com{href.lstrip('/')}"
                        results.append(Birthday(name=name, month=month, day=day, profile_url=profile_url))
        except Exception:
            continue

    # Strategy 2: fallback - look for #birthdays_content and parse structure
    if not results:
        content = page.locator("#birthdays_content")
        if content.count() > 0:
            # Get all links with name patterns
            all_links = content.locator("a[href*='facebook.com']")
            for i in range(all_links.count()):
                el = all_links.nth(i)
                try:
                    text = el.inner_text()
                    parsed = _parse_tooltip(text)
                    if parsed:
                        name, month, day = parsed
                        if month == today_month and day == today_day:
                            href = el.get_attribute("href")
                            profile_url = None
                            if href:
                                profile_url = href if href.startswith("http") else f"https://www.facebook.com{href.lstrip('/')}"
                            results.append(Birthday(name=name, month=month, day=day, profile_url=profile_url))
                except Exception:
                    continue

    return results


def _scroll_to_load_all(page: Page) -> None:
    """Scroll to bottom to lazy-load all birthdays."""
    for _ in range(12):  # ~12 months of birthdays
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)
        # Check if we've reached the bottom
        at_bottom = page.evaluate(
            "window.innerHeight + window.scrollY >= document.body.scrollHeight - 100"
        )
        if at_bottom:
            break


def fetch_today_birthdays_from_browser(context: BrowserContext) -> list[Birthday]:
    """
    Fetch today's birthdays by scraping the Facebook birthdays page.
    Requires an authenticated context.
    """
    page = context.new_page()
    try:
        page.goto(FB_BIRTHDAYS_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)

        _scroll_to_load_all(page)
        page.wait_for_timeout(1000)

        return _extract_from_page(page)
    finally:
        page.close()


def parse_birthdays_from_html(html_content: str) -> list[Birthday]:
    """Parse birthdays from pasted HTML (e.g. from #birthdays_content). Filters to today."""
    today = date.today()
    today_month, today_day = today.month, today.day
    results: list[Birthday] = []

    # Match links with tooltip: Name (M/D) or similar
    tooltip_pattern = re.compile(
        r'data-tooltip-content="([^"]+)"',
        re.IGNORECASE,
    )
    href_pattern = re.compile(r'href="(https?://[^"]*facebook\.com[^"]*)"', re.IGNORECASE)

    # Simple split by common tag boundaries to get chunks with both tooltip and href
    chunks = re.split(r"<a\s", html_content, flags=re.IGNORECASE)
    for chunk in chunks:
        tooltip_m = tooltip_pattern.search(chunk)
        href_m = href_pattern.search(chunk)
        if tooltip_m:
            parsed = _parse_tooltip(tooltip_m.group(1))
            if parsed:
                name, month, day = parsed
                if month == today_month and day == today_day:
                    profile_url = href_m.group(1) if href_m else None
                    results.append(Birthday(name=name, month=month, day=day, profile_url=profile_url))

    return results


def fetch_today_birthdays(
    context: BrowserContext | None,
    *,
    fallback_html_path: Path | None = FALLBACK_HTML_PATH,
) -> list[Birthday]:
    """
    Fetch today's birthdays. Uses browser if context provided; otherwise
    falls back to parsing from birthdays_html.html if it exists.
    """
    if context:
        try:
            return fetch_today_birthdays_from_browser(context)
        except Exception as e:
            print(f"Browser fetch failed: {e}. Trying fallback HTML...")

    path = fallback_html_path or FALLBACK_HTML_PATH
    if path.exists():
        html = path.read_text(encoding="utf-8", errors="replace")
        return parse_birthdays_from_html(html)

    return []
