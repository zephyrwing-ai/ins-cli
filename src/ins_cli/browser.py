"""Playwright browser manager — reuses logged-in Chrome session."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Default Chrome profile paths on macOS
_CHROME_CANARY = Path.home() / "Library/Application Support/Google/Chrome Canary"
_CHROME_STABLE = Path.home() / "Library/Application Support/Google/Chrome"

INSTAGRAM_URL = "https://www.instagram.com/"


def _find_chrome_user_data_dir() -> Path | None:
    if (_CHROME_CANARY / "Default").exists():
        return _CHROME_CANARY
    if (_CHROME_STABLE / "Default").exists():
        return _CHROME_STABLE
    return None


def _find_chrome_executable() -> str | None:
    for path in [
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]:
        if Path(path).exists():
            return path
    return None


def launch_browser():
    """
    Launch Playwright Chromium connected to the user's Chrome profile.

    This reuses the logged-in session so no login is needed.
    Returns (playwright, browser, context, page).
    """
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()

    user_data_dir = _find_chrome_user_data_dir()
    chrome_exe = _find_chrome_executable()

    if not chrome_exe:
        # Fallback: let Playwright use its own Chromium
        logger.debug("Chrome not found, using Playwright's built-in Chromium")
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(INSTAGRAM_URL)
        return pw, browser, context, page

    # Use user's Chrome with their profile (reuses login session)
    context = pw.chromium.launch_persistent_context(
        str(user_data_dir),
        executable_path=chrome_exe,
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
        channel="chromium",
    )

    page = context.new_page()
    page.goto(INSTAGRAM_URL)
    page.wait_for_load_state("networkidle")

    return pw, context, context, page


def close_browser(pw, context) -> None:
    try:
        context.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass
