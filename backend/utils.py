from __future__ import annotations

import hashlib
import json
import os
import random
import re
import string
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar
from urllib.parse import urlparse

import requests
from dateutil import tz


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

T = TypeVar("T")


def now_local_str() -> str:
    return datetime.now(tz=tz.tzlocal()).strftime("%Y-%m-%d %H:%M:%S")


def dt_local_str_from_ts(ts: int) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(tz.tzlocal())
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def safe_slug(text: str, max_len: int = 64) -> str:
    text = text.strip()
    if not text:
        return "item"
    # Avoid using URL directly as filename; hash + short host.
    host = ""
    try:
        host = (urlparse(text).netloc or "").split(":")[0].lower()
    except Exception:
        host = ""
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    base = re.sub(r"[^a-zA-Z0-9]+", "-", host) if host else "link"
    base = base.strip("-")[:20] or "link"
    return f"{base}-{h}"[:max_len]


def resolve_url(url: str, timeout: int = 15) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout, allow_redirects=True)
        return r.url
    except requests.RequestException:
        return url


def request_with_retry(
    method: str,
    url: str,
    *,
    session: Optional[requests.Session] = None,
    retries: int = 2,
    timeout: int = 20,
    backoff: float = 0.8,
    jitter: float = 0.3,
    **kwargs: Any,
) -> requests.Response:
    last_err: Optional[BaseException] = None
    s = session or requests.Session()
    for attempt in range(retries + 1):
        try:
            resp = s.request(method, url, timeout=timeout, **kwargs)
            return resp
        except (requests.Timeout, requests.ConnectionError) as e:
            last_err = e
            if attempt >= retries:
                break
            sleep_s = backoff * (2**attempt) + random.random() * jitter
            time.sleep(sleep_s)
    raise RuntimeError(f"网络请求失败（已重试{retries}次）: {url}") from last_err


def dump_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def dump_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def sleep_polite(min_s: float = 0.35, max_s: float = 0.9) -> None:
    time.sleep(min_s + random.random() * (max_s - min_s))


def random_id(n: int = 12) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))

