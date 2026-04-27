from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


def _sanitize_filename(name: str, max_len: int = 120) -> str:
    name = re.sub(r"[\\/:*?\"<>|\n\r\t]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
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
    # If Desktop missing, fallback to project exports/
    base = _desktop_dir()
    if base:
        return os.path.join(base, "Comment_Intelligence_Reports")
    # backend/ -> project root -> exports
    project_root = os.path.abspath(os.path.join(project_backend_dir, os.pardir, os.pardir))
    return os.path.join(project_root, "exports", "Comment_Intelligence_Reports")


def _try_register_cjk_font() -> None:
    # Best-effort: register one available CJK font, but never fail.
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        candidates = [
            # Windows
            r"C:\Windows\Fonts\msyh.ttc",  # Microsoft YaHei
            r"C:\Windows\Fonts\msyh.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\simsun.ttf",
            # macOS typical (not available on Windows but safe)
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/PingFang SC.ttc",
            # Linux common
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ]
        for p in candidates:
            if os.path.exists(p):
                pdfmetrics.registerFont(TTFont("CIS_CJK", p))
                return
    except Exception:
        return


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

    _try_register_cjk_font()

    base = _exports_base(backend_dir)
    date_folder = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(base, date_folder)
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = _sanitize_filename(f"{platform}_{video_id}_评论分析报告_{ts}.pdf")
    pdf_path = os.path.join(out_dir, filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Comment Intelligence Report",
    )

    styles = getSampleStyleSheet()
    base_font = styles["Normal"].fontName
    use_cjk = False
    try:
        # If registered, it will be usable by name.
        from reportlab.pdfbase import pdfmetrics

        pdfmetrics.getFont("CIS_CJK")
        use_cjk = True
    except Exception:
        use_cjk = False

    title_style = ParagraphStyle(
        "CIS_Title",
        parent=styles["Title"],
        fontName="CIS_CJK" if use_cjk else styles["Title"].fontName,
        textColor=colors.black,
        spaceAfter=10,
    )
    h_style = ParagraphStyle(
        "CIS_H",
        parent=styles["Heading2"],
        fontName="CIS_CJK" if use_cjk else styles["Heading2"].fontName,
        textColor=colors.black,
        spaceBefore=10,
        spaceAfter=6,
    )
    p_style = ParagraphStyle(
        "CIS_P",
        parent=styles["BodyText"],
        fontName="CIS_CJK" if use_cjk else styles["BodyText"].fontName,
        leading=14,
    )

    story: List[Any] = []
    story.append(Paragraph("评论区分析报告", title_style))
    story.append(Paragraph(f"平台：{platform}　视频ID：{video_id}", p_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("数据概况", h_style))
    stance_table = [
        ["support", stance_stats.get("support", 0), "oppose", stance_stats.get("oppose", 0)],
        ["neutral", stance_stats.get("neutral", 0), "joke", stance_stats.get("joke", 0)],
        ["question", stance_stats.get("question", 0), "", ""],
    ]
    tbl = Table(stance_table, colWidths=[40 * mm, 25 * mm, 40 * mm, 25 * mm])
    tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONT", (0, 0), (-1, -1), "CIS_CJK" if use_cjk else base_font),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(Paragraph("立场分布", p_style))
    story.append(tbl)

    story.append(Paragraph("高影响评论 Top 10", h_style))
    if not top_influence_comments:
        story.append(Paragraph("（暂无）", p_style))
    else:
        for i, c in enumerate(top_influence_comments[:10], 1):
            txt = (c.get("text") or "").replace("\n", " ")
            zh = (c.get("translation_zh") or "").replace("\n", " ")
            meta = f"{i}. {c.get('user','')}  👍{c.get('like',0)}  💬{c.get('reply_count',0)}  influence={c.get('influence_score',0):.3f}"
            story.append(Paragraph(meta, p_style))
            story.append(Paragraph(txt, p_style))
            if zh:
                story.append(Paragraph(f"译文：{zh}", p_style))
            story.append(Spacer(1, 6))

    story.append(Paragraph("观点聚类（摘要）", h_style))
    if not clusters:
        story.append(Paragraph("（暂无）", p_style))
    else:
        for cl in clusters[:8]:
            title = cl.get("title", "")
            keywords = cl.get("keywords", [])
            count = cl.get("count", 0)
            like_weight = cl.get("like_weight", 0)
            reps = cl.get("representative_comments", [])[:3]
            story.append(Paragraph(f"- 主题：{title}", p_style))
            if keywords:
                story.append(Paragraph(f"  关键词：{' / '.join(keywords[:5])}", p_style))
            story.append(Paragraph(f"  评论数：{count}　点赞权重：{like_weight}", p_style))
            for rep in reps:
                rep_text = rep.get("text", "")
                rep_likes = rep.get("like", 0)
                story.append(Paragraph(f"    · ({rep_likes}赞) {rep_text[:80]}", p_style))

    story.append(Paragraph("争议点", h_style))
    if not controversies:
        story.append(Paragraph("暂无明显争议点", p_style))
    else:
        for co in controversies[:5]:
            story.append(Paragraph(f"- {co.get('title', '')}", p_style))
            desc = co.get("description", "")
            if desc:
                story.append(Paragraph(f"  {desc}", p_style))
            samples = co.get("sample_comments", [])
            for s in samples[:2]:
                story.append(Paragraph(f"    · {str(s)[:80]}", p_style))

    story.append(Paragraph("总结", h_style))
    if not summary_lines:
        story.append(Paragraph("（暂无）", p_style))
    else:
        for line in summary_lines[:10]:
            story.append(Paragraph(f"- {line}", p_style))

    doc.build(story)
    return pdf_path

