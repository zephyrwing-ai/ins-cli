"""Browser-based write operations — uses Playwright to control Chrome."""

from __future__ import annotations

import logging
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


def post_image(media: str, caption: str = "") -> str:
    """Post a single image to Instagram feed via browser automation."""
    media_path = _resolve_media(media)

    pw, browser, context, page = launch_browser()
    try:
        # Wait for page to load
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Click the "Create" / "+" button
        create_btn = page.locator(
            'a[href="/accounts/create/"], '
            '[aria-label="Create"], '
            '[aria-label="New post"], '
            'svg[aria-label="New post"]'
        ).first
        create_btn.click()
        time.sleep(2)

        # Upload file via the hidden file input
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(media_path))
        time.sleep(3)

        # Click "Next" (first time — after crop/adjust)
        page.get_by_role("button", name="Next").first.click()
        time.sleep(2)

        # Click "Next" again (after filters)
        page.get_by_role("button", name="Next").first.click()
        time.sleep(2)

        # Type caption
        if caption:
            caption_area = page.locator(
                '[aria-label="Write a caption..."], '
                'textarea[placeholder="Write a caption..."]'
            ).first
            caption_area.fill(caption)
            time.sleep(1)

        # Click "Share"
        page.get_by_role("button", name="Share").first.click()

        # Wait for the success indicator
        page.wait_for_selector(
            '[aria-label="Your post has been shared"], '
            'text="Your post has been shared"',
            timeout=30000,
        )
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
        page.wait_for_load_state("networkidle")
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
    """Comment on a user's post via the private API in the browser context."""
    pw, browser, context, page = launch_browser()
    try:
        page.wait_for_load_state("networkidle")

        # Use Instagram's internal API from within the browser (has auth cookies)
        result = page.evaluate(f"""
        async () => {{
            const headers = {{
                'X-IG-App-ID': '936619743392459',
            }};
            const opts = {{ credentials: 'include', headers }};

            const r1 = await fetch(
                'https://www.instagram.com/api/v1/users/web_profile_info/?username='
                + encodeURIComponent({username!r}), opts
            );
            if (!r1.ok) throw new Error('User not found: ' + {username!r});
            const userId = (await r1.json())?.data?.user?.id;

            const idx = {post_index - 1};
            const r2 = await fetch(
                'https://www.instagram.com/api/v1/feed/user/' + userId + '/?count=' + (idx + 1),
                opts
            );
            const posts = (await r2.json())?.items || [];
            if (idx >= posts.length) throw new Error('Post index ' + (idx + 1) + ' not found');
            const pk = posts[idx].pk;

            const csrf = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
            const r3 = await fetch(
                'https://www.instagram.com/api/v1/web/comments/' + pk + '/add/',
                {{
                    method: 'POST',
                    credentials: 'include',
                    headers: {{
                        ...headers,
                        'X-CSRFToken': csrf,
                        'Content-Type': 'application/x-www-form-urlencoded',
                    }},
                    body: 'comment_text=' + encodeURIComponent({text!r}),
                }}
            );
            if (!r3.ok) throw new Error('Comment failed: HTTP ' + r3.status);
            return 'OK';
        }}
        """)

        return f"Commented on @{username}'s post #{post_index}: {text}"

    except Exception as e:
        logger.error("Comment failed: %s", e)
        raise SystemExit(f"Comment failed: {e}")
    finally:
        close_browser(pw, browser)
