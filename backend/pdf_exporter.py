from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def _sanitize_filename(name: str, max_len: int = 120) -> str:
    """Convert to ASCII-safe filename, preserving readability."""
    # Replace colons and other problematic chars
    name = re.sub(r"[\\/:*?\"<>|\n\r\t]+", "_", name)
    name = re.sub(r"\s+", "_", name).strip()
    if not name:
        return "report"
    return name[:max_len]


def _desktop_dir() -> Optional[str]:
    home = os.path.expanduser("~")
    if not home:
        return None
    desktop = os.path.join(home, "Desktop")
    if os.path.isdir(desktop):
        return desktop
    return None


def _exports_base(project_backend_dir: str) -> str:
    base = _desktop_dir()
    if base:
        return os.path.join(base, "Comment_Intelligence_Reports")
    project_root = os.path.abspath(os.path.join(project_backend_dir, os.pardir, os.pardir))
    return os.path.join(project_root, "exports", "Comment_Intelligence_Reports")


def _try_register_cjk_font() -> Optional[str]:
    """Try to register a CJK-capable font from common system paths.
    Returns the registered font name on success, None on complete failure.
    TTF files are preferred over TTC for better ToUnicode CMap embedding.
    """
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # (path, font_name, face_index) — face_index only for TTC files
        # TTF first (better font embedding), then TTC
        candidates: List[Tuple[str, str, int]] = [
            # ── Linux / Render ──
            ("/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf", "CIS_NotoSansSC", 0),
            ("/usr/share/fonts/truetype/noto/NotoSansSC-Regular.ttf", "CIS_NotoSansSC", 0),
            ("/usr/share/fonts/opentype/noto/NotoSerifSC-Regular.otf", "CIS_NotoSerifSC", 0),
            ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "CIS_NotoSansCJK", 0),
            ("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "CIS_DroidSans", 0),
            # ── Windows TTF (preferred) ──
            (r"C:\Windows\Fonts\simhei.ttf", "CIS_SimHei", 0),
            (r"C:\Windows\Fonts\simkai.ttf", "CIS_SimKai", 0),
            (r"C:\Windows\Fonts\STKAITI.TTF", "CIS_STKaiti", 0),
            (r"C:\Windows\Fonts\STZHONGS.TTF", "CIS_ZhongSong", 0),
            # ── Windows TTC (fallback) ──
            (r"C:\Windows\Fonts\msyh.ttc", "CIS_MSYaHei", 0),
            (r"C:\Windows\Fonts\msyh.ttc", "CIS_MSYaHei_Bold", 1),
            (r"C:\Windows\Fonts\simsun.ttc", "CIS_SimSun", 0),
            (r"C:\Windows\Fonts\mingliub.ttc", "CIS_MingLiu", 0),
            # ── macOS ──
            ("/System/Library/Fonts/STHeiti Light.ttc", "CIS_STHeiti", 0),
            ("/System/Library/Fonts/Hiragino Sans GB.ttc", "CIS_Hiragino", 0),
            ("/Library/Fonts/Arial Unicode.ttf", "CIS_ArialUnicode", 0),
        ]

        for path, font_name, face_idx in candidates:
            if not os.path.exists(path):
                continue
            try:
                pdfmetrics.registerFont(TTFont(font_name, path, face_idx))
                return font_name
            except Exception:
                continue
    except Exception:
        pass
    return None


