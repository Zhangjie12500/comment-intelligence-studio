from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from dateutil import tz

from ..analyzer import translate_to_zh
from ..utils import UA, resolve_url, request_with_retry, sleep_polite


class YouTubeError(RuntimeError):
    pass


def extract_video_id(url: str) -> str:
    # ── Strategy 1: regex directly on raw URL (no network needed) ──
    # Pattern A: youtu.be/VIDEO_ID[?...]
    m = re.search(r"youtu\.be/([0-9A-Za-z_-]{6,})", url)
    if m:
        return m.group(1)

    # Pattern B: youtube.com/(watch|shorts|embed|v)/VIDEO_ID
    m = re.search(r"youtube\.com/(?:watch|shorts|embed|v)/(?:[^/?&]+/)*([0-9A-Za-z_-]{6,})", url)
    if m:
        return m.group(1)

    # Pattern C: youtube.com/watch?v=VIDEO_ID[&...]
    # Extract video ID from query string via regex on raw URL (avoids network request)
    m = re.search(r"youtube\.com/(?:watch)?\?[^#]*[?&]v=([0-9A-Za-z_-]{6,})", url)
    if m:
        return m.group(1)

    # ── Strategy 2: follow redirects and parse query string ──
    # Only used when URL is a redirect target (e.g. youtu.be short link resolved)
    try:
        u = resolve_url(url)
        p = urlparse(u)
        host = (p.netloc or "").lower().split(":")[0]
        if host.endswith("youtu.be"):
            vid = p.path.strip("/").split("/")[0]
            if vid:
                return vid
        if host.endswith("youtube.com"):
            q = parse_qs(p.query)
            if "v" in q and q["v"]:
                return q["v"][0]
            m = re.search(r"/shorts/([0-9A-Za-z_-]{6,})", p.path)
            if m:
                return m.group(1)
    except Exception:
        pass

    raise YouTubeError("无法从 YouTube 链接解析 videoId，请检查链接格式是否正确")


# ── Standalone unit tests ──────────────────────────────────────────
if __name__ == "__main__":
    cases = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=xxx&index=5", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=QVSoNEqdXvU", "QVSoNEqdXvU"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?t=123", "dQw4w9WgXcQ"),
        ("https://youtu.be/abc123XYZ-?t=456", "abc123XYZ"),
        ("https://www.youtube.com/shorts/abc123XYZ", "abc123XYZ"),
        ("https://www.youtube.com/embed/abc123XYZ", "abc123XYZ"),
        ("https://www.youtube.com/v/abc123XYZ", "abc123XYZ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=123#comment", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/xyz789?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]
    all_pass = True
    for raw_url, expected in cases:
        try:
            result = extract_video_id(raw_url)
            ok = result == expected
        except Exception as e:
            ok = False
            result = str(e)
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"[{status}] {raw_url}")
        if not ok:
            print(f"       expected={expected}  got={result}")
    print()
    print("All tests passed!" if all_pass else "SOME TESTS FAILED!")



