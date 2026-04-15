"""Authentication module - login, session persistence, manual fallback."""

import os
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page

AUTH_DIR = Path(__file__).resolve().parent.parent.parent / ".auth"
STATE_PATH = AUTH_DIR / "state.json"
FB_LOGIN_URL = "https://www.facebook.com/login"
FB_HOME_URL = "https://www.facebook.com/"
FB_BIRTHDAYS_URL = "https://www.facebook.com/events/birthdays/"


def _ensure_auth_dir() -> None:
    """Create .auth directory if it doesn't exist."""
    AUTH_DIR.mkdir(parents=True, exist_ok=True)


def _is_logged_in(page: Page) -> bool:
    """Check if we're logged into Facebook by verifying we're not on login page."""
    url = page.url
    # Redirected away from login and not on a login/checkpoint page
    if "login" in url or "checkpoint" in url.lower():
        return False
    # Check for common logged-in indicators
    try:
        # Feed or home typically has this
        page.wait_for_load_state("domcontentloaded", timeout=5000)
        return True
    except Exception:
        return False


def _try_auto_login(page: Page, email: str, password: str) -> bool:
    """Attempt automated login. Returns True if successful."""
    try:
        page.goto(FB_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=10000)

        # Fill email - Facebook uses id="email" or placeholder
        email_input = page.locator('input[name="email"], input[id="email"]').first
        email_input.wait_for(state="visible", timeout=5000)
        email_input.fill(email)

        # Fill password
        pass_input = page.locator('input[name="pass"], input[id="pass"]').first
        pass_input.fill(password)

        # Click login
        login_btn = page.locator('button[name="login"], input[name="login"]').first
        login_btn.click()

        # Wait for navigation away from login
        page.wait_for_url(
            lambda u: "login" not in u and "checkpoint" not in u.lower(),
            timeout=15000,
        )
        page.wait_for_load_state("domcontentloaded", timeout=5000)

        return _is_logged_in(page)
    except Exception:
        return False


def _manual_login(page: Page) -> bool:
    """Launch headed browser for manual login. User completes login, then continues."""
    print("Manual login: Complete the login in the browser, then press Enter here...")
    page.pause()
    page.wait_for_load_state("domcontentloaded", timeout=5000)
    return _is_logged_in(page)


def get_authenticated_context(
    playwright,
    *,
    headless: bool = True,
    manual_login_only: bool = False,
) -> tuple[Browser, BrowserContext]:
    """
    Get an authenticated browser context.
    Tries: load saved state -> auto login -> manual login.
    """
    _ensure_auth_dir()
    browser: Browser = playwright.chromium.launch(headless=headless)
    state_file = str(STATE_PATH)

    # Try loading saved state first (unless manual_login_only)
    if not manual_login_only and STATE_PATH.exists():
        try:
            context = browser.new_context(storage_state=state_file)
            page = context.new_page()
            page.goto(FB_BIRTHDAYS_URL, wait_until="domcontentloaded", timeout=15000)
            if _is_logged_in(page):
                page.close()
                return (browser, context)
            context.close()
        except Exception:
            pass

    # Need to log in - use headed for manual fallback visibility
    context = browser.new_context()
    page = context.new_page()

    try:
        if manual_login_only:
            page.goto(FB_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            success = _manual_login(page)
        else:
            email = os.environ.get("FB_EMAIL", "")
            password = os.environ.get("FB_PASSWORD", "")
            if email and password:
                success = _try_auto_login(page, email, password)
                if not success:
                    print("Automated login failed (2FA/captcha?). Falling back to manual login...")
                    success = _manual_login(page)
            else:
                print("FB_EMAIL/FB_PASSWORD not set. Using manual login...")
                page.goto(FB_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
                success = _manual_login(page)

        if not success:
            raise RuntimeError("Login was not successful.")

        # Save state for next run
        context.storage_state(path=state_file)
        page.close()
        return (browser, context)
    except Exception:
        page.close()
        context.close()
        raise