def export_pdf(
    *,
    backend_dir: str,
    platform: str,
    video_id: str,
    stance_stats: Dict[str, int],
    top_influence_comments: List[Dict[str, Any]],
    clusters: List[Dict[str, Any]],
    controversies: List[Dict[str, Any]],
    summary_lines: List[str],
) -> str:
    """
    Generate PDF report. Must never raise in caller; caller should wrap try/except.
    Returns absolute pdf path on success.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib import colors

    # Register CJK font once; idempotent (reportlab ignores duplicate registrations)
    _CJK_FONT_NAME = _try_register_cjk_font()
    _ASCII_FONT = "Helvetica"  # reportlab built-in; safe for English labels

    base = _exports_base(backend_dir)
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(base, date_str)
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    # Use ASCII-safe filename to avoid encoding issues on non-UTF-8 systems
    filename = _sanitize_filename(f"{platform}_{video_id}_report_{ts}.pdf")
    pdf_path = os.path.join(out_dir, filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Comment Analysis Report",
    )

    styles = getSampleStyleSheet()

    # Use CJK font for all text so that Chinese characters display correctly;
    # fall back to Helvetica only when no CJK font is available.
    body_font = _CJK_FONT_NAME or _ASCII_FONT

    def _style(name: str, base_key: str, **kwargs) -> ParagraphStyle:
        base_s = styles[base_key]
        defaults = dict(fontName=body_font, textColor=colors.black, leading=14)
        defaults.update(kwargs)
        return ParagraphStyle(name, parent=base_s, **defaults)

    title_s  = _style("CIS_Title", "Title", fontSize=16, spaceAfter=10)
    h_s      = _style("CIS_H",     "Heading2", fontSize=12, spaceBefore=10, spaceAfter=6)
    body_s   = _style("CIS_P",     "Normal",   fontSize=10, leading=14)

    story: List[Any] = []

    # ── Header ──
    story.append(Paragraph("Comment Intelligence Report / 评论分析报告", title_s))
    story.append(Paragraph(f"Platform: {platform}   Video ID: {video_id}", body_s))
    story.append(Spacer(1, 8))

    # ── Stance Stats ──
    story.append(Paragraph("Stance Distribution / 立场分布", h_s))
    stance_rows = [
        ["support / 支持", stance_stats.get("support", 0),
         "oppose / 反对", stance_stats.get("oppose", 0)],
        ["neutral / 中立", stance_stats.get("neutral", 0),
         "joke / 玩梗", stance_stats.get("joke", 0)],
        ["question / 提问", stance_stats.get("question", 0), "", ""],
    ]
    tbl = Table(stance_rows, colWidths=[44 * mm, 22 * mm, 44 * mm, 22 * mm])
    tbl.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONT", (0, 0), (-1, -1), body_font),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ])
    )
    story.append(tbl)
    story.append(Spacer(1, 6))

    # ── Top Influence Comments ──
    story.append(Paragraph("Top Influence Comments / 高影响评论 Top 10", h_s))
    if not top_influence_comments:
        story.append(Paragraph("(No data available)", body_s))
    else:
        for i, c in enumerate(top_influence_comments[:10], 1):
            user   = c.get("user", "")
            txt    = (c.get("text") or "").replace("\n", " ")
            zh     = (c.get("translation_zh") or "").replace("\n", " ")
            like   = c.get("like", 0)
            reply  = c.get("reply_count", 0)
            inf    = c.get("influence_score", 0)

            story.append(Paragraph(
                f"{i}. {user}  likes={like}  replies={reply}  influence={inf:.3f}", body_s))
            story.append(Paragraph(txt, body_s))
            if zh:
                story.append(Paragraph(f"  Translation / 译文: {zh}", body_s))
            story.append(Spacer(1, 4))

    # ── Topic Clusters ──
    story.append(Paragraph("Topic Clusters / 观点聚类（摘要）", h_s))
    if not clusters:
        story.append(Paragraph("(No data available)", body_s))
    else:
        for cl in clusters[:8]:
            title   = cl.get("title", "")
            kw      = cl.get("keywords", [])
            count   = cl.get("count", 0)
            lk_w    = cl.get("like_weight", 0)
            reps    = (cl.get("representative_comments") or [])[:3]

            story.append(Paragraph(f"- Theme / 主题: {title}", body_s))
            if kw:
                story.append(Paragraph(f"  Keywords / 关键词: {' / '.join(kw[:5])}", body_s))
            story.append(Paragraph(f"  Count / 评论数: {count}   Like weight / 点赞权重: {lk_w}", body_s))
            for rep in reps:
                story.append(Paragraph(
                    f"    . ({rep.get('like', 0)} likes) {rep.get('text', '')[:80]}", body_s))

    # ── Controversies ──
    story.append(Paragraph("Controversies / 争议点", h_s))
    if not controversies:
        story.append(Paragraph("No significant controversies detected / 暂无明显争议点", body_s))
    else:
        for co in controversies[:5]:
            story.append(Paragraph(f"- {co.get('title', '')}", body_s))
            desc = co.get("description", "")
            if desc:
                story.append(Paragraph(f"  {desc}", body_s))
            for s in (co.get("sample_comments") or [])[:2]:
                story.append(Paragraph(f"    . {str(s)[:80]}", body_s))

    # ── Summary ──
    story.append(Paragraph("Summary / 总结", h_s))
    if not summary_lines:
        story.append(Paragraph("(No summary available)", body_s))
    else:
        for line in summary_lines[:10]:
            story.append(Paragraph(f"- {line}", body_s))

    doc.build(story)
    return pdf_path
