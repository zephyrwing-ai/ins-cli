"""Browser-based write operations — uses Playwright to control Chrome."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from .browser import INSTAGRAM_URL, close_browser, launch_browser

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_VIDEO_EXTS = {".mp4"}


def _resolve_media(media_path: str) -> Path:
    p = Path(media_path).resolve()
    if not p.exists():
        raise SystemExit(f"File not found: {p}")
    if p.suffix.lower() not in (SUPPORTED_IMAGE_EXTS | SUPPORTED_VIDEO_EXTS):
        raise SystemExit(f"Unsupported format: {p.suffix}. Use jpg/png/webp/mp4")
    return p


def _button(page, *names: str):
    pattern = re.compile("|".join(re.escape(name) for name in names), re.I)
    return page.get_by_role("button", name=pattern).first


def _click_next(page) -> None:
    page.locator(
        'button:has-text("Next"), '
        'div[role="button"]:has-text("Next"), '
        'button:has-text("下一步"), '
        'div[role="button"]:has-text("下一步")'
    ).first.click()


def _click_next_if_present(page) -> None:
    locator = page.locator(
        'button:has-text("Next"), '
        'div[role="button"]:has-text("Next"), '
        'button:has-text("下一步"), '
        'div[role="button"]:has-text("下一步")'
    ).first
    if locator.count() and locator.is_visible(timeout=2000):
        locator.click()


def _click_share(page) -> None:
    page.locator(
        'button:has-text("Share"), '
        'div[role="button"]:has-text("Share"), '
        'button:has-text("分享"), '
        'div[role="button"]:has-text("分享")'
    ).first.click()


def _open_post_composer(page) -> None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    page.goto(f"{INSTAGRAM_URL}create/select/")
    page.wait_for_load_state("domcontentloaded", timeout=15000)
    try:
        page.locator('input[type="file"]').first.wait_for(state="attached", timeout=8000)
        return
    except PlaywrightTimeoutError:
        pass

    create_btn = page.locator(
        'a[href="/create/select/"], '
        'a:has(svg[aria-label="New post"]), '
        'a:has(svg[aria-label="Create"]), '
        '[role="button"]:has(svg[aria-label="New post"]), '
        '[role="button"]:has(svg[aria-label="Create"]), '
        '[aria-label="Create"], '
        '[aria-label="New post"], '
        'svg[aria-label="New post"]'
    ).first
    create_btn.click(force=True)


def _fill_caption(page, caption: str) -> None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    selectors = [
        '[aria-label="Write a caption..."]',
        '[aria-label="Write a caption…"]',
        '[aria-label="撰写说明文字……"]',
        '[aria-label="撰写说明文字..."]',
        'textarea[placeholder="Write a caption..."]',
        'textarea[placeholder="Write a caption…"]',
        '[contenteditable="true"][role="textbox"]',
        '[contenteditable="true"]',
    ]
    for selector in selectors:
        locator = page.locator(selector).last
        try:
            locator.wait_for(state="visible", timeout=3000)
            try:
                locator.fill(caption, timeout=3000)
            except Exception:
                locator.click()
                page.keyboard.insert_text(caption)
            return
        except PlaywrightTimeoutError:
            continue
    textbox = page.get_by_role("textbox").last
    textbox.click(timeout=5000)
    page.keyboard.insert_text(caption)


def _wait_for_post_shared(page) -> None:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    messages = [
        "Your post has been shared",
        "Your reel has been shared",
        "你的帖子已分享",
        "你的 Reels 已分享",
    ]
    for message in messages:
        try:
            page.get_by_text(message, exact=False).first.wait_for(
                state="visible",
                timeout=8000,
            )
            return
        except PlaywrightTimeoutError:
            continue
    page.wait_for_timeout(5000)


def post_image(media: str, caption: str = "") -> str:
    """Post a single image to Instagram feed via browser automation."""
    media_path = _resolve_media(media)

    pw, browser, context, page = launch_browser()
    try:
        # Wait for page to load
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        time.sleep(2)

        # Open the post composer.
        _open_post_composer(page)
        time.sleep(2)

        # Upload file via the hidden file input
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(media_path))
        time.sleep(3)

        # Click "Next" (first time — after crop/adjust)
        _click_next(page)
        time.sleep(2)

        # Some Instagram variants have a second "Next" step after filters.
        _click_next_if_present(page)
        time.sleep(2)

        # Type caption
        if caption:
            _fill_caption(page, caption)
            time.sleep(1)

        # Click "Share"
        _click_share(page)

        # Wait for the success indicator when Instagram shows one.
        _wait_for_post_shared(page)
        time.sleep(2)

        return "Posted successfully"

    except Exception as e:
        logger.error("Post failed: %s", e)
        raise SystemExit(f"Post failed: {e}")
    finally:
        close_browser(pw, browser)


def post_story(media: str) -> str:
    """Post a story via browser automation."""
    media_path = _resolve_media(media)

    pw, browser, context, page = launch_browser()
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        time.sleep(2)

        # Click the "Create" button
        create_btn = page.locator(
            '[aria-label="Create"], '
            '[aria-label="New post"], '
            'svg[aria-label="New post"]'
        ).first
        create_btn.click()
        time.sleep(2)

        # Upload file
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(media_path))
        time.sleep(3)

        # Look for "Your story" button
        story_btn = page.locator(
            'button:has-text("Your story"), '
            '[aria-label="Your story"]'
        ).first
        story_btn.click()

        page.wait_for_timeout(5000)
        return "Story posted successfully"

    except Exception as e:
        logger.error("Story post failed: %s", e)
        raise SystemExit(f"Story post failed: {e}")
    finally:
        close_browser(pw, browser)


def comment_on_post(username: str, text: str, post_index: int = 1) -> str:
    """Comment on a user's post via browser automation."""
    pw, browser, context, page = launch_browser()
    try:
        page.goto(f"{INSTAGRAM_URL}{username}/", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(5000)

        posts = page.locator(
            'a[href^="/p/"], '
            'a[href^="/reel/"], '
            'a[href*="/p/"], '
            'a[href*="/reel/"]'
        )
        if posts.count() < post_index:
            raise RuntimeError(f"Post index {post_index} not found for @{username}")

        post_href = posts.nth(post_index - 1).get_attribute("href")
        if not post_href:
            raise RuntimeError(f"Post index {post_index} has no link for @{username}")
        page.goto(f"https://www.instagram.com{post_href}", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(5000)

        textarea = page.locator(
            'textarea[aria-label="Add a comment…"]:visible, '
            'textarea[aria-label="Add a comment..."]:visible, '
            'textarea[placeholder="Add a comment…"]:visible, '
            'textarea[placeholder="Add a comment..."]:visible, '
            'textarea:visible'
        ).first
        textarea.click(timeout=10000)
        textarea.fill(text)

        page.locator(
            'button:has-text("Post"), '
            'div[role="button"]:has-text("Post"), '
            'button:has-text("发布"), '
            'div[role="button"]:has-text("发布")'
        ).first.click()
        page.wait_for_timeout(5000)

        return f"Commented on @{username}'s post #{post_index}: {text}"

    except Exception as e:
        logger.error("Comment failed: %s", e)
        raise SystemExit(f"Comment failed: {e}")
    finally:
        close_browser(pw, browser)
