"""HTTP-based read operations — fast, no browser needed."""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from .auth import get_auth_headers, load_cookies
from .browser import close_browser, launch_browser

logger = logging.getLogger(__name__)

API_BASE = "https://www.instagram.com/api/v1"
WEB_BASE = "https://www.instagram.com"


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


def _get_user(session: requests.Session, username: str) -> dict[str, Any]:
    resp = session.get(
        f"{API_BASE}/users/web_profile_info/",
        params={"username": username},
    )
    _raise_for_status(resp, f"get profile @{username}")
    user = resp.json().get("data", {}).get("user")
    if not user:
        raise SystemExit(f"User not found: {username}")
    return user


def _raise_for_status(resp: requests.Response, action: str) -> None:
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        detail = ""
        try:
            payload = resp.json()
            detail = payload.get("message") or payload.get("error") or ""
        except (ValueError, AttributeError):
            detail = resp.text[:200]
        msg = f"Instagram API failed to {action}: HTTP {resp.status_code}"
        if detail:
            msg = f"{msg} ({detail})"
        raise SystemExit(msg) from e


def _browser_eval(script: str, arg: dict[str, Any]) -> Any:
    pw, browser, context, page = launch_browser()
    try:
        result = page.evaluate(script, arg)
        if isinstance(result, dict) and not result.get("ok", True):
            raise SystemExit(result.get("error") or "Instagram browser request failed")
        return result
    finally:
        close_browser(pw, browser)


def _browser_get_user(username: str) -> dict[str, Any]:
    result = _browser_eval(
        """
        async ({ username }) => {
          const res = await fetch(
            'https://www.instagram.com/api/v1/users/web_profile_info/?username='
              + encodeURIComponent(username),
            {
              credentials: 'include',
              headers: { 'X-IG-App-ID': '936619743392459' },
              signal: AbortSignal.timeout(15000),
            }
          );
          if (!res.ok) return { ok: false, error: 'Instagram API failed to get profile @' + username + ': HTTP ' + res.status };
          const data = await res.json();
          const user = data?.data?.user;
          if (!user) return { ok: false, error: 'User not found: ' + username };
          return { ok: true, user };
        }
        """,
        {"username": username},
    )
    return result["user"]


def _browser_search_users(query: str, count: int) -> list[dict[str, Any]]:
    result = _browser_eval(
        """
        async ({ query, count }) => {
          const res = await fetch(
            'https://www.instagram.com/web/search/topsearch/?query='
              + encodeURIComponent(query)
              + '&context=user',
            {
              credentials: 'include',
              headers: { 'X-IG-App-ID': '936619743392459' },
              signal: AbortSignal.timeout(15000),
            }
          );
          if (!res.ok) return { ok: false, error: 'Instagram API failed to search users: HTTP ' + res.status };
          const data = await res.json();
          return { ok: true, users: (data?.users || []).slice(0, count) };
        }
        """,
        {"query": query, "count": count},
    )
    users = result["users"]
    return [
        {
            "username": u.get("user", {}).get("username", ""),
            "name": u.get("user", {}).get("full_name", ""),
            "verified": u.get("user", {}).get("is_verified", False),
            "private": u.get("user", {}).get("is_private", False),
        }
        for u in users
    ]


def _browser_get_user_posts(username: str, count: int) -> list[dict[str, Any]]:
    result = _browser_eval(
        """
        async ({ username, count }) => {
          const headers = { 'X-IG-App-ID': '936619743392459' };
          const opts = { credentials: 'include', headers, signal: AbortSignal.timeout(15000) };

          const r1 = await fetch(
            'https://www.instagram.com/api/v1/users/web_profile_info/?username='
              + encodeURIComponent(username),
            opts
          );
          if (!r1.ok) return { ok: false, error: 'Instagram API failed to get profile @' + username + ': HTTP ' + r1.status };
          const user = (await r1.json())?.data?.user;
          const userId = user?.id;
          if (!userId) return { ok: false, error: 'User not found: ' + username };

          const r2 = await fetch(
            'https://www.instagram.com/api/v1/feed/user/' + userId + '/?count=' + count,
            opts
          );
          if (!r2.ok) return { ok: false, error: 'Instagram API failed to get posts for @' + username + ': HTTP ' + r2.status };
          const data = await r2.json();
          return { ok: true, items: (data?.items || []).slice(0, count) };
        }
        """,
        {"username": username, "count": count},
    )
    return [_post_row(i) for i in result["items"]]


