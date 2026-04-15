"""Posting module - post Happy Birthday to friend's wall."""

import time

from playwright.sync_api import BrowserContext, Page

from fuckzuck.birthdays import Birthday


# Selectors for Facebook's post composer (DOM changes frequently - multiple fallbacks)
POST_COMPOSER_SELECTORS = [
    '[aria-label*="Write something"]',
    '[aria-label*="What\'s on your mind"]',
    '[aria-label*="Create a post"]',
    '[contenteditable="true"][role="textbox"]',
    'div[role="button"][tabindex="0"]',
    '[data-lexical-editor="true"]',
    'div[aria-multiline="true"]',
]
POST_BUTTON_SELECTORS = [
    '[aria-label="Post"]',
    '[aria-label="Publish"]',
    'div[aria-label="Post"]',
    'div[role="button"]:has-text("Post")',
    'span:has-text("Post")',
]


def _navigate_to_profile(page: Page, birthday: Birthday) -> bool:
    """Navigate to friend's profile. Returns True if successful."""
    if not birthday.profile_url:
        return False
    try:
        page.goto(birthday.profile_url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)
        return True
    except Exception:
        return False


def _find_and_fill_composer(page: Page, message: str) -> bool:
    """Find the post composer and fill with message. Returns True if successful."""
    for selector in POST_COMPOSER_SELECTORS:
        try:
            el = page.locator(selector).first
            el.wait_for(state="visible", timeout=3000)
            el.click()
            page.wait_for_timeout(500)
            el.fill("")  # Clear if any placeholder
            el.fill(message)
            page.wait_for_timeout(500)
            return True
        except Exception:
            continue

    # Fallback: try contenteditable
    try:
        editable = page.locator('[contenteditable="true"]').first
        editable.wait_for(state="visible", timeout=2000)
        editable.click()
        page.keyboard.type(message, delay=50)
        return True
    except Exception:
        pass

    return False


def _click_post_button(page: Page) -> bool:
    """Click the Post/Publish button. Returns True if successful."""
    for selector in POST_BUTTON_SELECTORS:
        try:
            btn = page.locator(selector).first
            btn.wait_for(state="visible", timeout=2000)
            btn.click()
            page.wait_for_timeout(2000)
            return True
        except Exception:
            continue
    return False


def post_to_wall(context: BrowserContext, birthday: Birthday) -> tuple[bool, str]:
    """
    Post "Happy Birthday! [Name]" to the friend's wall.
    Returns (success, error_message).
    """
    if not birthday.profile_url:
        return (False, "No profile URL")

    page = context.new_page()
    try:
        if not _navigate_to_profile(page, birthday):
            return (False, "Failed to navigate to profile")

        message = f"Happy Birthday! {birthday.name}"
        if not _find_and_fill_composer(page, message):
            return (False, "Could not find post composer")

        if not _click_post_button(page):
            return (False, "Could not find Post button")

        return (True, "")
    except Exception as e:
        return (False, str(e))
    finally:
        page.close()


def post_to_all(
    context: BrowserContext,
    birthdays: list[Birthday],
    *,
    delay_seconds: float = 3.0,
    limit: int | None = None,
) -> tuple[int, int, list[str]]:
    """
    Post to each birthday person's wall.
    Returns (success_count, fail_count, list of error messages for failures).
    """
    to_post = birthdays[:limit] if limit else birthdays
    success_count = 0
    fail_count = 0
    errors: list[str] = []

    for i, bd in enumerate(to_post):
        ok, err = post_to_wall(context, bd)
        if ok:
            success_count += 1
        else:
            fail_count += 1
            errors.append(f"{bd.name}: {err}")

        # Delay between posts to avoid rate limiting
        if i < len(to_post) - 1:
            time.sleep(delay_seconds)

    return (success_count, fail_count, errors)
