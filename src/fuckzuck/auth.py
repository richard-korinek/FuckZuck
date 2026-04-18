"""Authentication module - stealth login with persistent browser profile."""

import os
import random
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Playwright
from playwright_stealth import Stealth

PROFILE_DIR = Path(__file__).resolve().parent.parent.parent / ".auth" / "chrome-profile"
FB_LOGIN_URL = "https://www.facebook.com/login"
FB_HOME_URL = "https://www.facebook.com/"
FB_BIRTHDAYS_URL = "https://www.facebook.com/events/birthdays/"

# Common real-world viewport sizes
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1680, "height": 1050},
]

LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-infobars",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
]


def _ensure_profile_dir() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _is_logged_in(page: Page) -> bool:
    """Check if we're logged into Facebook."""
    url = page.url
    if "login" in url or "checkpoint" in url.lower():
        return False
    try:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
        return True
    except Exception:
        return False


def _human_type(page: Page, selector: str, text: str) -> None:
    """Type with human-like delays."""
    el = page.locator(selector).first
    el.wait_for(state="visible", timeout=5000)
    el.click()
    page.wait_for_timeout(random.randint(200, 500))
    for char in text:
        page.keyboard.type(char, delay=random.randint(50, 150))
        if random.random() < 0.05:
            page.wait_for_timeout(random.randint(300, 800))


def _human_delay(page: Page, min_ms: int = 1000, max_ms: int = 3000) -> None:
    """Wait a random human-like duration."""
    page.wait_for_timeout(random.randint(min_ms, max_ms))


def _try_auto_login(page: Page, email: str, password: str) -> bool:
    """Attempt automated login with human-like behavior."""
    try:
        page.goto(FB_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=10000)
        _human_delay(page, 1000, 2000)

        # Random mouse movement before typing
        page.mouse.move(random.randint(100, 400), random.randint(100, 300))
        _human_delay(page, 300, 700)

        _human_type(page, 'input[name="email"], input[id="email"]', email)
        _human_delay(page, 500, 1200)

        _human_type(page, 'input[name="pass"], input[id="pass"]', password)
        _human_delay(page, 400, 900)

        # Move mouse to login button area before clicking
        login_btn = page.locator('button[name="login"], input[name="login"]').first
        box = login_btn.bounding_box()
        if box:
            page.mouse.move(
                box["x"] + box["width"] / 2 + random.randint(-5, 5),
                box["y"] + box["height"] / 2 + random.randint(-3, 3),
            )
            _human_delay(page, 200, 500)
        login_btn.click()

        page.wait_for_url(
            lambda u: "login" not in u and "checkpoint" not in u.lower(),
            timeout=15000,
        )
        page.wait_for_load_state("domcontentloaded", timeout=5000)
        return _is_logged_in(page)
    except Exception:
        return False


def _manual_login(page: Page) -> bool:
    """Open browser for manual login."""
    print("Manual login: Complete the login in the browser, then press Enter here...")
    page.pause()
    page.wait_for_load_state("domcontentloaded", timeout=5000)
    return _is_logged_in(page)


def get_authenticated_context(
    playwright: Playwright,
    *,
    headless: bool = True,
    manual_login_only: bool = False,
) -> BrowserContext:
    """
    Get an authenticated browser context using a persistent Chrome profile.
    Uses playwright-stealth to avoid bot detection.
    Returns a BrowserContext (persistent contexts manage their own browser).
    """
    _ensure_profile_dir()

    viewport = random.choice(VIEWPORTS)
    stealth = Stealth(init_scripts_only=True)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        viewport=viewport,
        args=LAUNCH_ARGS,
        locale="en-US",
        timezone_id=os.environ.get("TZ", "America/Chicago"),
        ignore_default_args=["--enable-automation"],
    )
    stealth.apply_stealth_sync(context)

    # Persistent context always has at least one page
    page = context.pages[0] if context.pages else context.new_page()

    try:
        # Check if already logged in from previous session
        page.goto(FB_BIRTHDAYS_URL, wait_until="domcontentloaded", timeout=15000)
        _human_delay(page, 1000, 2000)

        if _is_logged_in(page):
            page.close()
            return context

        # Need to log in
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
            page.close()
            context.close()
            raise RuntimeError("Login was not successful.")

        page.close()
        return context
    except Exception:
        page.close()
        context.close()
        raise
