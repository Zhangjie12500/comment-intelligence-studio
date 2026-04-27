from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
DEFAULT_TTL_HOURS = 24


def _sanitize_token(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", s.strip())
    return s[:80] or "x"


def cache_filename(platform: str, video_id: str, limit: int, include_replies: bool) -> str:
    return f"{_sanitize_token(platform)}_{_sanitize_token(video_id)}_{int(limit)}_{str(bool(include_replies)).lower()}.json"


def cache_path(platform: str, video_id: str, limit: int, include_replies: bool) -> str:
    return os.path.join(CACHE_DIR, cache_filename(platform, video_id, limit, include_replies))


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        # Accept both Z and offset formats
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def is_cache_valid(fetched_at_iso: str, ttl_hours: int = DEFAULT_TTL_HOURS) -> bool:
    dt = _parse_iso(fetched_at_iso)
    if not dt:
        return False
    return datetime.now(timezone.utc) - dt <= timedelta(hours=ttl_hours)


def read_cache(platform: str, video_id: str, limit: int, include_replies: bool) -> Optional[Dict[str, Any]]:
    p = cache_path(platform, video_id, limit, include_replies)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f)
        if not isinstance(j, dict):
            return None
        fetched_at = str(j.get("fetched_at") or "")
        if not fetched_at or not is_cache_valid(fetched_at):
            return None
        if not isinstance(j.get("comments"), list):
            return None
        return j
    except Exception:
        # cache damaged -> ignore
        return None


def write_cache(
    *,
    url: str,
    platform: str,
    video_id: str,
    limit: int,
    include_replies: bool,
    comments: Any,
) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    payload = {
        "url": url,
        "platform": platform,
        "video_id": video_id,
        "limit": int(limit),
        "include_replies": bool(include_replies),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "comments": comments if isinstance(comments, list) else [],
    }
    p = cache_path(platform, video_id, limit, include_replies)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    return p