def is_english(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    ascii_letters = sum(1 for ch in t if ("a" <= ch.lower() <= "z"))
    cjk = sum(1 for ch in t if "\u4e00" <= ch <= "\u9fff")
    return ascii_letters > max(10, 2 * cjk)


def api_get(session: requests.Session, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    base = "https://www.googleapis.com/youtube/v3/"
    r = request_with_retry("GET", base + path, session=session, params=params, headers={"User-Agent": UA})
    if r.status_code != 200:
        raise YouTubeError(f"YouTube API 请求失败（HTTP {r.status_code}）")
    return r.json()


def _map_api_error(j: Dict[str, Any]) -> Optional[str]:
    err = j.get("error") or {}
    if not isinstance(err, dict):
        return None
    errors = err.get("errors") or []
    reason = ""
    if errors and isinstance(errors, list) and isinstance(errors[0], dict):
        reason = errors[0].get("reason") or ""
    message = err.get("message") or ""
    reason = reason or ""
    if reason == "commentsDisabled":
        return "评论区关闭"
    if reason == "quotaExceeded":
        return "API 配额耗尽"
    if reason in ("videoNotFound", "notFound"):
        return "视频不可用/已删除"
    if reason in ("private", "forbidden"):
        return "视频为私密/无权限访问"
    if message:
        return message
    return None


def fetch_comments(url: str, limit: int) -> List[Dict[str, Any]]:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise YouTubeError("缺少环境变量 YOUTUBE_API_KEY（YouTube Data API v3）")

    video_id = extract_video_id(url)
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    comments: List[Dict[str, Any]] = []
    page_token: Optional[str] = None

    while len(comments) < limit:
        sleep_polite()
        params = {
            "key": api_key,
            "part": "snippet",
            "videoId": video_id,
            "maxResults": 100,
            "order": "time",
            "textFormat": "plainText",
        }
        if page_token:
            params["pageToken"] = page_token
        j = api_get(session, "commentThreads", params)
        mapped = _map_api_error(j)
        if mapped:
            raise YouTubeError(mapped)

        items = j.get("items") or []
        if not items:
            break

        for it in items:
            if len(comments) >= limit:
                break
            sn = ((it.get("snippet") or {}).get("topLevelComment") or {}).get("snippet") or {}
            user = sn.get("authorDisplayName") or ""
            text = sn.get("textDisplay") or ""
            like = int(sn.get("likeCount") or 0)
            published = sn.get("publishedAt") or ""
            t_local = published
            try:
                dt = datetime.fromisoformat(published.replace("Z", "+00:00")).astimezone(tz.tzlocal())
                t_local = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

            rec: Dict[str, Any] = {
                "platform": "youtube",
                "user": user,
                "text": text,
                "like": like,
                "time": t_local,
                "type": "main",
                "parent": "",
                "translation_zh": "",
            }
            if is_english(text):
                rec["translation_zh"] = translate_to_zh(text) or ""
            comments.append(rec)

            total_replies = int(((it.get("snippet") or {}).get("totalReplyCount")) or 0)
            if total_replies > 0 and len(comments) < limit:
                thread_id = it.get("id")
                if thread_id:
                    r_page: Optional[str] = None
                    while len(comments) < limit:
                        sleep_polite()
                        r_params = {
                            "key": api_key,
                            "part": "snippet",
                            "parentId": thread_id,
                            "maxResults": 100,
                            "textFormat": "plainText",
                        }
                        if r_page:
                            r_params["pageToken"] = r_page
                        rj = api_get(session, "comments", r_params)
                        mapped2 = _map_api_error(rj)
                        if mapped2:
                            # replies 部分失败不应影响主流程
                            break
                        r_items = rj.get("items") or []
                        if not r_items:
                            break
                        for ri in r_items:
                            if len(comments) >= limit:
                                break
                            rsn = (ri.get("snippet") or {})
                            r_user = rsn.get("authorDisplayName") or ""
                            r_text = rsn.get("textDisplay") or ""
                            r_like = int(rsn.get("likeCount") or 0)
                            r_pub = rsn.get("publishedAt") or ""
                            r_local = r_pub
                            try:
                                dt = datetime.fromisoformat(r_pub.replace("Z", "+00:00")).astimezone(tz.tzlocal())
                                r_local = dt.strftime("%Y-%m-%d %H:%M:%S")
                            except Exception:
                                pass
                            rrec: Dict[str, Any] = {
                                "platform": "youtube",
                                "user": r_user,
                                "text": r_text,
                                "like": r_like,
                                "time": r_local,
                                "type": "reply",
                                "parent": text,
                                "translation_zh": "",
                            }
                            if is_english(r_text):
                                rrec["translation_zh"] = translate_to_zh(r_text) or ""
                            comments.append(rrec)
                        r_page = rj.get("nextPageToken")
                        if not r_page:
                            break

        page_token = j.get("nextPageToken")
        if not page_token:
            break

    return comments[:limit]


def parse_video_id(url: str) -> str:
    return extract_video_id(url)

