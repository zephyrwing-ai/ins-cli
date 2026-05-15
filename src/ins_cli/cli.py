"""ins-cli: Instagram CLI — read via HTTP API, write via browser automation."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__


def _fmt_output(data, fmt: str = "table") -> str:
    if fmt == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)
    if fmt == "plain":
        if isinstance(data, list):
            return "\n".join(str(item) for item in data)
        return str(data)
    # table
    if isinstance(data, list) and data:
        headers = list(data[0].keys())
        lines = [" | ".join(headers)]
        lines.append("-" * len(lines[0]))
        for row in data:
            lines.append(" | ".join(str(row.get(h, "")) for h in headers))
        return "\n".join(lines)
    return json.dumps(data, indent=2, ensure_ascii=False)


def cmd_login(args) -> None:
    """Login by extracting cookies from browser or manual input."""
    from .auth import clear_cookies, extract_browser_cookies, save_cookies

    if args.manual:
        print("Paste your Instagram cookies as JSON (e.g. {\"sessionid\": \"...\", ...}):")
        try:
            raw = input("> ")
            cookies = json.loads(raw)
            save_cookies(cookies)
            print("Cookies saved.")
        except (json.JSONDecodeError, EOFError):
            print("Invalid JSON.")
            sys.exit(1)
        return

    # Try browser extraction
    cookies = extract_browser_cookies()
    if cookies:
        save_cookies(cookies)
        print("Logged in via browser cookies.")
        return

    print("Could not extract cookies from browser.")
    print("Try: ins login --manual")


def cmd_logout(args) -> None:
    from .auth import clear_cookies
    clear_cookies()
    print("Logged out (cookies cleared).")


def cmd_profile(args) -> None:
    from .reader import get_profile
    data = get_profile(args.username)
    print(_fmt_output(data, args.format))


def cmd_search(args) -> None:
    from .reader import search_users
    data = search_users(args.query, count=args.count)
    print(_fmt_output(data, args.format))


def cmd_posts(args) -> None:
    from .reader import get_user_posts
    data = get_user_posts(args.username, count=args.count)
    print(_fmt_output(data, args.format))


def cmd_comments(args) -> None:
    from .reader import get_comments
    data = get_comments(args.media_id, count=args.count)
    print(_fmt_output(data, args.format))


def cmd_post(args) -> None:
    from .writer import post_image
    result = post_image(args.media, caption=args.caption or "")
    print(result)


def cmd_story(args) -> None:
    from .writer import post_story
    result = post_story(args.media)
    print(result)


def cmd_comment(args) -> None:
    from .writer import comment_on_post
    result = comment_on_post(args.username, args.text, post_index=args.index)
    print(result)


def _add_format_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-f", "--format",
        choices=["table", "json", "plain"],
        default=argparse.SUPPRESS,
        help="Output format",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ins",
        description="Instagram CLI — read via HTTP API, write via browser automation",
    )
    parser.add_argument("--version", action="version", version=f"ins {__version__}")
    parser.add_argument(
        "-f", "--format",
        choices=["table", "json", "plain"],
        default="table",
        help="Output format",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # --- Auth ---
    p_login = sub.add_parser("login", help="Login via browser cookies or manual input")
    p_login.add_argument("--manual", action="store_true", help="Input cookies manually")
    p_login.set_defaults(func=cmd_login)

    p_logout = sub.add_parser("logout", help="Clear saved cookies")
    p_logout.set_defaults(func=cmd_logout)

    # --- Read ---
    p_profile = sub.add_parser("profile", help="Get user profile")
    p_profile.add_argument("username", help="Instagram username")
    _add_format_option(p_profile)
    p_profile.set_defaults(func=cmd_profile)

    p_search = sub.add_parser("search", help="Search users")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--count", type=int, default=10, help="Number of results")
    _add_format_option(p_search)
    p_search.set_defaults(func=cmd_search)

    p_posts = sub.add_parser("posts", help="Get user's recent posts")
    p_posts.add_argument("username", help="Instagram username")
    p_posts.add_argument("--count", type=int, default=12, help="Number of posts")
    _add_format_option(p_posts)
    p_posts.set_defaults(func=cmd_posts)

    p_comments = sub.add_parser("comments", help="Get comments on a post")
    p_comments.add_argument("media_id", help="Media ID of the post")
    p_comments.add_argument("--count", type=int, default=20, help="Number of comments")
    _add_format_option(p_comments)
    p_comments.set_defaults(func=cmd_comments)

    # --- Write ---
    p_post = sub.add_parser("post", help="Post an image to feed")
    p_post.add_argument("media", help="Path to image/video file")
    p_post.add_argument("--caption", "-c", help="Caption text")
    p_post.set_defaults(func=cmd_post)

    p_story = sub.add_parser("story", help="Post a story")
    p_story.add_argument("media", help="Path to image/video file")
    p_story.set_defaults(func=cmd_story)

    p_comment = sub.add_parser("comment", help="Comment on a user's post")
    p_comment.add_argument("username", help="Post author's username")
    p_comment.add_argument("text", help="Comment text")
    p_comment.add_argument("--index", type=int, default=1, help="Post index (1=most recent)")
    p_comment.set_defaults(func=cmd_comment)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
