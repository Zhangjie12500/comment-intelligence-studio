from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from ..utils import UA, dt_local_str_from_ts, resolve_url, request_with_retry, sleep_polite


MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39,
    12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63,
    57, 62, 11, 36, 20, 34, 44, 52,
]


class BiliError(RuntimeError):
    pass


def extract_bvid(url: str) -> str:
    u = resolve_url(url)
    m = re.search(r"/video/(BV[0-9A-Za-z]{10,})", u)
    if m:
        return m.group(1)
    q = parse_qs(urlparse(u).query)
    for k in ("bvid", "bv"):
        if k in q and q[k]:
            return q[k][0]
    raise BiliError("BV 号提取失败：请确认链接包含 /video/BVxxxx 或携带 bvid 参数")


def get_aid(session: requests.Session, bvid: str) -> int:
    r = request_with_retry(
        "GET",
        "https://api.bilibili.com/x/web-interface/view",
        session=session,
        params={"bvid": bvid},
        headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"},
    )
    if r.status_code != 200:
        raise BiliError(f"获取视频信息失败（HTTP {r.status_code}）")
    j = r.json()
    if j.get("code") != 0:
        raise BiliError(f"获取视频信息失败：{j.get('message') or j}")
    data = j.get("data") or {}
    aid = data.get("aid")
    if not aid:
        raise BiliError("获取 aid 失败：接口返回缺少 aid")
    return int(aid)


def get_wbi_keys(session: requests.Session) -> Tuple[str, str]:
    r = request_with_retry(
        "GET",
        "https://api.bilibili.com/x/web-interface/nav",
        session=session,
        headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"},
    )
    j = r.json()
    if j.get("code") != 0:
        raise BiliError(f"获取 WBI keys 失败：{j.get('message') or j}")
    data = j.get("data") or {}
    wbi_img = data.get("wbi_img") or {}
    img_url = wbi_img.get("img_url") or ""
    sub_url = wbi_img.get("sub_url") or ""
    img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
    sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
    if not img_key or not sub_key:
        raise BiliError("WBI 签名失效：获取 img_key/sub_key 为空（B站接口可能更新）")
    return img_key, sub_key


def mixin_key(img_key: str, sub_key: str) -> str:
    raw = img_key + sub_key
    mixed = "".join(raw[i] for i in MIXIN_KEY_ENC_TAB if i < len(raw))
    return mixed[:32]


def wbi_sign(params: Dict[str, Any], mixin: str) -> Dict[str, Any]:
    import time

    p = dict(params)
    p["wts"] = int(time.time())
    filtered = {}
    for k, v in p.items():
        s = str(v)
        s = re.sub(r"[!'()*]", "", s)
        filtered[k] = s
    qs = urlencode(sorted(filtered.items()))
    w_rid = hashlib.md5((qs + mixin).encode("utf-8")).hexdigest()
    filtered["w_rid"] = w_rid
    return filtered


