"""Cookie and authentication management for Instagram."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".ins-cli"
COOKIE_FILE = CONFIG_DIR / "cookies.json"
COOKIE_TTL_DAYS = 7


def get_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def save_cookies(cookies: dict[str, str]) -> None:
    get_config_dir()
    payload = {**cookies, "saved_at": time.time()}
    COOKIE_FILE.write_text(json.dumps(payload, indent=2))
    COOKIE_FILE.chmod(0o600)
    logger.debug("Saved cookies to %s", COOKIE_FILE)


def load_cookies() -> dict[str, str] | None:
    if not COOKIE_FILE.exists():
        return None
    try:
        data = json.loads(COOKIE_FILE.read_text())
        saved_at = data.pop("saved_at", 0)
        if saved_at and (time.time() - float(saved_at)) > COOKIE_TTL_DAYS * 86400:
            logger.info("Cookies older than %d days, consider re-login", COOKIE_TTL_DAYS)
        return data
    except (OSError, json.JSONDecodeError) as e:
        logger.debug("Failed to load cookies: %s", e)
        return None


def clear_cookies() -> None:
    if COOKIE_FILE.exists():
        COOKIE_FILE.unlink()
        logger.debug("Cleared cookies")


def cookies_to_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def extract_browser_cookies() -> dict[str, str] | None:
    """Extract Instagram cookies from stable Google Chrome via browser_cookie3."""
    try:
        import browser_cookie3 as bc3
    except ImportError:
        logger.debug("browser_cookie3 not installed, skipping browser extraction")
        return None

    try:
        jar = bc3.chrome(domain_name=".instagram.com")
        cookies = {c.name: c.value for c in jar if "instagram.com" in (c.domain or "")}
        if cookies.get("sessionid") or cookies.get("ds_user_id"):
            logger.debug("Extracted cookies from Google Chrome")
            return cookies
    except Exception as e:
        logger.debug("Failed to extract Chrome cookies: %s", e)

    try:
        cookies = _extract_chrome_cookies_with_playwright()
        if cookies:
            return cookies
    except Exception as e:
        logger.debug("Failed to extract Chrome cookies with Playwright: %s", e)

    logger.debug("No usable Instagram cookies found in Google Chrome")
    return None


def _extract_chrome_cookies_with_playwright() -> dict[str, str] | None:
    from playwright.sync_api import sync_playwright

    from .browser import INSTAGRAM_URL, _find_chrome_executable, _find_chrome_user_data_dir

    chrome_exe = _find_chrome_executable()
    user_data_dir = _find_chrome_user_data_dir()
    if not chrome_exe or not user_data_dir:
        return None

    pw = sync_playwright().start()
    try:
        context = pw.chromium.launch_persistent_context(
            str(user_data_dir),
            executable_path=chrome_exe,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.new_page()
        page.goto(INSTAGRAM_URL)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)
        cookies = {
            cookie["name"]: cookie["value"]
            for cookie in context.cookies(INSTAGRAM_URL)
            if "instagram.com" in cookie.get("domain", "")
        }
        context.close()
        if cookies.get("sessionid") or cookies.get("ds_user_id"):
            logger.debug("Extracted cookies from Google Chrome with Playwright")
            return cookies
        return None
    finally:
        pw.stop()


def get_auth_headers(cookies: dict[str, str]) -> dict[str, str]:
    """Build the standard Instagram private API auth headers from cookies."""
    csrf = cookies.get("csrftoken", "")
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/148.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "X-IG-App-ID": "936619743392459",
        "X-ASBD-ID": "129477",
        "X-CSRFToken": csrf,
        "X-Instagram-AJAX": "1",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookies_to_header(cookies),
        "Referer": "https://www.instagram.com/",
        "Origin": "https://www.instagram.com",
    }