def _browser_get_comments(media_id: str, count: int) -> list[dict[str, str]]:
    result = _browser_eval(
        """
        async ({ mediaId, count }) => {
          const res = await fetch(
            'https://www.instagram.com/api/v1/media/' + encodeURIComponent(mediaId) + '/comments/?count=' + count,
            {
              credentials: 'include',
              headers: { 'X-IG-App-ID': '936619743392459' },
              signal: AbortSignal.timeout(15000),
            }
          );
          if (!res.ok) return { ok: false, error: 'Instagram API failed to get comments for media ' + mediaId + ': HTTP ' + res.status };
          const data = await res.json();
          return { ok: true, comments: data?.comments || [] };
        }
        """,
        {"mediaId": media_id, "count": count},
    )
    return [_comment_row(c) for c in result["comments"][:count]]


def _profile_row(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user.get("id", ""),
        "username": user.get("username", ""),
        "name": user.get("full_name", ""),
        "bio": user.get("biography", ""),
        "followers": user.get("edge_followed_by", {}).get("count", 0),
        "following": user.get("edge_follow", {}).get("count", 0),
        "posts": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
        "verified": user.get("is_verified", False),
        "private": user.get("is_private", False),
    }


def _post_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id", ""),
        "pk": item.get("pk", ""),
        "caption": (item.get("caption") or {}).get("text", ""),
        "likes": item.get("like_count", 0),
        "comments": item.get("comment_count", 0),
        "media_type": item.get("media_type", 0),
        "taken_at": item.get("taken_at", 0),
        "code": item.get("code", ""),
        "url": f"https://www.instagram.com/p/{item.get('code', '')}/",
    }


def _comment_row(comment: dict[str, Any]) -> dict[str, str]:
    return {
        "username": comment.get("user", {}).get("username", ""),
        "text": comment.get("text", ""),
        "likes": comment.get("comment_like_count", 0),
    }


def get_profile(username: str) -> dict[str, Any]:
    """Get a user's profile info via the web_profile_info API."""
    try:
        session, _headers = _get_session()
        user = _get_user(session, username)
    except (SystemExit, requests.RequestException):
        user = _browser_get_user(username)
    return _profile_row(user)


def search_users(query: str, count: int = 10) -> list[dict[str, str]]:
    """Search for Instagram users."""
    try:
        session, _headers = _get_session()
        resp = session.get(
            f"{WEB_BASE}/web/search/topsearch/",
            params={"context": "user", "query": query},
        )
        _raise_for_status(resp, f"search users for {query!r}")
        users = resp.json().get("users", [])[:count]
        return [
            {
                "username": u.get("user", {}).get("username", ""),
                "name": u.get("user", {}).get("full_name", ""),
                "verified": u.get("user", {}).get("is_verified", False),
                "private": u.get("user", {}).get("is_private", False),
            }
            for u in users
        ]
    except (SystemExit, requests.RequestException):
        return _browser_search_users(query, count)


def get_user_posts(username: str, count: int = 12) -> list[dict[str, Any]]:
    """Get recent posts from a user."""
    try:
        session, _headers = _get_session()
        user = _get_user(session, username)
        user_id = user.get("id")
        if not user_id:
            cookies = load_cookies()
            if cookies and cookies.get("ds_user_id") and username == "self":
                user_id = cookies["ds_user_id"]
        if not user_id:
            return []
        resp = session.get(
            f"{API_BASE}/feed/user/{user_id}/",
            params={"count": count},
        )
        _raise_for_status(resp, f"get posts for @{username}")
        return [_post_row(i) for i in resp.json().get("items", [])]
    except (SystemExit, requests.RequestException):
        return _browser_get_user_posts(username, count)


def get_comments(media_id: str, count: int = 20) -> list[dict[str, str]]:
    """Get comments on a post."""
    try:
        session, _headers = _get_session()
        resp = session.get(
            f"{API_BASE}/media/{media_id}/comments/",
            params={"count": count},
        )
        _raise_for_status(resp, f"get comments for media {media_id}")
        return [_comment_row(c) for c in resp.json().get("comments", [])[:count]]
    except (SystemExit, requests.RequestException):
        return _browser_get_comments(media_id, count)