def fetch_replies_for_rpid(session: requests.Session, oid: int, rpid: int, limit: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    pn = 1
    while len(out) < limit:
        sleep_polite()
        r = request_with_retry(
            "GET",
            "https://api.bilibili.com/x/v2/reply/reply",
            session=session,
            params={"type": 1, "oid": oid, "root": rpid, "pn": pn, "ps": 20},
            headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"},
        )
        j = r.json()
        if j.get("code") != 0:
            # Some videos have comments disabled or limited
            msg = j.get("message") or ""
            if "关闭" in msg or "不可见" in msg:
                return out
            return out
        data = j.get("data") or {}
        replies = data.get("replies") or []
        if not replies:
            break
        out.extend(replies)
        pn += 1
    return out[:limit]


def fetch_comments(url: str, limit: int, include_replies: bool = True) -> List[Dict[str, Any]]:
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    bvid = extract_bvid(url)
    oid = get_aid(session, bvid)

    # WBI path (preferred). If WBI keys unavailable (login/region), fallback to legacy endpoint.
    mixin: Optional[str] = None
    try:
        img_key, sub_key = get_wbi_keys(session)
        mixin = mixin_key(img_key, sub_key)
    except BiliError:
        mixin = None

    comments: List[Dict[str, Any]] = []

    def ingest_reply_item(item: Dict[str, Any]) -> None:
        nonlocal comments
        if len(comments) >= limit:
            return
        user = ((item.get("member") or {}).get("uname")) or ""
        text = ((item.get("content") or {}).get("message")) or ""
        like = int(item.get("like") or 0)
        ctime = int(item.get("ctime") or 0)
        comments.append(
            {
                "platform": "bilibili",
                "user": user,
                "text": text,
                "like": like,
                "reply_count": int(item.get("rcount") or 0),
                "time": dt_local_str_from_ts(ctime),
                "type": "main",
                "parent": "",
                "translation_zh": "",
            }
        )

        rpid = int(item.get("rpid") or 0)
        rcount = int(item.get("rcount") or 0)
        if include_replies and rpid and rcount > 0 and len(comments) < limit:
            nested_raw = fetch_replies_for_rpid(session, oid=oid, rpid=rpid, limit=max(0, limit - len(comments)))
            parent_text = text
            for rr in (nested_raw or []):
                if len(comments) >= limit:
                    break
                n_user = ((rr.get("member") or {}).get("uname")) or ""
                n_text = ((rr.get("content") or {}).get("message")) or ""
                n_like = int(rr.get("like") or 0)
                n_ctime = int(rr.get("ctime") or 0)
                comments.append(
                    {
                        "platform": "bilibili",
                        "user": n_user,
                        "text": n_text,
                        "like": n_like,
                        "reply_count": int(rr.get("rcount") or 0),
                        "time": dt_local_str_from_ts(n_ctime),
                        "type": "reply",
                        "parent": parent_text,
                        "translation_zh": "",
                    }
                )

    if mixin:
        pagination_str = json.dumps({"offset": ""}, ensure_ascii=False)
        while len(comments) < limit:
            sleep_polite()
            params = {"type": 1, "oid": oid, "mode": 2, "pagination_str": pagination_str, "plat": 1}
            signed = wbi_sign(params, mixin)
            r = request_with_retry(
                "GET",
                "https://api.bilibili.com/x/v2/reply/wbi/main",
                session=session,
                params=signed,
                headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"},
            )
            j = r.json()
            code = j.get("code")
            if code != 0:
                msg = j.get("message") or ""
                if "关闭" in msg or "不可见" in msg:
                    raise BiliError("评论区不可用/已关闭")
                if "w_rid" in msg or "sign" in msg or "校验" in msg:
                    raise BiliError("B站 WBI 签名可能已变更，请检查 wbi 实现或稍后重试。")
                # fallback to legacy if WBI blocked
                mixin = None
                break

            data = j.get("data") or {}
            replies = data.get("replies") or []
            if not replies:
                break

            for item in replies:
                ingest_reply_item(item)
                if len(comments) >= limit:
                    break

            cursor = data.get("cursor") or {}
            pr = cursor.get("pagination_reply") or {}
            next_offset = ""
            if isinstance(pr, dict):
                next_offset = pr.get("next_offset") or ""
            if not next_offset:
                next_offset = cursor.get("next_offset") or ""
            if not next_offset:
                break
            pagination_str = json.dumps({"offset": next_offset}, ensure_ascii=False)

    # Legacy fallback: x/v2/reply/main (pn/ps)
    if not mixin and len(comments) < limit:
        pn = 1
        ps = 20
        while len(comments) < limit:
            sleep_polite()
            r = request_with_retry(
                "GET",
                "https://api.bilibili.com/x/v2/reply/main",
                session=session,
                params={"type": 1, "oid": oid, "pn": pn, "ps": ps, "sort": 2},
                headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"},
            )
            j = r.json()
            if j.get("code") != 0:
                msg = j.get("message") or ""
                if "关闭" in msg or "不可见" in msg:
                    raise BiliError("评论区不可用/已关闭")
                raise BiliError(f"B站评论接口失败：{msg or j}")
            data = j.get("data") or {}
            replies = data.get("replies") or []
            if not replies:
                break
            for item in replies:
                ingest_reply_item(item)
                if len(comments) >= limit:
                    break
            page = data.get("page") or {}
            count = int(page.get("count") or 0)
            if count and pn * ps >= count:
                break
            pn += 1

    return comments[:limit]


def parse_video_id(url: str) -> str:
    # Always return bvid as video_id
    return extract_bvid(url)

