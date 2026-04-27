from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

import requests


def is_probably_emoji_only(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    t2 = re.sub(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF]+", "", t)
    t2 = re.sub(r"[\s\W_]+", "", t2, flags=re.UNICODE)
    return len(t2) == 0


MEANINGLESS_PATTERNS = [
    r"^(哈)+$",
    r"^(哈哈)+$",
    r"^(6)+$",
    r"^(666)+$",
    r"^(牛)+$",
    r"^\.{1,3}$",
    r"^。+$",
    r"^!+$",
    r"^\?+$",
]


def is_meaningless_short(text: str) -> bool:
    t = re.sub(r"\s+", "", text.strip())
    if not t:
        return True
    if len(t) <= 2:
        return True
    for p in MEANINGLESS_PATTERNS:
        if re.match(p, t):
            return True
    return False


def normalize_for_dedup(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[“”\"'’]", "", t)
    t = re.sub(r"[，,。.!！?？:：;；]+", "", t)
    return t


def jaccard_similarity(a: str, b: str) -> float:
    sa = set(a)
    sb = set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def clean_and_merge(
    comments: List[Dict[str, Any]],
    similarity_threshold: float = 0.92,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    raw_n = len(comments)
    cleaned: List[Dict[str, Any]] = []
    seen_norm: set[str] = set()
    removed = {"empty": 0, "emoji_only": 0, "meaningless_short": 0, "duplicate": 0, "similar_merged": 0}

    for c in comments:
        text = (c.get("text") or "").strip()
        if not text:
            removed["empty"] += 1
            continue
        if is_probably_emoji_only(text):
            removed["emoji_only"] += 1
            continue
        if is_meaningless_short(text):
            removed["meaningless_short"] += 1
            continue

        norm = normalize_for_dedup(text)
        if not norm:
            removed["empty"] += 1
            continue
        if norm in seen_norm:
            removed["duplicate"] += 1
            continue

        merged = False
        for existing in cleaned:
            en = normalize_for_dedup(existing.get("text") or "")
            if en and jaccard_similarity(norm, en) >= similarity_threshold:
                removed["similar_merged"] += 1
                merged = True
                if int(c.get("like") or 0) > int(existing.get("like") or 0):
                    existing.update(c)
                break
        if merged:
            continue

        seen_norm.add(norm)
        cleaned.append(c)

    stats = {"raw": raw_n, "cleaned": len(cleaned), "removed": removed}
    return cleaned, stats


def top_liked(comments: List[Dict[str, Any]], n: int = 10) -> List[Dict[str, Any]]:
    return sorted(comments, key=lambda x: int(x.get("like") or 0), reverse=True)[:n]


def compute_stance_stats(comments: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count comments per stance category. Every comment gets exactly one primary category."""
    counts: Dict[str, int] = {"support": 0, "oppose": 0, "neutral": 0, "joke": 0, "question": 0}
    for c in comments:
        cat = classify_stance(c.get("text") or "")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def classify_stance(text: str) -> str:
    """Return one of: support, oppose, question, joke, neutral.
    Evaluated in priority order to ensure every comment falls into exactly one bucket."""
    t = text.strip()
    if re.search(r"不对|反对|质疑|假吗|骗|垃圾|离谱|bad|wrong|disagree|lie|假的|造谣|无语", t):
        return "oppose"
    if re.search(r"为什么|怎么|是否|什么|为什么|疑问|请问|[?？]", t):
        return "question"
    if re.search(r"哈哈|笑死|绷|乐|蚌|典|草|整活|lol|lmao|233|666|牛", t):
        return "joke"
    if re.search(r"支持|赞|认同|说得对|同意|good|great|love|based|确实|有道理|顶|厉害|牛批|绝了", t):
        return "support"
    return "neutral"


def compute_top_influence(comments: List[Dict[str, Any]], n: int = 10) -> List[Dict[str, Any]]:
    """Enrich top-n comments with influence_score and stance, sorted descending."""
    enriched = []
    for c in comments:
        like_count = int(c.get("like") or 0)
        reply_count = int(c.get("reply_count") or 0)
        influence_score = like_count * 1.0 + reply_count * 2.0
        enriched.append({
            "user": c.get("user", c.get("username", "")),
            "text": c.get("text", ""),
            "like": like_count,
            "reply_count": reply_count,
            "influence_score": influence_score,
            "stance": classify_stance(c.get("text") or ""),
            "translation_zh": c.get("translation_zh") or "",
        })
    enriched.sort(key=lambda x: x["influence_score"], reverse=True)
    return enriched[:n]


def compute_clusters(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Simple keyword-based clustering. Groups by normalized token overlap."""
    buckets: Dict[str, Dict[str, Any]] = {}
    for c in comments:
        text = c.get("text") or ""
        norm = normalize_for_dedup(text)
        # Extract tokens: 2+ Chinese chars or 3+ ASCII letters
        words = re.findall(r"[a-z]{3,}|[\u4e00-\u9fff]{2,}", norm)
        if not words:
            words = [norm[:10]] if norm else []
        key = "_".join(words[:4])
        if not key:
            continue
        b = buckets.get(key) or {"keywords": [], "examples": [], "like_weight": 0, "count": 0}
        b["keywords"] = list(dict.fromkeys(b["keywords"] + words[:3]))  # deduplicated append
        b["examples"].append(c)
        b["like_weight"] += int(c.get("like") or 0)
        b["count"] += 1
        buckets[key] = b

    result = []
    for key, b in buckets.items():
        examples = sorted(b["examples"], key=lambda x: int(x.get("like") or 0), reverse=True)
        representative = examples[:3]
        result.append({
            "title": key.replace("_", " ")[:40],
            "keywords": b["keywords"][:6],
            "count": b["count"],
            "like_weight": b["like_weight"],
            "representative_comments": [
                {
                    "user": e.get("user", ""),
                    "text": e.get("text", ""),
                    "like": int(e.get("like") or 0),
                }
                for e in representative
            ],
        })

    result.sort(key=lambda x: x["like_weight"], reverse=True)
    return result[:12]


def compute_controversies(
    stance_stats: Dict[str, int],
    top_comments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Generate controversy items based on stance distribution and top comments."""
    controversies = []
    oppose_n = stance_stats.get("oppose", 0)
    question_n = stance_stats.get("question", 0)
    support_n = stance_stats.get("support", 0)
    joke_n = stance_stats.get("joke", 0)
    neutral_n = stance_stats.get("neutral", 0)
    total = support_n + oppose_n + question_n + joke_n + neutral_n

    if oppose_n > 0:
        controversies.append({
            "title": "评论区存在反对或质疑声音",
            "description": f"共有 {oppose_n} 条评论表达质疑或反对观点，占比约 {oppose_n*100//max(total,1)}%。",
            "related_count": oppose_n,
            "sample_comments": [c["text"] for c in top_comments if c.get("stance") == "oppose"][:3],
        })

    if question_n > 0:
        controversies.append({
            "title": "评论区存在较多追问和求证",
            "description": f"共有 {question_n} 条评论提出问题，占比约 {question_n*100//max(total,1)}%。",
            "related_count": question_n,
            "sample_comments": [c["text"] for c in top_comments if c.get("stance") == "question"][:3],
        })

    if support_n > 0 and oppose_n > 0:
        controversies.append({
            "title": "支持与反对观点并存",
            "description": f"支持观点 {support_n} 条，反对观点 {oppose_n} 条，评论区存在明显观点分歧。",
            "related_count": support_n + oppose_n,
            "sample_comments": [
                c["text"] for c in top_comments
                if c.get("stance") in ("support", "oppose")
            ][:4],
        })

    if joke_n > total * 0.3:
        controversies.append({
            "title": "评论区玩梗调侃比例较高",
            "description": f"调侃/玩梗类评论 {joke_n} 条，占比约 {joke_n*100//max(total,1)}%，评论区氛围偏娱乐化。",
            "related_count": joke_n,
            "sample_comments": [c["text"] for c in top_comments if c.get("stance") == "joke"][:3],
        })

    return controversies


def compute_summary(
    stance_stats: Dict[str, int],
    clusters: List[Dict[str, Any]],
    cleaned_count: int,
    raw_count: int,
    platform: str,
) -> str:
    """Generate a Chinese summary paragraph based on analysis results."""
    support_n = stance_stats.get("support", 0)
    oppose_n = stance_stats.get("oppose", 0)
    question_n = stance_stats.get("question", 0)
    joke_n = stance_stats.get("joke", 0)
    neutral_n = stance_stats.get("neutral", 0)
    total = support_n + oppose_n + question_n + joke_n + neutral_n

    # Dominant category
    categories = [("支持/认同", support_n), ("质疑/反对", oppose_n),
                  ("提问/求证", question_n), ("调侃/玩梗", joke_n), ("中立/补充", neutral_n)]
    dominant_label, dominant_n = max(categories, key=lambda x: x[1])
    dominant_pct = dominant_n * 100 // max(total, 1)

    # Top clusters
    top_cluster_names = [c["title"] for c in clusters[:3] if c.get("title")]

    platform_label = "B站（bilibili）" if platform == "bilibili" else "YouTube"
    summary_parts = [
        f"本次分析共抓取 {raw_count} 条评论，清洗后保留 {cleaned_count} 条"
        + f"（移除空内容/表情/重复等 {raw_count - cleaned_count} 条）。",
        f"评论区整体以「{dominant_label}」为主，共 {dominant_n} 条，占比约 {dominant_pct}%。",
    ]

    if oppose_n > 0:
        summary_parts.append(f"存在 {oppose_n} 条质疑或反对声音（占比约 {oppose_n*100//max(total,1)}%），评论区存在一定观点分歧。")
    if question_n > 0:
        summary_parts.append(f"共有 {question_n} 条提问或求证类评论（占比约 {question_n*100//max(total,1)}%），部分用户在寻求更多信息。")
    if top_cluster_names:
        summary_parts.append(f"主要讨论围绕以下主题展开：{'、'.join(top_cluster_names[:3])}。")
    if joke_n > neutral_n * 0.5:
        summary_parts.append("调侃/玩梗类评论较多，评论区氛围偏轻松娱乐。")
    if support_n > oppose_n * 3:
        summary_parts.append("正面情感占绝对主导，观众整体态度积极。")

    summary_parts.append(f"平台：{platform_label}。")
    return " ".join(summary_parts)


def classify_local(text: str) -> str:
    t = text.strip().lower()
    if re.search(r"\bwhy\b|\bhow\b|为什么|怎么|求解释|请问|[?？]", t):
        return "提问 / 求解释"
    if re.search(r"支持|赞|认同|说得对|同意|good|great|love|based|exactly", t):
        return "支持 / 认同"
    if re.search(r"不对|反对|质疑|假吗|骗|垃圾|bad|wrong|disagree|lie", t):
        return "质疑 / 反对"
    if re.search(r"哈哈|lol|lmao|笑死|梗|整活|离谱|666|牛", t):
        return "调侃 / 玩梗"
    return "中立 / 补充"


def cluster_local(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    for c in comments:
        text = c.get("text") or ""
        norm = normalize_for_dedup(text)
        words = re.findall(r"[a-z]{3,}|[\u4e00-\u9fff]{2,}", norm)
        key = " ".join(words[:5]) if words else norm[:20]
        key = key.strip()
        if not key:
            continue
        b = buckets.setdefault(key, {"title": key[:30], "examples": [], "like_weight": 0})
        b["examples"].append(c)
        b["like_weight"] += int(c.get("like") or 0)
    clusters = list(buckets.values())
    clusters.sort(key=lambda x: x["like_weight"], reverse=True)
    return clusters[:12]


def openai_chat(messages: List[Dict[str, str]], model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 OPENAI_API_KEY")
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.2},
        timeout=90,
    )
    r.raise_for_status()
    j = r.json()
    return (((j.get("choices") or [])[0] or {}).get("message") or {}).get("content") or ""


def translate_to_zh(text: str) -> str:
    if not text.strip():
        return ""
    if not os.getenv("OPENAI_API_KEY"):
        return ""
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    prompt = "把下面英文评论翻译成地道流畅的中文，保留语气与梗，不要解释。\n\n英文：" + text + "\n\n中文："
    try:
        return openai_chat([{"role": "user", "content": prompt}], model=model).strip()
    except Exception:
        return ""


def build_report_local(raw_comments: List[Dict[str, Any]], cleaned: List[Dict[str, Any]], clean_stats: Dict[str, Any]) -> str:
    main_n = sum(1 for c in cleaned if c.get("type") == "main")
    reply_n = sum(1 for c in cleaned if c.get("type") == "reply")
    top10 = top_liked(cleaned, 10)

    cat_map: Dict[str, List[Dict[str, Any]]] = {}
    for c in cleaned:
        cat = classify_local(c.get("text") or "")
        cat_map.setdefault(cat, []).append(c)

    out: List[str] = []
    out.append("# 评论区分析报告\n\n")
    out.append("## 1. 数据概况\n")
    out.append(f"- 原始评论数: {len(raw_comments)}\n")
    out.append(f"- 清洗后评论数: {len(cleaned)}\n")
    out.append(f"- 主评论 / 回复数量: {main_n} / {reply_n}\n")
    out.append(f"- 清洗移除明细: {json.dumps(clean_stats.get('removed', {}), ensure_ascii=False)}\n")
    out.append("\n### 点赞最高评论 Top 10\n")
    for i, c in enumerate(top10, 1):
        out.append(f"{i}. ({c.get('like', 0)}赞) {c.get('user','')}: {c.get('text','')}\n")

    out.append("\n## 2. 分类评论\n")
    for cat in ["支持 / 认同", "质疑 / 反对", "中立 / 补充", "调侃 / 玩梗", "提问 / 求解释"]:
        items = cat_map.get(cat, [])
        items.sort(key=lambda x: int(x.get("like") or 0), reverse=True)
        reps = items[:3]
        out.append(f"\n### {cat}\n")
        out.append(f"- 评论数量: {len(items)}\n")
        out.append(f"- 大致情绪: {'偏正向' if cat=='支持 / 认同' else '偏负向' if cat=='质疑 / 反对' else '偏中性/混合'}\n")
        out.append("- 代表评论:\n")
        if reps:
            for c in reps:
                out.append(f"  - ({c.get('like',0)}赞) {c.get('text','')}\n")
        else:
            out.append("  - （无）\n")

    out.append("\n## 3. 观点聚类\n")
    for cat, items in cat_map.items():
        if not items:
            continue
        clusters = cluster_local(items)
        out.append(f"\n### {cat}\n")
        if not clusters:
            out.append("- （无足够数据聚类）\n")
            continue
        for cl in clusters[:5]:
            ex = sorted(cl["examples"], key=lambda x: int(x.get("like") or 0), reverse=True)[:3]
            core = ex[0].get("text", "") if ex else ""
            out.append(f"\n- 观点标题: {cl['title']}\n")
            out.append(f"  - 核心意思: {core}\n")
            out.append("  - 代表性评论:\n")
            for e in ex:
                out.append(f"    - ({e.get('like',0)}赞) {e.get('text','')}\n")
            out.append(f"  - 点赞权重/影响力: {cl['like_weight']}\n")

    out.append("\n## 4. 总结\n")
    dominant_cat = max(cat_map.items(), key=lambda kv: len(kv[1]))[0] if cat_map else "中立 / 补充"
    out.append(f"- 评论区主流共识: 主要集中在「{dominant_cat}」类观点。\n")
    out.append("- 最大争议点: （本地规则版本无法可靠抽取争议主轴，建议配置 OPENAI_API_KEY 获取高质量总结）\n")
    out.append("- 用户最关注的问题: 提问类评论与高赞评论中出现频率最高的主题。\n")
    out.append("- 情绪整体倾向: 以分类占比与高赞评论为准（本地规则为粗略估计）。\n")
    return "".join(out)


def build_report_openai(raw_comments: List[Dict[str, Any]], cleaned: List[Dict[str, Any]], clean_stats: Dict[str, Any]) -> str:
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    payload = {
        "stats": {
            "raw": len(raw_comments),
            "cleaned": len(cleaned),
            "removed": clean_stats.get("removed", {}),
            "main": sum(1 for c in cleaned if c.get("type") == "main"),
            "reply": sum(1 for c in cleaned if c.get("type") == "reply"),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "top20": top_liked(cleaned, 20),
        "sample_comments": cleaned[:220],
    }
    sys_msg = "你是中文互联网评论区分析专家。请严格按用户指定的 report.md 结构输出，并尽量引用原文支撑结论。"
    user_msg = (
        "基于下面 JSON 数据生成报告，必须包含：\n"
        "# 评论区分析报告\n"
        "## 1. 数据概况（含 Top10）\n"
        "## 2. 分类评论（五类：支持/质疑/中立/调侃/提问；每类给数量、情绪、代表评论）\n"
        "## 3. 观点聚类（每类输出若干簇：标题、核心意思、代表评论原文、点赞权重大致影响力）\n"
        "## 4. 总结（主流共识、最大争议点、最关注问题、整体情绪倾向）\n\n"
        "数据如下（JSON）：\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    content = openai_chat(
        [{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
        model=model,
    )
    return content.strip() + "\n"


def build_report(raw_comments: List[Dict[str, Any]], cleaned: List[Dict[str, Any]], clean_stats: Dict[str, Any]) -> str:
    if os.getenv("OPENAI_API_KEY"):
        try:
            return build_report_openai(raw_comments, cleaned, clean_stats)
        except Exception:
            return build_report_local(raw_comments, cleaned, clean_stats)
    return build_report_local(raw_comments, cleaned, clean_stats)

