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
    """Extract Instagram cookies from the default browser via browser_cookie3."""
    try:
        import browser_cookie3 as bc3
    except ImportError:
        logger.debug("browser_cookie3 not installed, skipping browser extraction")
        return None

    for browser_name in ("chrome", "brave", "firefox", "safari", "edge"):
        try:
            loader = getattr(bc3, browser_name)
            jar = loader(domain_name=".instagram.com")
            cookies = {c.name: c.value for c in jar if "instagram.com" in (c.domain or "")}
            if cookies.get("sessionid") or cookies.get("ds_user_id"):
                logger.debug("Extracted cookies from %s", browser_name)
                return cookies
        except Exception:
            continue

    logger.debug("No usable cookies found in any browser")
    return None


def get_auth_headers(cookies: dict[str, str]) -> dict[str, str]:
    """Build the standard Instagram private API auth headers from cookies."""
    csrf = cookies.get("csrftoken", "")
    return {
        "X-IG-App-ID": "936619743392459",
        "X-CSRFToken": csrf,
        "X-Instagram-AJAX": "1",
        "Cookie": cookies_to_header(cookies),
        "Referer": "https://www.instagram.com/",
        "Origin": "https://www.instagram.com",
    }
