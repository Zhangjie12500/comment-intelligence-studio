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


# 视频类型关键词
VIDEO_TYPE_PATTERNS = {
    "测评类": ["测评", "评测", "对比", "横评", "体验", "使用感受", "开箱", "上手", "review", "评测", "test"],
    "多商品对比类": ["对比", "哪个好", "选哪个", "比较", "横评", "测评", "推荐", "避坑", "推荐"],
    "攻略类": ["攻略", "教程", "入门", "指南", "怎么", "如何", "技巧", "教学", "分享", "上手", "玩法"],
    "科普类": ["科普", "原理", "为什么", "是什么", "讲解", "解析", "知识", "介绍", "说明", "science"],
    "娱乐类": ["搞笑", "整活", "娱乐", "沙雕", "鬼畜", "娱乐", "爆笑", "趣味", "funny", "好笑"],
    "观点类": ["观点", "看法", "认为", "觉得", "态度", "看法", "评价", "见解", "想法"],
    "带货类": ["购买", "链接", "推荐", "种草", "下单", "买", "入手", "值得", "性价比", "优惠"],
    "vlog类": ["日常", "vlog", "生活", "记录", "分享", "一天", "记录", "日志", "日志"],
}


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


def classify_video_type(
    video_title: str = "",
    video_desc: str = "",
    subtitle_text: str = "",
    comments: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Classify video type based on title, description, subtitle, and comments.
    Returns: {primary, secondary, confidence, reason}
    """
    comments = comments or []
    
    # Combine all text sources for analysis
    all_text = " ".join([
        video_title or "",
        video_desc or "",
        subtitle_text[:2000] if subtitle_text else "",
    ])
    
    # Add comment text
    comment_texts = [c.get("text", "")[:100] for c in comments[:20]]
    all_text += " " + " ".join(comment_texts)
    
    # Count type matches
    type_scores: Dict[str, float] = {}
    type_matches: Dict[str, List[str]] = {}
    
    for vtype, keywords in VIDEO_TYPE_PATTERNS.items():
        score = 0.0
        matches = []
        for kw in keywords:
            if kw.lower() in all_text.lower():
                score += 1.0
                matches.append(kw)
        if score > 0:
            type_scores[vtype] = score
            type_matches[vtype] = matches
    
    # If no matches, default to "其他"
    if not type_scores:
        return {
            "primary": "其他",
            "secondary": "",
            "confidence": 0.3,
            "reason": "未能识别明确类型，归类为其他类视频"
        }
    
    # Sort by score
    sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Primary type (highest score)
    primary = sorted_types[0][0]
    primary_score = sorted_types[0][1]
    
    # Secondary type (if exists and significantly different)
    secondary = ""
    for vtype, score in sorted_types[1:]:
        # Only consider if score is at least 50% of primary
        if score >= primary_score * 0.5:
            secondary = vtype
            break
    
    # Calculate confidence (0-1)
    max_possible = sum(len(kws) for kws in VIDEO_TYPE_PATTERNS.values())
    confidence = min(primary_score / 3.0, 1.0)  # Cap at 1.0
    
    # Generate reason
    primary_keywords = type_matches.get(primary, [])
    reason = f"根据关键词「{', '.join(primary_keywords[:3])}」判断为{primary}内容"
    if secondary:
        reason += f"，辅以{secondary}特征"
    
    return {
        "primary": primary,
        "secondary": secondary,
        "confidence": round(confidence, 2),
        "reason": reason
    }


def is_low_info_density(text: str) -> Tuple[bool, str]:
    """
    Check if comment has low information density.
    Returns: (is_low_info, reason)
    """
    t = text.strip()
    if not t:
        return True, "空内容"
    
    # Check for spam patterns
    spam_patterns = [
        (r"^(.)\1{5,}$", "字符重复刷屏"),
        (r"^(.)\1{2,}(.)\2{2,}$", "循环刷屏"),
    ]
    for pattern, reason in spam_patterns:
        if re.match(pattern, t):
            return True, reason
    
    # Check for emoji-only
    if is_probably_emoji_only(t):
        return True, "纯表情"
    
    # Check for meaningless short patterns
    meaningless_patterns = [
        r"^(哈)+[！!。]*$",
        r"^(哈哈)+[！!。]*$",
        r"^(笑死)+[！!。]*$",
        r"^(牛)+[！!。]*$",
        r"^(6)+$",
        r"^(666)+$",
        r"^(233)+[！!。]*$",
        r"^[\.。!！?？]{1,3}$",
        r"^绷不住了+$",
        r"^蚌埠住了+$",
        r"^草+$",
        r"^笑崩了+$",
        r"^救命+$",
    ]
    for pattern in meaningless_patterns:
        if re.match(pattern, t):
            return True, "低信息密度"
    
    return False, ""


def clean_and_merge_v2(
    comments: List[Dict[str, Any]],
    video_type: str = "其他",
    similarity_threshold: float = 0.88,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Enhanced comment cleaning with video-type-aware logic.
    
    Key principles:
    1. Always keep at least some comments (fallback to raw if needed)
    2. Never filter out ALL comments
    3. Handle empty/removed comments gracefully
    4. Individual comment errors don't fail the batch
    
    For 娱乐类 videos: Keep more low-info comments (笑点反馈)
    For 测评/攻略/科普: More aggressive filtering but still keep minimum
    """
    import traceback
    
    raw_n = len(comments)
    if raw_n == 0:
        return [], {"raw": 0, "cleaned": 0, "removed": 0, "details": {}, "fallback_used": False}
    
    cleaned: List[Dict[str, Any]] = []
    seen_norm: set[str] = set()
    
    # Stats tracking
    stats = {
        "raw": raw_n,
        "cleaned": 0,
        "removed": 0,
        "parse_errors": 0,
        "fallback_used": False,
        "details": {
            "empty": 0,
            "emoji_only": 0,
            "low_info_density": 0,
            "spam": 0,
            "duplicate": 0,
            "similar_merged": 0,
            "removed_comments": 0,
            "kept_minimum": 0,
            "removed": 0,  # Track removed count for debugging
        }
    }
    
    # Determine filtering aggressiveness based on video type
    # But always keep at least some comments
    low_info_tolerance = 0
    
    if video_type == "娱乐类":
        low_info_tolerance = 10  # Keep more humor feedback
    elif video_type == "vlog类":
        low_info_tolerance = 5
    elif video_type in ["测评类", "攻略类", "科普类", "多商品对比类"]:
        low_info_tolerance = 3
    elif video_type == "观点类":
        low_info_tolerance = 4
    elif video_type == "带货类":
        low_info_tolerance = 3
    else:
        low_info_tolerance = 5
    
    # Track kept comments for minimum guarantee
    all_kept_for_minimum: List[Dict[str, Any]] = []
    
    for c in comments:
        # Safely handle individual comment parse errors
        try:
            # Get text, handling None and various formats
            raw_text = c.get("text")
            if raw_text is None:
                text = ""
            elif isinstance(raw_text, str):
                text = raw_text.strip()
            else:
                text = str(raw_text).strip()
            
            # Track if this is a removed/deleted comment
            is_removed = False
            removed_markers = ["removed", "deleted", "unavailable", "[已删除]", "[removed]", "[deleted]", "此评论已被删除"]
            if text.lower() in [m.lower() for m in removed_markers]:
                is_removed = True
            if c.get("is_removed") or c.get("deleted") or c.get("is_deleted"):
                is_removed = True
            
            # Skip removed comments
            if is_removed:
                stats["details"]["removed_comments"] += 1
                stats["details"]["removed"] += 1
                continue
            
            # For empty text comments - KEEP THEM but mark
            if not text:
                stats["details"]["empty"] += 1
                # Keep the comment but mark it
                c["_is_empty"] = True
                c["_empty_reason"] = "text_empty"
                all_kept_for_minimum.append(c)
                cleaned.append(c)
                continue
            
            # Skip pure emoji (but keep short text)
            if is_probably_emoji_only(text):
                # Check if it's too short to be meaningful
                if len(text) <= 5:
                    stats["details"]["emoji_only"] += 1
                    # Keep short emoji comments for minimum
                    c["_is_emoji_only"] = True
                    all_kept_for_minimum.append(c)
                    cleaned.append(c)
                    continue
                else:
                    # Longer emoji text - skip
                    stats["details"]["emoji_only"] += 1
                    stats["details"]["removed"] += 1
                    continue
            
            # Check for spam
            is_spam, spam_reason = is_low_info_density(text)
            if is_spam:
                # For entertainment videos, be more lenient with spam
                if video_type == "娱乐类" and len(cleaned) < 20:
                    c["_is_spam"] = True
                    c["_spam_reason"] = spam_reason
                    all_kept_for_minimum.append(c)
                    cleaned.append(c)
                    stats["details"]["spam"] += 1
                    continue
                else:
                    stats["details"]["spam"] += 1
                    stats["details"]["removed"] += 1
                    continue
            
            # Check for low info density - but keep some
            is_low, low_reason = is_low_info_density(text)
            if is_low:
                if len(all_kept_for_minimum) < low_info_tolerance:
                    c["_is_low_info"] = True
                    c["_low_info_reason"] = low_reason
                    all_kept_for_minimum.append(c)
                    cleaned.append(c)
                    stats["details"]["low_info_density"] += 1
                    continue
                else:
                    stats["details"]["removed"] += 1
                    continue
            
            # Normalize and check for duplicates
            try:
                norm = normalize_for_dedup(text)
            except Exception:
                norm = text.lower()[:50]  # Fallback normalization
            
            if not norm:
                stats["details"]["empty"] += 1
                c["_is_empty"] = True
                c["_empty_reason"] = "normalize_failed"
                all_kept_for_minimum.append(c)
                cleaned.append(c)
                continue
            
            if norm in seen_norm:
                stats["details"]["duplicate"] += 1
                stats["details"]["removed"] += 1
                continue
            
            # Check for similar comments
            merged = False
            for existing in cleaned:
                try:
                    en = normalize_for_dedup(existing.get("text") or "")
                    if en and jaccard_similarity(norm, en) >= similarity_threshold:
                        stats["details"]["similar_merged"] += 1
                        merged = True
                        if int(c.get("like") or 0) > int(existing.get("like") or 0):
                            existing.update(c)
                        break
                except Exception:
                    continue
            
            if merged:
                stats["details"]["removed"] += 1
                continue
            
            seen_norm.add(norm)
            cleaned.append(c)
            
        except Exception as e:
            # Safely skip individual comment parse errors
            stats["parse_errors"] = stats.get("parse_errors", 0) + 1
            stats["details"]["removed"] += 1
            # Keep this comment anyway for minimum
            c["_parse_error"] = True
            all_kept_for_minimum.append(c)
            cleaned.append(c)
            continue
    
    stats["cleaned"] = len(cleaned)
    stats["removed"] = raw_n - len(cleaned)
    
    # CRITICAL: Ensure we always have at least some comments
    # If cleaning removed everything, use raw comments as fallback
    if stats["cleaned"] == 0 and raw_n > 0:
        # Fallback: use first 50 raw comments
        fallback_comments = comments[:50]
        # Mark them as fallback
        for fc in fallback_comments:
            fc["_fallback"] = True
        stats["fallback_used"] = True
        stats["details"]["kept_minimum"] = len(fallback_comments)
        return fallback_comments, stats
    
    # Ensure minimum of 10 comments if we have raw comments
    if stats["cleaned"] < 10 and raw_n >= 10:
        # Add some raw comments to meet minimum
        remaining_slots = 10 - stats["cleaned"]
        for rc in comments:
            if len(cleaned) >= 10:
                break
            if rc not in cleaned:
                rc["_added_for_minimum"] = True
                cleaned.append(rc)
                stats["details"]["kept_minimum"] += 1
        stats["cleaned"] = len(cleaned)
        stats["removed"] = raw_n - len(cleaned)
    
    return cleaned, stats


def clean_and_merge(
    comments: List[Dict[str, Any]],
    similarity_threshold: float = 0.92,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Legacy function for backwards compatibility."""
    return clean_and_merge_v2(comments, "其他", similarity_threshold)


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
    """
    Compute semantic clusters from comments using LLM.

    Falls back to keyword-based clustering if OpenAI API is not available.
    """
    if not comments:
        return []

    # Check if OpenAI API is available
    if not os.getenv("OPENAI_API_KEY"):
        return _compute_clusters_keyword_fallback(comments)

    # Prepare comments for LLM (max 200)
    sample_comments = comments[:200]

    # Format comments for prompt
    comment_lines = []
    for i, c in enumerate(sample_comments, 1):
        text = c.get("text", "")[:150]  # Truncate long comments
        likes = c.get("like", 0)
        comment_lines.append(f"{i}. [{likes}赞] {text}")

    comments_text = "\n".join(comment_lines)
    total_count = len(sample_comments)

    # Determine number of clusters based on comment count
    num_clusters = min(max(3, total_count // 30), 6)

    prompt = f"""你是一个视频评论分析专家。
请将以下评论总结为 {num_clusters}-{num_clusters+1} 个核心观点。

要求：
1. 不要直接复制评论原句。
2. 使用抽象、概括性的表达。
3. 每个观点一句话。
4. 标注情绪倾向：positive / neutral / negative / mixed。
5. 估算该观点大致占比 ratio，范围 0-1，所有占比之和应接近 1。
6. 每个观点保留 1-2 条代表评论 examples。
7. 输出必须是合法 JSON。
8. 不要输出 Markdown 代码块标记。

评论列表（共{total_count}条）：
{comments_text}

输出格式：
{{
  "opinion_clusters": [
    {{
      "summary": "观众认为嘉宾表达能力强，但部分内容仍显得不够深入。",
      "sentiment": "positive",
      "ratio": 0.32,
      "examples": ["代表评论1...", "代表评论2..."]
    }}
  ]
}}

只输出JSON，不要有其他文字："""

    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = _llm_call(
            [{"role": "user", "content": prompt}],
            model=model,
            max_tokens=1500
        )

        # Parse JSON response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError("No JSON found in response")

        data = json.loads(json_match.group())

        # Extract clusters - handle both "opinion_clusters" and direct array
        clusters_list = data.get("opinion_clusters") or data.get("clusters") or []

        # Build result
        result = []
        for item in clusters_list:
            cluster = {
                "summary": item.get("summary", ""),
                "sentiment": item.get("sentiment", "neutral"),
                "ratio": float(item.get("ratio", 0)),
                "count": int(item.get("ratio", 0) * total_count),
                "examples": item.get("examples", [])[:2],
                "keywords": [],
            }
            result.append(cluster)

        if not result:
            raise ValueError("No valid clusters extracted")

        # Sort by ratio (most common first)
        result.sort(key=lambda x: x["ratio"], reverse=True)
        return result

    except Exception as e:
        print(f"[clusters] LLM clustering failed: {e}, falling back to keyword-based")
        return _compute_clusters_keyword_fallback(comments)


def _compute_clusters_keyword_fallback(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keyword-based clustering fallback.
    Used when OpenAI API is not available or fails.
    """
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
    total = len(comments)
    for key, b in buckets.items():
        examples = sorted(b["examples"], key=lambda x: int(x.get("like") or 0), reverse=True)
        representative = examples[:3]
        result.append({
            "summary": key.replace("_", " ")[:40],  # Use as summary in fallback
            "sentiment": "neutral",
            "ratio": b["count"] / max(total, 1),
            "count": b["count"],
            "keywords": b["keywords"][:6],
            "like_weight": b["like_weight"],
            "examples": [e.get("text", "")[:100] for e in representative],
            "representative_comments": [
                {
                    "user": e.get("user", ""),
                    "text": e.get("text", ""),
                    "like": int(e.get("like") or 0),
                }
                for e in representative
            ],
        })

    result.sort(key=lambda x: x.get("like_weight", 0), reverse=True)
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
) -> Dict[str, Any]:
    """
    Generate a structured summary based on analysis results.
    Returns: {title, summary, points, sections, _fallback}
    """
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

    # Top cluster summaries
    top_clusters = clusters[:5] if clusters else []
    top_cluster_summaries = []
    for c in top_clusters:
        if c.get("summary"):
            top_cluster_summaries.append(c["summary"])
        elif c.get("title"):
            top_cluster_summaries.append(c["title"])

    platform_label = "B站（bilibili）" if platform == "bilibili" else "YouTube"

    # Build structured summary
    result = {
        "title": "评论区整体分析",
        "summary": "",
        "points": [],
        "sections": {},
        "_fallback": True,  # Mark as rule-based
    }

    # Main summary
    summary_parts = [
        f"本次分析共抓取 {raw_count} 条评论，清洗后保留 {cleaned_count} 条。",
        f"评论区整体以「{dominant_label}」为主，共 {dominant_n} 条，占比约 {dominant_pct}%。",
    ]
    
    if oppose_n > 0:
        summary_parts.append(f"存在 {oppose_n} 条质疑或反对声音（占比约 {oppose_n*100//max(total,1)}%），评论区存在一定观点分歧。")
    if question_n > 0:
        summary_parts.append(f"共有 {question_n} 条提问或求证类评论，部分用户在寻求更多信息。")
    if joke_n > neutral_n * 0.5:
        summary_parts.append("调侃/玩梗类评论较多，评论区氛围偏轻松娱乐。")
    if support_n > oppose_n * 3:
        summary_parts.append("正面情感占绝对主导，观众整体态度积极。")

    result["summary"] = " ".join(summary_parts)

    # Key points
    points = []
    if top_cluster_summaries:
        points.append(f"主要讨论围绕：{'；'.join(top_cluster_summaries[:3])}")
    if oppose_n > 0:
        points.append(f"存在 {oppose_n} 条反对/质疑声音，需关注用户疑虑")
    if question_n > 0:
        points.append(f" {question_n} 条评论提出问题，可考虑补充相关内容")
    if joke_n > neutral_n:
        points.append("评论区玩梗氛围浓厚，可考虑增加互动内容")
    
    result["points"] = points[:5]

    # Sections
    if top_cluster_summaries:
        result["sections"]["核心主题"] = top_cluster_summaries[:5]
    
    if oppose_n > 0:
        result["sections"]["关注点"] = [
            f"存在 {oppose_n} 条反对/质疑声音（{oppose_n*100//max(total,1)}%）"
        ]
    
    if question_n > 0:
        result["sections"]["用户疑问"] = [
            f" {question_n} 条评论提出问题或求证"
        ]

    return result


def compute_summary_ai(
    stance_stats: Dict[str, int],
    clusters: List[Dict[str, Any]],
    cleaned_count: int,
    raw_count: int,
    platform: str,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Generate AI-powered structured summary.
    Falls back to rule-based if LLM fails.
    """
    if not os.getenv("OPENAI_API_KEY"):
        return compute_summary(stance_stats, clusters, cleaned_count, raw_count, platform)
    
    try:
        # Prepare context
        support_n = stance_stats.get("support", 0)
        oppose_n = stance_stats.get("oppose", 0)
        question_n = stance_stats.get("question", 0)
        joke_n = stance_stats.get("joke", 0)
        neutral_n = stance_stats.get("neutral", 0)
        total = support_n + oppose_n + question_n + joke_n + neutral_n

        # Cluster summaries
        cluster_texts = []
        for c in clusters[:8]:
            if c.get("summary"):
                cluster_texts.append(f"- {c['summary']} (占比: {int(c.get('ratio', 0) * 100)}%)")
            elif c.get("title"):
                cluster_texts.append(f"- {c['title']}")

        prompt = f"""你是一个视频评论分析专家。请根据以下分析数据，生成结构化的评论总结。

数据分析：
- 总评论数：{cleaned_count} 条（清洗后）
- 原始评论数：{raw_count} 条
- 支持/认同：{support_n} 条（{support_n*100//max(total,1)}%）
- 质疑/反对：{oppose_n} 条（{oppose_n*100//max(total,1)}%）
- 提问/求证：{question_n} 条（{question_n*100//max(total,1)}%）
- 调侃/玩梗：{joke_n} 条（{joke_n*100//max(total,1)}%）
- 中立/补充：{neutral_n} 条（{neutral_n*100//max(total,1)}%）

观点聚类：
{chr(10).join(cluster_texts) if cluster_texts else "无聚类数据"}

请生成以下JSON格式（只输出JSON）：
{{
    "title": "总结标题（不超过20字）",
    "summary": "2-3句整体总结",
    "points": ["观点1", "观点2", "观点3", "观点4"],
    "sections": {{
        "核心主题": ["主题1", "主题2"],
        "关注点": ["关注1"]
    }}
}}

要求：
- 不要复述原句
- 使用抽象表达
- points 3-5条，每条不超过30字"""

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response = _llm_call([{"role": "user", "content": prompt}], model=model)
        
        if not response:
            return compute_summary(stance_stats, clusters, cleaned_count, raw_count, platform)
        
        # Parse JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            result = json.loads(json_match.group())
            result["_fallback"] = False
            return result
        
        return compute_summary(stance_stats, clusters, cleaned_count, raw_count, platform)

    except Exception as e:
        print(f"[summary] AI summary failed: {e}")
        return compute_summary(stance_stats, clusters, cleaned_count, raw_count, platform)


def compute_summary_ai_with_status(
    stance_stats: Dict[str, int],
    clusters: List[Dict[str, Any]],
    cleaned_count: int,
    raw_count: int,
    platform: str,
    model: str = "gpt-4o-mini",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Generate AI summary with status info.
    Returns: (summary_dict, ai_status_dict)
    """
    try:
        result = compute_summary_ai(stance_stats, clusters, cleaned_count, raw_count, platform, model)
        ai_status = {
            "enabled": True,
            "model": model,
            "message": "AI总结已启用。",
            "error": None
        }
        return result, ai_status
    except Exception as e:
        # Fallback to rule-based
        result = compute_summary(stance_stats, clusters, cleaned_count, raw_count, platform)
        ai_status = {
            "enabled": False,
            "model": model,
            "message": "AI总结不可用，已使用规则分析结果。",
            "error": str(e)
        }
        return result, ai_status


def parse_json_safely(text: str):
    """
    Safely parse JSON from text with fallback extraction.
    Returns parsed JSON dict/list or None if parsing fails.
    """
    import re
    if not text:
        return None

    # Try direct parse first
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to extract first JSON block from text
    try:
        json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', text)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    return None


def compute_opinion_clusters_ai_with_status(
    comments: List[Dict[str, Any]],
    fallback_clusters: List[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Generate AI-powered opinion clusters with status info.
    Returns: (result_dict, ai_status_dict)

    result_dict structure:
    {
        "opinion_clusters": [
            {
                "summary": "抽象观点总结",
                "sentiment": "positive",
                "ratio": 0.32,
                "examples": ["代表评论1", "代表评论2"]
            }
        ]
    }
    """
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Prepare comments
    sample_comments = comments[:200]
    comment_lines = []
    for i, c in enumerate(sample_comments, 1):
        text = (c.get("text") or "")[:200]  # Truncate to 200 chars
        likes = c.get("like", 0)
        comment_lines.append(f"{i}. [{likes}赞] {text}")

    comments_text = "\n".join(comment_lines)
    total_count = len(sample_comments)
    num_clusters = min(max(3, total_count // 40), 5)

    prompt = f"""你是一个视频评论分析专家。
请将以下评论总结为 {num_clusters} 个核心观点。

要求：
1. 不要直接复制评论原句。
2. 使用抽象、概括性的表达。
3. 每个观点一句话。
4. sentiment 只能是 positive / neutral / negative / mixed。
5. ratio 是 0-1 之间的小数，所有 ratio 之和应接近 1。
6. examples 保留 1-2 条代表评论（简短摘要）。
7. 输出必须是合法 JSON。
8. 不要输出 Markdown。
9. 不要输出代码块。

评论列表（共{total_count}条）：
{comments_text}

输出格式：
{{
  "opinion_clusters": [
    {{
      "summary": "观众认为嘉宾表达能力强，但部分内容仍显得不够深入。",
      "sentiment": "positive",
      "ratio": 0.32,
      "examples": ["代表评论1", "代表评论2"]
    }}
  ]
}}

只输出JSON，不要有其他文字："""

    try:
        response = _llm_call(
            [{"role": "user", "content": prompt}],
            model=model,
            max_tokens=1500,
        )

        if not response:
            raise ValueError("Empty response from LLM")

        # Parse JSON safely
        parsed = parse_json_safely(response)
        if not parsed:
            raise ValueError("Failed to parse JSON response")

        clusters_list = parsed.get("opinion_clusters") or []

        # Build result
        result = {
            "opinion_clusters": []
        }
        for item in clusters_list:
            cluster = {
                "summary": item.get("summary", ""),
                "sentiment": item.get("sentiment", "neutral"),
                "ratio": float(item.get("ratio", 0)),
                "examples": (item.get("examples") or [])[:2],
            }
            result["opinion_clusters"].append(cluster)

        if not result["opinion_clusters"]:
            raise ValueError("No valid clusters extracted")

        # Sort by ratio (most common first)
        result["opinion_clusters"].sort(key=lambda x: x["ratio"], reverse=True)

        ai_status = {
            "enabled": True,
            "model": model,
            "message": "AI总结已启用。",
            "error": None
        }
        return result, ai_status

    except Exception as e:
        # Fallback to existing rule-based clusters
        fallback = fallback_clusters or []
        ai_status = {
            "enabled": False,
            "model": model,
            "message": "AI总结不可用，已使用规则分析结果。",
            "error": str(e)
        }
        return {"opinion_clusters": fallback}, ai_status


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


# ──────────────────────────────────────────────────
# LLM Functions - 使用统一 llm 模块
# ──────────────────────────────────────────────────

def _llm_call(
    messages: List[Dict[str, str]],
    model: str = "",
    temperature: float = 0.3,
    max_tokens: int = 800,
) -> str:
    """
    调用统一 LLM 接口，返回响应内容或空字符串
    """
    from backend.llm import call_llm, get_llm_config

    config = get_llm_config()
    model = model.strip() or config.get("model", "gpt-4o-mini")

    # 构建 prompt
    prompt = messages[-1].get("content", "") if messages else ""
    system_prompt = messages[0].get("content", "") if messages and messages[0].get("role") == "system" else ""

    result = call_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if result["ok"]:
        return result["content"]
    else:
        print(f"[LLM] 调用失败: {result['error']}")
        return ""


def translate_to_zh(text: str) -> str:
    """翻译英文到中文"""
    if not text.strip():
        return ""
    
    from backend.llm import translate_to_zh as llm_translate
    return llm_translate(text)


# ──────────────────────────────────────────────────
# Video Summary Functions
# ──────────────────────────────────────────────────

def fetch_youtube_subtitles(video_id: str) -> tuple[bool, str]:
    """
    Fetch subtitles from YouTube video using transcript API.
    Returns (has_subtitle, subtitle_text).
    """
    try:
        import urllib.request
        import urllib.parse
        
        # Try YouTube transcript API (unofficial but widely available)
        transcript_url = f"https://youtubetranscript.com/?v={video_id}"
        
        try:
            req = urllib.request.Request(
                transcript_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ViewLens/1.0)"}
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode('utf-8')
        except Exception:
            # Fallback: try invidious instance
            try:
                invidious_url = f"https://yewtu.be/api/v1/videos/{video_id}"
                req = urllib.request.Request(
                    invidious_url,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    subtitles = data.get('subtitles', []) or []
                    if subtitles:
                        # Get English subtitle if available, otherwise first available
                        eng_sub = next((s for s in subtitles if s.get('lang', '').startswith('en')), None)
                        sub = eng_sub or subtitles[0]
                        sub_url = sub.get('url', '')
                        if sub_url:
                            sub_req = urllib.request.Request(
                                sub_url,
                                headers={"User-Agent": "Mozilla/5.0"}
                            )
                            with urllib.request.urlopen(sub_req, timeout=15) as sub_resp:
                                sub_content = sub_resp.read().decode('utf-8')
                                # Parse VTT format
                                text = parse_vtt_subtitle(sub_content)
                                if text:
                                    return True, text
            except Exception:
                pass
            
            # Try YouTube Data API for captions (requires API key, limited)
            api_key = os.getenv("YOUTUBE_API_KEY")
            if api_key:
                try:
                    captions_url = f"https://www.googleapis.com/youtube/v3/captions?part=snippet&videoId={video_id}&key={api_key}"
                    cap_req = urllib.request.Request(
                        captions_url,
                        headers={"User-Agent": "Mozilla/5.0"}
                    )
                    with urllib.request.urlopen(cap_req, timeout=10) as cap_resp:
                        cap_data = json.loads(cap_resp.read().decode('utf-8'))
                        items = cap_data.get('items', []) or []
                        if items:
                            # Has captions, but downloading requires OAuth in most cases
                            return True, ""  # Has caption but can't download without OAuth
                except Exception:
                    pass
            
            return False, ""
        
        # Parse transcript XML
        text = parse_youtube_transcript_xml(content)
        return len(text.strip()) > 50, text
        
    except Exception:
        return False, ""


def parse_youtube_transcript_xml(content: str) -> str:
    """Parse YouTube transcript XML content."""
    import re
    # Extract text between <text> tags
    matches = re.findall(r'<text[^>]*>([^<]+)</text>', content)
    return ' '.join(matches)


def parse_vtt_subtitle(content: str) -> str:
    """Parse WebVTT subtitle format."""
    import re
    lines = content.split('\n')
    text_parts = []
    capture = False
    for line in lines:
        line = line.strip()
        if line == '' or line.startswith('WEBVTT') or line.startswith('NOTE') or line.startswith('STYLE'):
            continue
        if '-->' in line:
            capture = True
            continue
        if capture and line:
            # Remove HTML tags if any
            clean = re.sub(r'<[^>]+>', '', line)
            if clean.strip():
                text_parts.append(clean.strip())
    return ' '.join(text_parts)


def fetch_bilibili_subtitles(bvid: str) -> tuple[bool, str]:
    """
    Fetch subtitles from Bilibili video.
    Returns (has_subtitle, subtitle_text).
    """
    try:
        # Bilibili subtitle API
        url = f"https://api.bilibili.com/x/player/v2?bvid={bvid}"
        req = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com/"
            },
            timeout=10
        )
        
        if req.status_code == 200:
            data = req.json()
            if data.get('code') == 0:
                data = data.get('data', {}) or {}
                subtitle = data.get('subtitle', {}) or {}
                subtitles_list = subtitle.get('subtitles', []) or []
                
                if subtitles_list:
                    # Try to fetch subtitle content
                    first_sub = subtitles_list[0]
                    sub_url = first_sub.get('subtitle_url', '')
                    if sub_url:
                        if not sub_url.startswith('http'):
                            sub_url = 'https:' + sub_url
                        sub_req = requests.get(sub_url, timeout=10)
                        if sub_req.status_code == 200:
                            sub_data = sub_req.json()
                            # Parse Bilibili subtitle JSON format
                            body = sub_data.get('body', []) or []
                            text_parts = []
                            for item in body:
                                content = item.get('content', '')
                                if content:
                                    text_parts.append(content)
                            return True, ''.join(text_parts)
                    return True, ""
        return False, ""
    except Exception:
        return False, ""


def generate_video_summary(
    subtitle_text: str,
    video_title: str = "",
    video_desc: str = "",
    top_comments: List[Dict[str, Any]] = None,
    platform: str = "",
) -> Dict[str, Any]:
    """
    Generate video summary using AI if available, otherwise fallback to rule-based.
    Returns video_summary dict with: has_subtitle, summary, key_points, accuracy_note
    """
    top_comments = top_comments or []
    
    # Check if we have subtitle
    has_subtitle = len(subtitle_text.strip()) > 50
    
    if not has_subtitle:
        # Weak summary without subtitle
        if not os.getenv("OPENAI_API_KEY"):
            return {
                "has_subtitle": False,
                "summary": "暂无字幕内容，无法生成视频摘要。请配置 OPENAI_API_KEY 以启用 AI 摘要功能。",
                "key_points": [],
                "accuracy_note": "未检测到字幕，摘要准确性较低"
            }
        
        # Generate weak summary from title + comments
        try:
            return _generate_weak_summary_ai(video_title, video_desc, top_comments, platform)
        except Exception:
            return {
                "has_subtitle": False,
                "summary": f"视频标题：{video_title or '未知'}\n\n基于评论分析，视频内容摘要：\n" + _generate_rule_based_summary(top_comments),
                "key_points": _extract_key_points_from_comments(top_comments),
                "accuracy_note": "未检测到字幕，此摘要基于视频标题和评论内容生成，准确性较低"
            }
    
    # We have subtitle, generate proper summary
    if not os.getenv("OPENAI_API_KEY"):
        # Rule-based summary with subtitle
        return {
            "has_subtitle": True,
            "summary": _generate_rule_based_summary_from_subtitle(subtitle_text[:3000]),
            "key_points": _extract_key_points_from_subtitle(subtitle_text[:3000]),
            "accuracy_note": "基于字幕内容生成，建议结合评论理解完整内容"
        }
    
    try:
        return _generate_summary_ai(subtitle_text, video_title, top_comments, platform)
    except Exception:
        # Fallback to rule-based
        return {
            "has_subtitle": True,
            "summary": _generate_rule_based_summary_from_subtitle(subtitle_text[:3000]),
            "key_points": _extract_key_points_from_subtitle(subtitle_text[:3000]),
            "accuracy_note": "基于字幕内容生成（AI摘要生成失败，使用规则摘要）"
        }


def _generate_summary_ai(
    subtitle_text: str,
    video_title: str,
    top_comments: List[Dict[str, Any]],
    platform: str,
) -> Dict[str, Any]:
    """Generate video summary using OpenAI."""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Prepare context
    comments_text = ""
    if top_comments:
        sample_comments = top_comments[:10]
        comments_text = "\n\n高赞评论摘要：\n" + "\n".join(
            f"- {c.get('text', '')[:100]}" for c in sample_comments
        )
    
    prompt = f"""你是一个视频内容分析专家。请根据以下信息生成视频内容摘要。

视频标题：{video_title or '未知'}

视频字幕内容：
{subtitle_text[:4000]}{comments_text}

请生成以下格式的JSON响应（只输出JSON，不要其他内容）：
{{
    "summary": "用2-3句话概括视频的核心内容",
    "key_points": ["要点1", "要点2", "要点3", "要点4", "要点5"],
    "accuracy_note": "简要说明摘要的准确性和局限性"
}}

要求：
1. summary使用中文，简洁明了
2. key_points列出5个左右视频的主要观点或知识点
3. accuracy_note说明摘要的可靠程度
4. 只输出JSON，不要有其他文字"""
    
    response = _llm_call([{"role": "user", "content": prompt}], model=model)
    
    # Parse JSON response
    try:
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response)
        
        return {
            "has_subtitle": True,
            "summary": result.get("summary", ""),
            "key_points": result.get("key_points", [])[:5],
            "accuracy_note": result.get("accuracy_note", "基于字幕和评论内容生成")
        }
    except Exception:
        # Fallback if JSON parsing fails
        return {
            "has_subtitle": True,
            "summary": response[:500] if response else "无法生成摘要",
            "key_points": _extract_key_points_from_subtitle(subtitle_text[:3000]),
            "accuracy_note": "摘要生成可能不完整"
        }


def _generate_weak_summary_ai(
    video_title: str,
    video_desc: str,
    top_comments: List[Dict[str, Any]],
    platform: str,
) -> Dict[str, Any]:
    """Generate weak summary when no subtitle available using AI."""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    comments_text = ""
    if top_comments:
        sample = top_comments[:15]
        comments_text = "\n\n高赞评论摘要：\n" + "\n".join(
            f"- {c.get('text', '')[:150]}" for c in sample
        )
    
    prompt = f"""你是一个视频内容分析专家。由于没有字幕，请根据视频标题和评论内容推测视频可能的主题和内容。

视频标题：{video_title or '未知'}
视频简介：{video_desc or '无'}
{comments_text}

请生成以下格式的JSON响应（只输出JSON，不要其他内容）：
{{
    "summary": "根据评论推测的视频内容，用2-3句话描述",
    "key_points": ["推测要点1", "推测要点2", "推测要点3"],
    "accuracy_note": "说明：由于没有字幕，此摘要是基于评论内容推测得出的，准确度有限"
}}

注意：
1. 这是一个基于评论推测的摘要，可能不完全准确
2. key_points应该是评论中反映出的主要讨论话题
3. 只输出JSON，不要有其他文字"""
    
    response = _llm_call([{"role": "user", "content": prompt}], model=model)
    
    try:
        import re
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response)
        
        return {
            "has_subtitle": False,
            "summary": result.get("summary", ""),
            "key_points": result.get("key_points", [])[:5],
            "accuracy_note": result.get("accuracy_note", "未检测到字幕，摘要基于评论推测，准确度有限")
        }
    except Exception:
        return {
            "has_subtitle": False,
            "summary": f"视频标题：{video_title or '未知'}\n\n基于评论分析：\n" + _generate_rule_based_summary(top_comments),
            "key_points": _extract_key_points_from_comments(top_comments),
            "accuracy_note": "未检测到字幕，摘要基于评论推测生成，准确度有限"
        }


def _generate_rule_based_summary(top_comments: List[Dict[str, Any]]) -> str:
    """Generate summary from comments using rule-based approach."""
    if not top_comments:
        return "暂无足够评论数据生成摘要。"
    
    # Get top comments text
    texts = [c.get('text', '')[:200] for c in top_comments[:10]]
    combined = ' '.join(texts)
    
    # Simple truncation-based summary
    if len(combined) > 300:
        return combined[:300] + "..."
    return combined


def _generate_rule_based_summary_from_subtitle(subtitle: str) -> str:
    """Generate summary from subtitle using rule-based approach."""
    # Take first 500 chars as summary (first part often contains intro)
    if len(subtitle) > 500:
        # Try to find a good break point
        cut = subtitle[:500]
        last_period = cut.rfind('。')
        if last_period > 200:
            return cut[:last_period+1]
        return cut + "..."
    return subtitle


def _extract_key_points_from_comments(top_comments: List[Dict[str, Any]]) -> List[str]:
    """Extract key points from comments using simple rules."""
    if not top_comments:
        return []
    
    # Get unique significant words from top comments
    import re
    all_text = ' '.join(c.get('text', '') for c in top_comments[:20])
    
    # Extract Chinese phrases (2-6 chars)
    phrases = re.findall(r'[\u4e00-\u9fff]{2,6}', all_text)
    
    # Filter common stop words and count frequency
    stop_words = {'什么', '怎么', '为什么', '这个', '那个', '一个', '真的', '可以', '不是', '就是', '但是', '所以', '因为', '如果', '没有'}
    filtered = [p for p in phrases if p not in stop_words and len(p) >= 2]
    
    # Count and get top phrases
    from collections import Counter
    counter = Counter(filtered)
    top_phrases = [p for p, _ in counter.most_common(10)]
    
    return top_phrases[:5]


def _extract_key_points_from_subtitle(subtitle: str) -> List[str]:
    """Extract key points from subtitle text."""
    import re
    
    # Extract sentences
    sentences = re.split(r'[。！？\n]', subtitle)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    # Get first 5 significant sentences
    points = []
    for s in sentences[:10]:
        if len(points) >= 5:
            break
        # Extract key phrase (first meaningful part)
        if len(s) > 50:
            s = s[:50] + "..."
        if s and s not in points:
            points.append(s)
    
    return points if points else ["暂无关键信息"]


def build_cleaning_summary(
    clean_stats: Dict[str, Any],
    video_type: str = "其他",
) -> Dict[str, Any]:
    """
    Build cleaning summary from cleaning stats.
    """
    # Handle both old and new stats format
    details = clean_stats.get("details", {}) if isinstance(clean_stats, dict) else {}
    
    original_count = clean_stats.get("raw", 0)
    cleaned_count = clean_stats.get("cleaned", 0)
    removed_count = clean_stats.get("removed", original_count - cleaned_count)
    
    # Low info count (new format) or meaningless_short (old format)
    low_info = details.get("low_info_density", 0) or details.get("meaningless_short", 0)
    
    # Duplicate count (new format) or duplicate + similar_merged (old format)
    duplicate = details.get("duplicate", 0) + details.get("similar_merged", 0)
    
    # Generate strategy description
    if video_type == "娱乐类":
        strategy = "宽松策略：保留部分低信息密度评论（如笑点反馈），以保留社区氛围"
    elif video_type == "测评类":
        strategy = "严格策略：重点过滤低信息密度评论，保留高质量反馈"
    elif video_type == "攻略类":
        strategy = "严格策略：过滤闲聊类评论，保留实用建议和问题"
    elif video_type == "科普类":
        strategy = "严格策略：过滤调侃类评论，保留知识点讨论"
    elif video_type == "多商品对比类":
        strategy = "中等策略：保留对比观点，过滤纯情绪化评论"
    elif video_type == "vlog类":
        strategy = "宽松策略：保留情感表达和互动类评论"
    elif video_type == "观点类":
        strategy = "中等策略：保留不同观点类评论，过滤无意义表达"
    elif video_type == "带货类":
        strategy = "中等策略：保留购买意向和商品咨询，过滤无意义评论"
    else:
        strategy = "标准策略：基础过滤，保持内容质量"
    
    return {
        "original_count": original_count,
        "cleaned_count": cleaned_count,
        "removed_count": removed_count,
        "low_info_count": low_info,
        "duplicate_count": duplicate,
        "strategy": strategy,
    }


def generate_content_comment_comparison(
    video_summary: Dict[str, Any] = None,
    video_type: Dict[str, Any] = None,
    cleaned: List[Dict[str, Any]] = None,
    clusters: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate content-comment comparison analysis.
    Compares what the video focuses on vs what the audience cares about.
    """
    video_summary = video_summary or {}
    video_type = video_type or {}
    cleaned = cleaned or []
    clusters = clusters or []
    
    # Extract video focus from video_summary key_points
    video_focus = video_summary.get("key_points", [])[:5]
    
    # Extract audience focus from clusters and top comments
    audience_focus = []
    if clusters:
        # Get top cluster titles as audience focus
        for cl in clusters[:5]:
            title = cl.get("title", "")
            if title and len(title) > 2:
                audience_focus.append(title[:30])
    
    # Also extract from high-liked comments keywords
    top_comments = sorted(cleaned, key=lambda x: int(x.get("like") or 0), reverse=True)[:20]
    comment_keywords = _extract_keywords_from_comments(top_comments)
    
    # Merge and deduplicate audience focus
    for kw in comment_keywords[:5]:
        if kw not in audience_focus:
            audience_focus.append(kw)
    
    audience_focus = audience_focus[:5]
    
    # Generate gap analysis
    video_focus_set = set(video_focus)
    audience_focus_set = set(audience_focus)
    
    overlap = video_focus_set & audience_focus_set
    video_only = video_focus_set - audience_focus_set
    audience_only = audience_focus_set - video_focus_set
    
    gap_parts = []
    if overlap:
        gap_parts.append(f"一致关注点：{'、'.join(list(overlap)[:3])}")
    if video_only:
        gap_parts.append(f"视频侧重但评论较少提及：{'、'.join(list(video_only)[:3])}")
    if audience_only:
        gap_parts.append(f"评论区关注但视频未深入：{'、'.join(list(audience_only)[:3])}")
    
    gap_analysis = "；".join(gap_parts) if gap_parts else "视频内容与评论关注点基本一致"
    
    # Generate audience needs (questions, complaints, requests)
    audience_needs = []
    questions = [c.get("text", "") for c in cleaned if c.get("stance") == "question"][:5]
    for q in questions[:3]:
        if len(q) > 5:
            audience_needs.append(f"观众疑问：{q[:50]}")
    
    opposes = [c.get("text", "") for c in cleaned if c.get("stance") == "oppose"][:5]
    for o in opposes[:2]:
        if len(o) > 5:
            audience_needs.append(f"观众质疑：{o[:50]}")
    
    audience_needs = audience_needs[:5]
    
    # Generate missed topics
    missed_topics = list(audience_only)[:3]
    
    # Add type-specific missed topics
    vtype = video_type.get("primary", "")
    if vtype == "测评类":
        if "价格" not in "".join(video_focus):
            missed_topics.append("价格/性价比讨论")
        if "购买" not in "".join(video_focus):
            missed_topics.append("购买渠道/优惠信息")
    elif vtype == "攻略类":
        if "常见问题" not in "".join(video_focus):
            missed_topics.append("常见问题/避坑指南")
    elif vtype == "科普类":
        if "纠错" not in "".join(video_focus):
            missed_topics.append("知识点纠错/补充")
    
    return {
        "video_focus": video_focus,
        "audience_focus": audience_focus,
        "gap_analysis": gap_analysis,
        "audience_needs": audience_needs,
        "missed_topics": missed_topics[:5],
    }


def _extract_keywords_from_comments(comments: List[Dict[str, Any]]) -> List[str]:
    """Extract meaningful keywords from comments."""
    import re
    all_text = " ".join(c.get("text", "") for c in comments)
    
    # Extract Chinese phrases (2-6 chars)
    phrases = re.findall(r'[\u4e00-\u9fff]{2,6}', all_text)
    
    # Filter stop words
    stop_words = {
        '什么', '怎么', '为什么', '这个', '那个', '一个', '真的', '可以', '不是', '就是',
        '但是', '所以', '因为', '如果', '没有', '哈哈', '哈哈哈', '笑死', '牛逼', '牛批',
        '厉害', '支持', '确实', '感觉', '觉得', '知道', '可能', '应该', '看到', '说完',
    }
    filtered = [p for p in phrases if p not in stop_words and len(p) >= 2]
    
    # Count frequency
    from collections import Counter
    counter = Counter(filtered)
    return [p for p, _ in counter.most_common(20)]


def generate_visualization_recommendation(
    video_type: Dict[str, Any] = None,
    cleaned: List[Dict[str, Any]] = None,
    clusters: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate visualization recommendation based on video type and data.
    Different video types should recommend different chart types.
    """
    video_type = video_type or {}
    cleaned = cleaned or []
    clusters = clusters or []
    
    vtype = video_type.get("primary", "其他")
    vtype_secondary = video_type.get("secondary", "")
    
    # Check data sufficiency
    comment_count = len(cleaned)
    cluster_count = len(clusters)
    has_enough_data = comment_count >= 10 and cluster_count >= 2
    
    # Default fallback
    fallback = "基础立场分布饼图 + 高赞评论列表"
    
    # Type-specific recommendations
    if vtype == "测评类" or vtype == "多商品对比类":
        # Heatmap is good for product × dimension comparison
        if has_enough_data:
            return {
                "chart_type": "heatmap",
                "reason": "适合展示商品/产品 × 评价维度的对比分析，直观呈现各商品优劣势",
                "fallback": fallback,
                "data_status": "ready",
            }
        else:
            return {
                "chart_type": "heatmap",
                "reason": "适合展示商品/产品 × 评价维度的对比分析",
                "fallback": fallback,
                "data_status": "insufficient",
            }
    
    elif vtype == "攻略类":
        # Guide videos: high-frequency questions, keywords, step suggestions
        if has_enough_data:
            return {
                "chart_type": "高频问题卡片 + 关键词云",
                "reason": "适合展示攻略中的常见问题和关键步骤，帮助观众快速定位所需信息",
                "fallback": "分步骤信息卡片 + 问题汇总",
                "data_status": "ready",
            }
        else:
            return {
                "chart_type": "高频问题卡片",
                "reason": "适合展示攻略中的常见问题",
                "fallback": "问题汇总列表",
                "data_status": "insufficient",
            }
    
    elif vtype == "科普类":
        # Science videos: knowledge focus, controversy points, corrections
        if has_enough_data:
            return {
                "chart_type": "知识点关注度 + 争议点列表",
                "reason": "适合展示科普内容的知识要点分布和观众讨论的争议焦点",
                "fallback": "知识点汇总 + 高赞评论",
                "data_status": "ready",
            }
        else:
            return {
                "chart_type": "知识点汇总",
                "reason": "适合展示科普内容的知识点",
                "fallback": "关键信息列表",
                "data_status": "insufficient",
            }
    
    elif vtype == "娱乐类":
        # Entertainment: sentiment distribution, hot memes, humor feedback
        if has_enough_data:
            return {
                "chart_type": "情绪分布 + 热梗词云",
                "reason": "适合展示娱乐内容的观众情绪反应和热门梗的传播情况",
                "fallback": "情绪分布饼图 + 热门评论",
                "data_status": "ready",
            }
        else:
            return {
                "chart_type": "情绪分布",
                "reason": "适合展示娱乐内容的观众情绪",
                "fallback": "情绪占比统计",
                "data_status": "insufficient",
            }
    
    elif vtype == "观点类":
        # Opinion videos: viewpoint clusters, stance distribution, controversy
        if has_enough_data:
            return {
                "chart_type": "观点聚类 + 立场分布",
                "reason": "适合展示不同观点的分布情况和观众立场的差异",
                "fallback": "观点汇总 + 支持/反对统计",
                "data_status": "ready",
            }
        else:
            return {
                "chart_type": "观点汇总",
                "reason": "适合展示评论中的主要观点",
                "fallback": "观点列表",
                "data_status": "insufficient",
            }
    
    elif vtype == "带货类":
        # E-commerce: purchase intent, concerns, trust issues
        if has_enough_data:
            # Check if multiple products mentioned
            product_mentions = _count_product_mentions(cleaned)
            if product_mentions >= 3:
                return {
                    "chart_type": "购买意向分析 + 疑虑点分布",
                    "reason": "适合展示带货商品的观众购买意向和主要疑虑",
                    "fallback": "购买意向统计 + 高赞评论",
                    "data_status": "ready",
                }
            else:
                return {
                    "chart_type": "购买意向分析",
                    "reason": "适合展示带货商品的观众购买意向和疑虑",
                    "fallback": "意向统计 + 疑虑汇总",
                    "data_status": "ready",
                }
        else:
            return {
                "chart_type": "购买意向统计",
                "reason": "适合展示带货商品的购买意向",
                "fallback": "意向分类汇总",
                "data_status": "insufficient",
            }
    
    elif vtype == "vlog类":
        # Vlog: emotional expression, interaction, engagement
        if has_enough_data:
            return {
                "chart_type": "情感互动分析 + 社区氛围图",
                "reason": "适合展示vlog内容的观众情感表达和社区互动氛围",
                "fallback": "情感分布 + 高互动评论",
                "data_status": "ready",
            }
        else:
            return {
                "chart_type": "情感分布",
                "reason": "适合展示vlog内容的观众情感",
                "fallback": "情感分类统计",
                "data_status": "insufficient",
            }
    
    else:
        # Default: use stance chart
        if has_enough_data:
            return {
                "chart_type": "立场分布 + 观点聚类",
                "reason": "通用推荐，适合展示评论的整体立场分布和主要观点",
                "fallback": "立场饼图 + 高赞评论",
                "data_status": "ready",
            }
        else:
            return {
                "chart_type": "立场分布",
                "reason": "基础可视化，展示评论的立场分布",
                "fallback": "立场统计",
                "data_status": "insufficient",
            }


def _count_product_mentions(comments: List[Dict[str, Any]]) -> int:
    """Count product-related mentions in comments."""
    import re
    product_keywords = [
        "买", "购买", "下单", "链接", "推荐", "种草", "值得", "性价比",
        "划算", "贵", "便宜", "折扣", "优惠", "入手", "商品", "产品"
    ]
    
    all_text = " ".join(c.get("text", "") for c in comments)
    
    count = 0
    for kw in product_keywords:
        if kw in all_text:
            count += 1
    
    return min(count, 10)  # Cap at 10


def build_report_local(raw_comments, cleaned, clean_stats, video_summary=None, video_type=None, cleaning_summary=None, content_comment_comparison=None, visualization_recommendation=None) -> str:
    main_n = sum(1 for c in cleaned if c.get("type") == "main")
    reply_n = sum(1 for c in cleaned if c.get("type") == "reply")
    top10 = top_liked(cleaned, 10)

    cat_map: Dict[str, List[Dict[str, Any]]] = {}
    for c in cleaned:
        cat = classify_local(c.get("text") or "")
        cat_map.setdefault(cat, []).append(c)

    out: List[str] = []
    out.append("# ViewLens 视频评论分析报告\n\n")

    # ── Video Type Section ──
    if video_type and video_type.get("primary"):
        out.append("## 视频类型判断\n")
        out.append(f"- 主类型: {video_type.get('primary', '')}\n")
        if video_type.get("secondary"):
            out.append(f"- 辅助类型: {video_type.get('secondary', '')}\n")
        out.append(f"- 置信度: {video_type.get('confidence', 0) * 100:.0f}%\n")
        out.append(f"- 判断理由: {video_type.get('reason', '')}\n")
        out.append("\n---\n\n")

    # ── Video Summary Section ──
    if video_summary:
        out.append("## 视频内容摘要\n")
        has_sub = video_summary.get("has_subtitle", False)
        out.append(f"- 字幕状态: {'有' if has_sub else '无'}\n")
        
        summary_text = video_summary.get("summary", "")
        if summary_text:
            out.append(f"\n### 内容摘要\n{summary_text}\n")
        
        key_points = video_summary.get("key_points", []) or []
        if key_points:
            out.append("\n### 关键内容\n")
            for i, pt in enumerate(key_points, 1):
                out.append(f"{i}. {pt}\n")
        
        accuracy = video_summary.get("accuracy_note", "")
        if accuracy:
            out.append(f"\n> 注：{accuracy}\n")
        out.append("\n---\n\n")

    # ── Cleaning Summary Section ──
    if cleaning_summary:
        out.append("## 数据清洗概览\n")
        out.append(f"- 原始评论数: {cleaning_summary.get('original_count', 0)}\n")
        out.append(f"- 清洗后评论数: {cleaning_summary.get('cleaned_count', 0)}\n")
        out.append(f"- 删除数量: {cleaning_summary.get('removed_count', 0)}\n")
        out.append(f"- 低信息密度: {cleaning_summary.get('low_info_count', 0)}\n")
        out.append(f"- 重复评论: {cleaning_summary.get('duplicate_count', 0)}\n")
        out.append(f"- 清洗策略: {cleaning_summary.get('strategy', '')}\n")
        out.append("\n---\n\n")

    # ── Content-Comment Comparison Section ──
    if content_comment_comparison:
        out.append("## 内容-评论对照分析\n")
        video_focus = content_comment_comparison.get("video_focus", []) or []
        if video_focus:
            out.append("- 视频关注点: " + "、".join(video_focus) + "\n")
        audience_focus = content_comment_comparison.get("audience_focus", []) or []
        if audience_focus:
            out.append("- 评论区关注点: " + "、".join(audience_focus) + "\n")
        gap = content_comment_comparison.get("gap_analysis", "")
        if gap:
            out.append(f"- 差异分析: {gap}\n")
        needs = content_comment_comparison.get("audience_needs", []) or []
        if needs:
            out.append("- 观众需求:\n")
            for n in needs[:5]:
                out.append(f"  - {n}\n")
        missed = content_comment_comparison.get("missed_topics", []) or []
        if missed:
            out.append("- 遗漏话题: " + "、".join(missed) + "\n")
        out.append("\n---\n\n")

    # ── Visualization Recommendation Section ──
    if visualization_recommendation:
        out.append("## 推荐可视化方式\n")
        chart_type = visualization_recommendation.get("chart_type", "")
        reason = visualization_recommendation.get("reason", "")
        data_status = visualization_recommendation.get("data_status", "insufficient")
        fallback = visualization_recommendation.get("fallback", "")
        out.append(f"- 推荐图表: {chart_type}\n")
        out.append(f"- 推荐理由: {reason}\n")
        out.append(f"- 数据状态: {'充足' if data_status == 'ready' else '不足'}\n")
        if fallback:
            out.append(f"- 降级方案: {fallback}\n")
        out.append("\n---\n\n")

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


def build_report_openai(raw_comments, cleaned, clean_stats, video_summary=None, video_type=None, cleaning_summary=None) -> str:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "stats": {
            "raw": len(raw_comments),
            "cleaned": len(cleaned),
            "removed": clean_stats.get("removed", {}),
            "main": sum(1 for c in cleaned if c.get("type") == "main"),
            "reply": sum(1 for c in cleaned if c.get("type") == "reply"),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "video_summary": video_summary or {},
        "video_type": video_type or {},
        "cleaning_summary": cleaning_summary or {},
        "top20": top_liked(cleaned, 20),
        "sample_comments": cleaned[:220],
    }
    
    # Add new sections
    video_type_section = ""
    if video_type and video_type.get("primary"):
        video_type_section = """
## 视频类型判断
- 主类型: %s
- 辅助类型: %s
- 置信度: %d%%
- 判断理由: %s
""" % (
            video_type.get('primary', ''),
            video_type.get('secondary', ''),
            int(video_type.get('confidence', 0) * 100),
            video_type.get('reason', '')
        )
    
    video_section = ""
    if video_summary:
        key_pts = ', '.join(video_summary.get('key_points', []) or [])
        video_section = """
## 视频内容摘要
- 字幕状态: %s
- 内容摘要: %s
- 关键内容: %s
- 准确性说明: %s
""" % (
            '有' if video_summary.get('has_subtitle') else '无',
            video_summary.get('summary', '无'),
            key_pts,
            video_summary.get('accuracy_note', '无')
        )
    
    cleaning_section = ""
    if cleaning_summary:
        cleaning_section = """
## 数据清洗概览
- 原始评论数: %d
- 清洗后评论数: %d
- 删除数量: %d
- 低信息密度: %d
- 重复评论: %d
- 清洗策略: %s
""" % (
            cleaning_summary.get('original_count', 0),
            cleaning_summary.get('cleaned_count', 0),
            cleaning_summary.get('removed_count', 0),
            cleaning_summary.get('low_info_count', 0),
            cleaning_summary.get('duplicate_count', 0),
            cleaning_summary.get('strategy', '')
        )
    
    sys_msg = "你是中文互联网评论区分析专家。请严格按用户指定的 report.md 结构输出，并尽量引用原文支撑结论。"
    user_msg = (
        "基于下面 JSON 数据生成报告，必须包含：\n"
        "# ViewLens 视频评论分析报告\n"
        + video_type_section + video_section + cleaning_section +
        "## 1. 数据概况（含 Top10）\n"
        "## 2. 分类评论（五类：支持/质疑/中立/调侃/提问；每类给数量、情绪、代表评论）\n"
        "## 3. 观点聚类（每类输出若干簇：标题、核心意思、代表评论原文、点赞权重大致影响力）\n"
        "## 4. 总结（主流共识、最大争议点、最关注问题、整体情绪倾向）\n\n"
        "数据如下（JSON）：\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    content = _llm_call(
        [{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
        model=model,
    )
    return content.strip() + "\n"


def build_report_openai(raw_comments, cleaned, clean_stats, video_summary=None, video_type=None, cleaning_summary=None, content_comment_comparison=None, visualization_recommendation=None) -> str:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "stats": {
            "raw": len(raw_comments),
            "cleaned": len(cleaned),
            "removed": clean_stats.get("removed", {}) if isinstance(clean_stats, dict) else {},
            "main": sum(1 for c in cleaned if c.get("type") == "main"),
            "reply": sum(1 for c in cleaned if c.get("type") == "reply"),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "video_summary": video_summary or {},
        "video_type": video_type or {},
        "cleaning_summary": cleaning_summary or {},
        "content_comment_comparison": content_comment_comparison or {},
        "visualization_recommendation": visualization_recommendation or {},
        "top20": top_liked(cleaned, 20),
        "sample_comments": cleaned[:220],
    }
    
    video_type_section = ""
    if video_type and video_type.get("primary"):
        video_type_section = """
## 视频类型判断
- 主类型: %s
- 辅助类型: %s
- 置信度: %d%%
- 判断理由: %s
""" % (
            video_type.get('primary', ''),
            video_type.get('secondary', ''),
            int(video_type.get('confidence', 0) * 100),
            video_type.get('reason', '')
        )
    
    video_section = ""
    if video_summary:
        key_pts = ', '.join(video_summary.get('key_points', []) or [])
        video_section = """
## 视频内容摘要
- 字幕状态: %s
- 内容摘要: %s
- 关键内容: %s
- 准确性说明: %s
""" % (
            '有' if video_summary.get('has_subtitle') else '无',
            video_summary.get('summary', '无'),
            key_pts,
            video_summary.get('accuracy_note', '无')
        )
    
    cleaning_section = ""
    if cleaning_summary:
        cleaning_section = """
## 数据清洗概览
- 原始评论数: %d
- 清洗后评论数: %d
- 删除数量: %d
- 低信息密度: %d
- 重复评论: %d
- 清洗策略: %s
""" % (
            cleaning_summary.get('original_count', 0),
            cleaning_summary.get('cleaned_count', 0),
            cleaning_summary.get('removed_count', 0),
            cleaning_summary.get('low_info_count', 0),
            cleaning_summary.get('duplicate_count', 0),
            cleaning_summary.get('strategy', '')
        )
    
    comparison_section = ""
    if content_comment_comparison:
        vf = ', '.join(content_comment_comparison.get('video_focus', []) or [])
        af = ', '.join(content_comment_comparison.get('audience_focus', []) or [])
        comparison_section = """
## 内容-评论对照分析
- 视频关注点: %s
- 评论区关注点: %s
- 差异分析: %s
- 观众需求: %s
- 遗漏话题: %s
""" % (
            vf or '无',
            af or '无',
            content_comment_comparison.get('gap_analysis', ''),
            ', '.join(content_comment_comparison.get('audience_needs', []) or []),
            ', '.join(content_comment_comparison.get('missed_topics', []) or [])
        )
    
    viz_section = ""
    if visualization_recommendation:
        viz_section = """
## 推荐可视化方式
- 推荐图表: %s
- 推荐理由: %s
- 数据状态: %s
- 降级方案: %s
""" % (
            visualization_recommendation.get('chart_type', ''),
            visualization_recommendation.get('reason', ''),
            '充足' if visualization_recommendation.get('data_status') == 'ready' else '不足',
            visualization_recommendation.get('fallback', '')
        )
    
    sys_msg = "你是中文互联网评论区分析专家。请严格按用户指定的 report.md 结构输出，并尽量引用原文支撑结论。"
    user_msg = (
        "基于下面 JSON 数据生成报告，必须包含：\n"
        "# ViewLens 视频评论分析报告\n"
        + video_type_section + video_section + cleaning_section + comparison_section + viz_section +
        "## 1. 数据概况（含 Top10）\n"
        "## 2. 分类评论（五类：支持/质疑/中立/调侃/提问；每类给数量、情绪、代表评论）\n"
        "## 3. 观点聚类（每类输出若干簇：标题、核心意思、代表评论原文、点赞权重大致影响力）\n"
        "## 4. 总结（主流共识、最大争议点，最关注问题、整体情绪倾向）\n\n"
        "数据如下（JSON）：\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    content = _llm_call(
        [{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}],
        model=model,
    )
    return content.strip() + "\n"


def build_report(raw_comments, cleaned, clean_stats, video_summary=None, video_type=None, cleaning_summary=None, content_comment_comparison=None, visualization_recommendation=None) -> str:
    if os.getenv("OPENAI_API_KEY"):
        try:
            return build_report_openai(raw_comments, cleaned, clean_stats, video_summary, video_type, cleaning_summary, content_comment_comparison, visualization_recommendation)
        except Exception:
            return build_report_local(raw_comments, cleaned, clean_stats, video_summary, video_type, cleaning_summary, content_comment_comparison, visualization_recommendation)
    return build_report_local(raw_comments, cleaned, clean_stats, video_summary, video_type, cleaning_summary, content_comment_comparison, visualization_recommendation)


# ──────────────────────────────────────────────────
# Heatmap Generation
# ──────────────────────────────────────────────────

# Common product detection patterns
PRODUCT_PATTERNS = {
    "手机": ["手机", "苹果", "iphone", "iPhone", "华为", "小米", "三星", "oppo", "vivo", "一加", "荣耀"],
    "电脑": ["电脑", "笔记本", "macbook", "MacBook", "联想", "戴尔", "惠普", "华硕", "thinkpad", "ThinkPad"],
    "平板": ["平板", "ipad", "iPad", "matepad", "MatePad", "平板"],
    "耳机": ["耳机", "airpods", "AirPods", "索尼", "森海塞尔", "bose", "Bose", "降噪耳机"],
    "相机": ["相机", "单反", "微单", "佳能", "尼康", "富士", "索尼"],
    "手表": ["手表", "apple watch", "Apple Watch", "华为手表", "小米手表", "智能手表"],
}

# Aspect/dimension detection patterns
ASPECT_PATTERNS = {
    "价格": ["价格", "性价比", "贵", "便宜", "划算", "值不值", "预算", "多少钱", "价位"],
    "性能": ["性能", "处理器", "cpu", "骁龙", "麒麟", "流畅", "卡顿", "跑分"],
    "续航": ["续航", "电池", "充电", "快充", "电量", "待机", "耗电"],
    "拍照": ["拍照", "摄影", "摄像头", "像素", "影像", "照片", "录像", "视频"],
    "屏幕": ["屏幕", "显示", "分辨率", "刷新率", "OLED", "LCD", "护眼"],
    "系统": ["系统", "iOS", "安卓", "鸿蒙", "流畅度", "生态"],
    "外观": ["外观", "颜值", "设计", "手感", "重量", "厚度", "做工"],
    "音质": ["音质", "音效", "声音", "扬声器", "外放", "听感"],
}

# Sentiment keywords
POSITIVE_WORDS = ["好", "棒", "强", "赞", "推荐", "值得", "优秀", "出色", "完美", "顶级", "满意", "喜欢", "牛", "强"]
NEGATIVE_WORDS = ["差", "烂", "坑", "不推荐", "垃圾", "失望", "后悔", "问题", "毛病", "翻车", "劝退", "辣鸡"]


def _detect_products(text: str) -> List[str]:
    """Detect mentioned products in text."""
    found = []
    text_lower = text.lower()
    for product, keywords in PRODUCT_PATTERNS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            found.append(product)
    return list(set(found))


def _detect_aspects(text: str) -> List[str]:
    """Detect mentioned aspects/dimensions in text."""
    found = []
    text_lower = text.lower()
    for aspect, keywords in ASPECT_PATTERNS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            found.append(aspect)
    return list(set(found))


def _detect_sentiment(text: str) -> str:
    """Detect overall sentiment of text."""
    pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)
    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    return "neutral"


def generate_heatmap_data(
    video_type: Dict[str, Any] = None,
    cleaned: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate heatmap data for product × aspect comparison.
    Only applicable for: 测评类, 多商品对比类, 带货类
    """
    video_type = video_type or {}
    cleaned = cleaned or []

    # Check video type eligibility
    vtype_primary = video_type.get("primary", "")
    vtype_secondary = video_type.get("secondary", "")
    eligible_types = {"测评类", "多商品对比类", "带货类", "多商品带货类"}

    is_eligible = (
        vtype_primary in eligible_types or
        vtype_secondary in eligible_types
    )

    if not is_eligible:
        return {
            "x_axis": [],
            "y_axis": [],
            "unit": "评论倾向值",
            "value_explanation": "当前视频类型不适用热力图分析。",
            "values": [],
            "data_status": "insufficient",
            "reason": "非测评/对比类视频，不生成热力图",
        }

    # Extract products and aspects from comments
    product_aspect_comments: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

    for comment in cleaned:
        text = comment.get("text", "") or ""
        if len(text) < 5:
            continue

        products = _detect_products(text)
        aspects = _detect_aspects(text)
        stance = comment.get("stance", "neutral")
        likes = int(comment.get("like") or 0)

        # For each product-aspect pair found in comment
        for prod in products:
            for asp in aspects:
                key = (prod, asp)
                if key not in product_aspect_comments:
                    product_aspect_comments[key] = []
                product_aspect_comments[key].append({
                    "text": text,
                    "stance": stance,
                    "likes": likes,
                })

    # Filter to products with at least 2 aspects mentioned
    products_with_aspects = {}
    for (prod, asp), comments in product_aspect_comments.items():
        if len(comments) >= 1:  # At least 1 comment for the pair
            if prod not in products_with_aspects:
                products_with_aspects[prod] = {"aspects": set(), "pairs": {}}
            products_with_aspects[prod]["aspects"].add(asp)
            products_with_aspects[prod]["pairs"][asp] = comments

    # Check minimum requirements
    valid_products = [
        p for p, data in products_with_aspects.items()
        if len(data["aspects"]) >= 2
    ]

    all_aspects = set()
    for prod_data in products_with_aspects.values():
        all_aspects.update(prod_data["aspects"])

    if len(valid_products) < 2 or len(all_aspects) < 2:
        return {
            "x_axis": [],
            "y_axis": [],
            "unit": "评论倾向值",
            "value_explanation": "该数值基于评论数量、语义相关性和情绪倾向估算，仅代表评论区反馈，不代表客观评分。",
            "values": [],
            "data_status": "insufficient",
            "reason": f"检测到 {len(valid_products)} 个商品和 {len(all_aspects)} 个维度，需要至少 2 个商品和 2 个维度",
        }

    # Build heatmap data
    x_axis = sorted(list(all_aspects))[:6]  # Max 6 aspects
    y_axis = valid_products[:5]  # Max 5 products
    values = []

    for prod in y_axis:
        pairs_data = products_with_aspects[prod]["pairs"]
        for asp in x_axis:
            comments = pairs_data.get(asp, [])
            count = len(comments)
            value = 0.0
            sentiment = "neutral"

            if count > 0:
                # Calculate sentiment distribution
                pos = sum(1 for c in comments if c["stance"] in ["support", "positive"] or _detect_sentiment(c["text"]) == "positive")
                neg = sum(1 for c in comments if c["stance"] in ["oppose", "negative"] or _detect_sentiment(c["text"]) == "negative")
                total = pos + neg if (pos + neg) > 0 else count

                # Calculate heat value (0-100)
                if total > 0:
                    sentiment_ratio = (pos - neg) / total
                    base_value = 50 + sentiment_ratio * 40  # Range 10-90
                    # Add confidence based on count
                    count_factor = min(count / 10, 1.0) * 10
                    value = min(100, max(0, base_value + count_factor))
                else:
                    value = 50  # Neutral baseline

                # Determine sentiment
                if pos > neg:
                    sentiment = "positive"
                elif neg > pos:
                    sentiment = "negative"
                else:
                    sentiment = "neutral"

                # Get examples (top 2 by likes)
                sorted_comments = sorted(comments, key=lambda x: x["likes"], reverse=True)
                examples = [c["text"][:100] for c in sorted_comments[:2]]
            else:
                examples = []
                value = 0
                sentiment = "neutral"

            values.append({
                "product": prod,
                "aspect": asp,
                "value": round(value, 1),
                "sentiment": sentiment,
                "count": count,
                "examples": examples,
            })

    return {
        "x_axis": x_axis,
        "y_axis": y_axis,
        "unit": "评论倾向值",
        "value_explanation": "该数值基于评论数量、语义相关性和情绪倾向估算，仅代表评论区反馈，不代表客观评分。",
        "values": values,
        "data_status": "ready",
        "reason": "",
    }


