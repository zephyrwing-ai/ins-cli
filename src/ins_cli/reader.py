"""HTTP-based read operations — fast, no browser needed."""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from .auth import get_auth_headers, load_cookies

logger = logging.getLogger(__name__)

API_BASE = "https://www.instagram.com/api/v1"


def _get_session() -> tuple[requests.Session, dict[str, str]]:
    cookies = load_cookies()
    if not cookies:
        raise SystemExit("Not logged in. Run: ins login")
    session = requests.Session()
    headers = get_auth_headers(cookies)
    session.headers.update(headers)
    for k, v in cookies.items():
        session.cookies.set(k, v, domain=".instagram.com")
    return session, headers


def get_profile(username: str) -> dict[str, Any]:
    """Get a user's profile info via the web_profile_info API."""
    session, headers = _get_session()
    resp = session.get(
        f"{API_BASE}/users/web_profile_info/",
        params={"username": username},
    )
    resp.raise_for_status()
    user = resp.json().get("data", {}).get("user", {})
    return {
        "username": user.get("username", ""),
        "name": user.get("full_name", ""),
        "bio": user.get("biography", ""),
        "followers": user.get("edge_followed_by", {}).get("count", 0),
        "following": user.get("edge_follow", {}).get("count", 0),
        "posts": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
        "verified": user.get("is_verified", False),
        "private": user.get("is_private", False),
    }


def search_users(query: str, count: int = 10) -> list[dict[str, str]]:
    """Search for Instagram users."""
    session, headers = _get_session()
    resp = session.get(
        f"{API_BASE}/users/search/",
        params={"query": query, "count": count},
    )
    resp.raise_for_status()
    users = resp.json().get("users", [])
    return [
        {
            "username": u.get("username", ""),
            "name": u.get("full_name", ""),
            "verified": u.get("is_verified", False),
            "private": u.get("is_private", False),
        }
        for u in users
    ]


def get_user_posts(username: str, count: int = 12) -> list[dict[str, Any]]:
    """Get recent posts from a user."""
    session, headers = _get_session()

    # First resolve user ID
    profile = get_profile(username)
    user_id = profile.get("id")
    if not user_id:
        # Try from cookies
        cookies = load_cookies()
        if cookies and cookies.get("ds_user_id") and username == "self":
            user_id = cookies["ds_user_id"]

    if not user_id:
        # Fallback: use web_profile_info to get id
        resp = session.get(
            f"{API_BASE}/users/web_profile_info/",
            params={"username": username},
        )
        data = resp.json().get("data", {}).get("user", {})
        user_id = data.get("id")

    if not user_id:
        return []

    resp = session.get(
        f"{API_BASE}/feed/user/{user_id}/",
        params={"count": count},
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        {
            "caption": (i.get("caption") or {}).get("text", ""),
            "likes": i.get("like_count", 0),
            "comments": i.get("comment_count", 0),
            "media_type": i.get("media_type", 0),
            "taken_at": i.get("taken_at", 0),
            "code": i.get("code", ""),
            "url": f"https://www.instagram.com/p/{i.get('code', '')}/",
        }
        for i in items
    ]


def get_comments(media_id: str, count: int = 20) -> list[dict[str, str]]:
    """Get comments on a post."""
    session, headers = _get_session()
    resp = session.get(
        f"{API_BASE}/media/{media_id}/comments/",
        params={"count": count},
    )
    resp.raise_for_status()
    comments = resp.json().get("comments", [])
    return [
        {
            "username": c.get("user", {}).get("username", ""),
            "text": c.get("text", ""),
            "likes": c.get("comment_like_count", 0),
        }
        for c in comments
    ]
