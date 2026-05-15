"""Playwright browser manager — reuses logged-in Google Chrome session."""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default stable Google Chrome profile path on macOS.
_CHROME_STABLE = Path.home() / "Library/Application Support/Google/Chrome"

INSTAGRAM_URL = "https://www.instagram.com/"


def _goto_instagram(page) -> None:
    try:
        page.goto(INSTAGRAM_URL, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        if "Timeout" not in str(e):
            raise
        logger.debug("Instagram navigation timed out; continuing with current page")


def _find_chrome_user_data_dir() -> Path | None:
    override = os.environ.get("INS_CHROME_USER_DATA_DIR")
    if override:
        path = Path(override).expanduser()
        if path.exists():
            return path

    if (_CHROME_STABLE / "Default").exists():
        return _CHROME_STABLE
    return None


def _find_chrome_executable() -> str | None:
    override = os.environ.get("INS_CHROME_EXECUTABLE")
    if override and Path(override).expanduser().exists():
        return str(Path(override).expanduser())

    candidates: list[str]
    system = platform.system()
    if system == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
    elif system == "Windows":
        candidates = [
            str(Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe"),
            str(Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe"),
            str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"),
        ]
    else:
        candidates = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/snap/bin/google-chrome",
        ]

    for path in candidates:
        if Path(path).exists():
            return path
    return None


def _cookie_context_items() -> list[dict[str, Any]]:
    try:
        from .auth import load_cookies
    except ImportError:
        return []

    saved = load_cookies() or {}
    return [
        {
            "name": name,
            "value": value,
            "domain": ".instagram.com",
            "path": "/",
            "secure": True,
            "httpOnly": name in {"sessionid"},
            "sameSite": "Lax",
        }
        for name, value in saved.items()
        if name != "saved_at"
    ]


def launch_browser():
    """
    Launch Playwright Chromium connected to the user's Chrome profile.

    This reuses the logged-in session so no login is needed.
    Returns (playwright, browser, context, page).
    """
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()

    chrome_exe = _find_chrome_executable()
    user_data_dir = _find_chrome_user_data_dir()

    if not chrome_exe:
        pw.stop()
        raise SystemExit(
            "Google Chrome was not found. Install stable Google Chrome, or set "
            "INS_CHROME_EXECUTABLE to its executable path. Chrome Canary is not used."
        )

    cookies = _cookie_context_items()
    if cookies:
        logger.debug("Launching stable Google Chrome with saved Instagram cookies")
        browser = pw.chromium.launch(
            executable_path=chrome_exe,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()
        _goto_instagram(page)
        return pw, browser, context, page

    if not user_data_dir:
        pw.stop()
        raise SystemExit(
            "Google Chrome profile was not found. Open stable Google Chrome once, "
            "log in to Instagram, then retry. You can also set INS_CHROME_USER_DATA_DIR."
        )

    # Use user's Chrome with their profile (reuses login session)
    logger.debug("Launching stable Google Chrome: %s", chrome_exe)
    try:
        context = pw.chromium.launch_persistent_context(
            str(user_data_dir),
            executable_path=chrome_exe,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.new_page()
        _goto_instagram(page)

        return pw, context, context, page
    except Exception as e:
        if "ProcessSingleton" not in str(e) and "SingletonLock" not in str(e):
            pw.stop()
            raise
        logger.debug("Chrome profile is in use; launching stable Chrome with saved cookies")

    browser = pw.chromium.launch(
        executable_path=chrome_exe,
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context()
    page = context.new_page()
    _goto_instagram(page)
    return pw, browser, context, page


def close_browser(pw, context) -> None:
    try:
        context.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass
