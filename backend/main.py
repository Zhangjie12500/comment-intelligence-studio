from __future__ import annotations

import asyncio
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

import json
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from dotenv import load_dotenv

# Load .env: root takes priority, backend/.env is fallback
_BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BASE_DIR / ".env")
load_dotenv(_BASE_DIR / "backend" / ".env", override=False)

# Startup diagnostics (no secrets exposed)
_yt_key_loaded = bool(os.getenv("YOUTUBE_API_KEY"))
_openai_key_loaded = bool(os.getenv("OPENAI_API_KEY"))
print(f"[startup] YouTube API Key loaded: {'yes' if _yt_key_loaded else 'no'}")
print(f"[startup] OpenAI API Key loaded: {'yes' if _openai_key_loaded else 'no'}")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.analyzer import (
    build_report,
    build_cleaning_summary,
    clean_and_merge,
    clean_and_merge_v2,
    classify_video_type,
    compute_stance_stats,
    compute_top_influence,
    compute_clusters,
    compute_controversies,
    compute_summary,
    compute_summary_ai,
    compute_summary_ai_with_status,
    compute_opinion_clusters_ai_with_status,
    generate_video_summary,
    generate_content_comment_comparison,
    generate_visualization_recommendation,
    generate_heatmap_data,
    fetch_youtube_subtitles,
    fetch_bilibili_subtitles,
)
from backend.cache import read_cache, write_cache
from backend.pdf_exporter import export_pdf
from backend.schemas import FilesInfo, JobCreateRequest, JobCreateResponse, JobStatusResponse, OpinionClusters, Platform, TaskInfo, TaskStatus, VideoSummary, VideoType, CleaningSummary, ContentCommentComparison, VisualizationRecommendation, HeatmapData, HeatmapValue
from backend.scrapers import bilibili, youtube
from backend.utils import dump_json, dump_text, now_local_str, random_id, safe_slug


APP_TITLE = "Comment Intelligence Studio API"
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")

def _job_dir(job_id: str) -> str:
    return os.path.join(STORAGE_DIR, job_id)


def _job_state_path(job_id: str) -> str:
    return os.path.join(_job_dir(job_id), "job_state.json")


def _atomic_write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def persist_job(job: JobState) -> None:
    failed_tasks = [s for s in job.tasks.values() if s.task.status == TaskStatus.failed]
    if failed_tasks:
        overall_status = "failed"
        # Collect distinct errors (use friendly messages)
        errors = list({_map_error_to_user_message(s.task.error) for s in failed_tasks if s.task.error})
        overall_error = "; ".join(errors) if errors else "部分任务失败"
    elif all(s.task.status == TaskStatus.done for s in job.tasks.values()):
        overall_status = "done"
        overall_error = ""
    else:
        overall_status = "running"
        overall_error = ""
    payload = {
        "job_id": job.job_id,
        "status": overall_status,
        "error": overall_error,
        "force_refresh": bool(getattr(job, "force_refresh", False)),
        "include_replies": bool(getattr(job, "include_replies", True)),
        "created_at": min(s.task.created_at for s in job.tasks.values()),
        "updated_at": max(s.task.updated_at for s in job.tasks.values()),
        "tasks": [],
    }
    for task_id, state in job.tasks.items():
        t = state.task
        payload["tasks"].append(
            {
                "task": t.model_dump(),
                "paths": {
                    "comments_path": state.comments_path or "",
                    "report_path": state.report_path or "",
                    "pdf_path": state.pdf_path or "",
                },
            }
        )
    _atomic_write_json(_job_state_path(job.job_id), payload)


def load_job_from_disk(job_id: str) -> Optional[JobState]:
    p = _job_state_path(job_id)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f)
        job = JobState(job_id)
        job.force_refresh = bool(j.get("force_refresh", False))
        job.include_replies = bool(j.get("include_replies", True))
        for item in (j.get("tasks") or []):
            t_raw = (item.get("task") or {})
            t = TaskInfo(**t_raw)
            # If server restarted during run, mark as failed (no resume).
            if t.status in {TaskStatus.pending, TaskStatus.fetching, TaskStatus.analyzing, TaskStatus.exporting}:
                t.status = TaskStatus.failed
                t.error = "服务重启/热重载导致任务中断，请重新提交该链接"
                t.updated_at = now_local_str()
                t.warnings = list(t.warnings or [])
                t.warnings.append("任务状态已从磁盘恢复，但进行中的抓取不会自动续跑。")
            state = TaskState(t)
            paths = item.get("paths") or {}
            state.comments_path = paths.get("comments_path") or None
            state.report_path = paths.get("report_path") or None
            state.pdf_path = paths.get("pdf_path") or None
            job.tasks[t.task_id] = state
        return job
    except Exception:
        return None


def detect_platform(url: str) -> Platform:
    from urllib.parse import urlparse

    host = (urlparse(url).netloc or "").lower().split(":")[0]
    if host.endswith("bilibili.com") or host.endswith("b23.tv"):
        return Platform.bilibili
    if host.endswith("youtube.com") or host.endswith("youtu.be"):
        return Platform.youtube
    raise ValueError("无法识别平台：仅支持 bilibili.com/b23.tv 与 youtube.com/youtu.be 的视频链接")


class TaskState:
    def __init__(self, task: TaskInfo):
        self.task = task
        self.comments_path: Optional[str] = None
        self.report_path: Optional[str] = None
        self.pdf_path: Optional[str] = None
        self.raw_comments: List[Dict[str, Any]] = []
        self.cleaned_comments: List[Dict[str, Any]] = []


class JobState:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.tasks: Dict[str, TaskState] = {}
        self.force_refresh: bool = False
        self.include_replies: bool = True


jobs: Dict[str, JobState] = {}
fetch_semaphore = asyncio.Semaphore(3)
executor = ThreadPoolExecutor(max_workers=6)


# Error message mapping for user-friendly display
ERROR_MESSAGE_MAP = {
    # YouTube specific
    "removed": "部分评论已被删除或不可用，系统已自动跳过",
    "deleted": "部分评论已被删除或不可用，系统已自动跳过",
    "unavailable": "部分评论已不可用，系统已自动跳过",
    "[已删除]": "部分评论已被删除，系统已自动跳过",
    "[removed]": "部分评论已被删除，系统已自动跳过",
    "[deleted]": "部分评论已被删除，系统已自动跳过",
    "评论已删除": "部分评论已被删除，系统已自动跳过",
    
    # Network/Connection errors
    "ConnectionError": "无法连接到视频平台，请检查网络连接",
    "Timeout": "请求超时，请稍后重试",
    "timed out": "请求超时，请稍后重试",
    
    # API errors
    "quotaExceeded": "YouTube API 配额已用尽，请明天再试或配置更多配额",
    "API 配额耗尽": "YouTube API 配额已用尽，请明天再试或配置更多配额",
    "commentsDisabled": "该视频已关闭评论区",
    "评论区关闭": "该视频已关闭评论区",
    "videoNotFound": "视频不存在或已被删除",
    "视频不可用/已删除": "视频不存在或已被删除",
    "private": "视频为私密视频，无法访问",
    "forbidden": "无权访问该视频内容",
    "视频为私密/无权限访问": "视频为私密视频或无权访问",
    
    # General errors
    "缺少环境变量 YOUTUBE_API_KEY": "未配置 YouTube API 密钥，请联系管理员",
    "缺少 OPENAI_API_KEY": "未配置 OpenAI API 密钥，无法生成 AI 分析",
    "URL 解析失败": "无法识别视频链接格式，请检查链接是否正确",
}


def _map_error_to_user_message(raw_error: str) -> str:
    """
    Map raw error messages to user-friendly Chinese messages.
    """
    if not raw_error:
        return "发生未知错误，请稍后重试"
    
    # Direct match
    if raw_error in ERROR_MESSAGE_MAP:
        return ERROR_MESSAGE_MAP[raw_error]
    
    # Partial match for common error patterns
    raw_lower = raw_error.lower()
    for pattern, friendly_msg in ERROR_MESSAGE_MAP.items():
        if pattern.lower() in raw_lower:
            return friendly_msg
    
    # Return original if no mapping found
    return raw_error


# Allowlist origins for CORS. Set CORS_ORIGINS env var (comma-separated) in production.
# Example: CORS_ORIGINS=https://your-app.vercel.app,https://your-app-git-branch.vercel.app
# If set to "*", all origins are allowed.
# If not set, defaults to localhost dev origins only.
# credentials is always False — this API has no session/auth, credentials not needed.
_cors_raw = os.getenv("CORS_ORIGINS", "").strip()

if _cors_raw == "*":
    _cors_origins = ["*"]
elif _cors_raw:
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
else:
    _cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app = FastAPI(title=APP_TITLE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup diagnostics ─────────────────────────────────────────────
_log_cors = os.getenv("CORS_ORIGINS", "").strip()
print(f"[CIS] CORS_ORIGINS env      = {repr(_log_cors)}")
print(f"[CIS] Final allow_origins   = {_cors_origins}")
print(f"[CIS] allow_credentials      = False")
print(f"[CIS] allow_methods/headers = *")
print(f"[CIS] App ready at http://0.0.0.0:8010")


def _task_dir(job_id: str, task_id: str) -> str:
    return os.path.join(STORAGE_DIR, job_id, task_id)


async def run_task(job_id: str, task_id: str) -> None:
    job = jobs.get(job_id)
    if not job or task_id not in job.tasks:
        return
    state = job.tasks[task_id]
    t = state.task

    def set_status(status: TaskStatus, *, err: str = "") -> None:
        t.status = status
        t.error = err
        t.updated_at = now_local_str()
        try:
            persist_job(job)
        except Exception:
            pass

    try:
        job_force_refresh = getattr(job, "force_refresh", False)
        job_include_replies = getattr(job, "include_replies", True)

        # Cache check (global cache/; storage/ is per-task export)
        if not job_force_refresh and t.platform and t.video_id:
            cached = read_cache(t.platform.value, t.video_id, t.limit, job_include_replies)
        else:
            cached = None

        if cached:
            state.raw_comments = list(cached.get("comments") or [])
            t.source = "cache"
            t.raw_count = len(state.raw_comments)
            try:
                persist_job(job)
            except Exception:
                pass
        else:
            # Fetching (with global semaphore to avoid rate-limit)
            set_status(TaskStatus.fetching)
            async with fetch_semaphore:
                loop = asyncio.get_running_loop()
                if t.platform == Platform.bilibili:
                    raw = await loop.run_in_executor(executor, bilibili.fetch_comments, t.url, t.limit, job_include_replies)
                else:
                    raw = await loop.run_in_executor(executor, youtube.fetch_comments, t.url, t.limit)
            state.raw_comments = raw or []
            t.raw_count = len(state.raw_comments)
            t.source = "fresh"
            try:
                persist_job(job)
            except Exception:
                pass
            # write cache (best-effort)
            try:
                write_cache(
                    url=t.url,
                    platform=t.platform.value if t.platform else "",
                    video_id=t.video_id or "",
                    limit=t.limit,
                    include_replies=job_include_replies,
                    comments=state.raw_comments,
                )
            except Exception as e:
                t.warnings.append(f"缓存写入失败（已降级忽略）：{str(e) or e.__class__.__name__}")

        # Analyze
        set_status(TaskStatus.analyzing)
        
        # First, classify video type (needed for adaptive cleaning)
        video_type_result = await asyncio.get_running_loop().run_in_executor(
            executor, classify_video_type, "", "", "", state.raw_comments[:20]
        )
        video_type_str = video_type_result.get("primary", "其他")
        
        # Use adaptive cleaning based on video type
        cleaned, clean_stats = await asyncio.get_running_loop().run_in_executor(
            executor, clean_and_merge_v2, state.raw_comments, video_type_str
        )
        state.cleaned_comments = cleaned or []
        t.cleaned_count = len(state.cleaned_comments)
        t.main_count = sum(1 for c in state.cleaned_comments if c.get("type") == "main")
        t.reply_count = sum(1 for c in state.cleaned_comments if c.get("type") == "reply")
        
        # Track removed comments info for user
        removed_details = clean_stats.get("details", {})
        removed_count = removed_details.get("removed_comments", 0)
        parse_errors = clean_stats.get("parse_errors", 0)
        fallback_used = clean_stats.get("fallback_used", False)
        kept_minimum = removed_details.get("kept_minimum", 0)
        
        if fallback_used:
            t.warnings.append(f"评论过滤较严格，已使用原始数据进行补足（保留 {kept_minimum} 条）。")
        elif removed_count > 0 or parse_errors > 0:
            parts = []
            if removed_count > 0:
                parts.append(f"已跳过 {removed_count} 条被删除/不可用的评论")
            if parse_errors > 0:
                parts.append(f"解析异常 {parse_errors} 条")
            t.warnings.append("; ".join(parts) + "。")
        
        # IMPORTANT: Task should NOT fail if we have raw comments
        # Only fail if fetch completely failed (raw_count == 0)
        # With the improved cleaning, we now always return at least some comments

        # Run all local analysis and write results back to the task fields
        stance_stats = await asyncio.get_running_loop().run_in_executor(executor, compute_stance_stats, state.cleaned_comments)
        top_influence = await asyncio.get_running_loop().run_in_executor(executor, compute_top_influence, state.cleaned_comments, 10)
        clusters = await asyncio.get_running_loop().run_in_executor(executor, compute_clusters, state.cleaned_comments)
        controversies = await asyncio.get_running_loop().run_in_executor(executor, compute_controversies, stance_stats, top_influence)
        platform_val = t.platform.value if t.platform else ""

        # Get AI model
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Try AI summary first, fallback to rule-based
        if os.getenv("OPENAI_API_KEY"):
            summary, ai_status = await asyncio.get_running_loop().run_in_executor(
                executor, compute_summary_ai_with_status, stance_stats, clusters, t.cleaned_count, t.raw_count or 0, platform_val, model
            )
        else:
            summary = await asyncio.get_running_loop().run_in_executor(
                executor, compute_summary, stance_stats, clusters, t.cleaned_count, t.raw_count or 0, platform_val
            )
            ai_status = {
                "enabled": False,
                "model": model,
                "message": "AI总结不可用，已使用规则分析结果。",
                "error": "OPENAI_API_KEY 未配置"
            }

        t.stance_stats = stance_stats
        t.top_influence_comments = top_influence
        t.clusters = clusters
        t.controversies = controversies
        t.summary = summary
        t.ai_status = ai_status

        # ── AI Opinion Clusters (新功能) ──
        try:
            if os.getenv("OPENAI_API_KEY"):
                opinion_result, opinion_ai_status = await asyncio.get_running_loop().run_in_executor(
                    executor, compute_opinion_clusters_ai_with_status, state.cleaned_comments, clusters
                )
                # 合并 ai_status
                t.ai_status["opinion_clusters_enabled"] = opinion_ai_status.get("enabled", False)
                t.opinion_clusters = OpinionClusters(**opinion_result)
            else:
                # 使用规则聚类结果
                t.opinion_clusters = OpinionClusters(opinion_clusters=[
                    {"summary": c.get("summary", ""), "sentiment": c.get("sentiment", "neutral"),
                     "ratio": c.get("ratio", 0), "examples": c.get("examples", [])[:2]}
                    for c in clusters[:5]
                ])
        except Exception as e:
            t.warnings.append(f"观点聚类生成失败（已降级忽略）：{str(e)}")
            t.opinion_clusters = OpinionClusters(opinion_clusters=[
                {"summary": c.get("summary", ""), "sentiment": c.get("sentiment", "neutral"),
                 "ratio": c.get("ratio", 0), "examples": c.get("examples", [])[:2]}
                for c in clusters[:5]
            ])

        # Video Type
        t.video_type = VideoType(**video_type_result)
        
        # Cleaning Summary
        cleaning_summary_result = await asyncio.get_running_loop().run_in_executor(
            executor, build_cleaning_summary, clean_stats, video_type_str
        )
        t.cleaning_summary = CleaningSummary(**cleaning_summary_result)

        # ── Video Summary (subtitle + AI) ──
        try:
            video_id = t.video_id or ""
            subtitle_text = ""
            has_subtitle = False
            
            # Fetch subtitles based on platform
            if t.platform == Platform.bilibili and video_id:
                has_subtitle, subtitle_text = await asyncio.get_running_loop().run_in_executor(
                    executor, fetch_bilibili_subtitles, video_id
                )
            elif t.platform == Platform.youtube and video_id:
                has_subtitle, subtitle_text = await asyncio.get_running_loop().run_in_executor(
                    executor, fetch_youtube_subtitles, video_id
                )
            
            # Generate video summary
            video_summary = await asyncio.get_running_loop().run_in_executor(
                executor, 
                generate_video_summary,
                subtitle_text,
                "",  # video_title
                "",  # video_desc
                top_influence[:20],
                platform_val
            )
            
            t.video_summary = VideoSummary(**video_summary)
            t.warnings.append(f"字幕检测: {'有' if has_subtitle else '无'}")
        except Exception as e:
            t.warnings.append(f"视频摘要生成失败（已降级忽略）：{str(e)}")
            t.video_summary = VideoSummary(
                has_subtitle=False,
                summary="视频摘要生成失败",
                key_points=[],
                accuracy_note="摘要生成过程中出现错误"
            )

        # ── Content-Comment Comparison ──
        try:
            comparison_result = await asyncio.get_running_loop().run_in_executor(
                executor,
                generate_content_comment_comparison,
                t.video_summary.model_dump() if t.video_summary else None,
                video_type_result,
                state.cleaned_comments,
                clusters,
            )
            t.content_comment_comparison = ContentCommentComparison(**comparison_result)
        except Exception as e:
            t.warnings.append(f"内容-评论对照分析失败（已降级忽略）：{str(e)}")
            t.content_comment_comparison = ContentCommentComparison()

        # ── Visualization Recommendation ──
        try:
            viz_result = await asyncio.get_running_loop().run_in_executor(
                executor,
                generate_visualization_recommendation,
                video_type_result,
                state.cleaned_comments,
                clusters,
            )
            t.visualization_recommendation = VisualizationRecommendation(**viz_result)
        except Exception as e:
            t.warnings.append(f"可视化推荐生成失败（已降级忽略）：{str(e)}")
            t.visualization_recommendation = VisualizationRecommendation()

        # ── Heatmap Data ──
        try:
            heatmap_result = await asyncio.get_running_loop().run_in_executor(
                executor,
                generate_heatmap_data,
                video_type_result,
                state.cleaned_comments,
            )
            # Extract values and data_status from result
            heatmap_values = []
            for v in heatmap_result.get("values", []):
                heatmap_values.append(HeatmapValue(**v))
            t.heatmap_data = HeatmapData(
                x_axis=heatmap_result.get("x_axis", []),
                y_axis=heatmap_result.get("y_axis", []),
                unit=heatmap_result.get("unit", "评论倾向值"),
                value_explanation=heatmap_result.get("value_explanation", ""),
                values=heatmap_values,
            )
        except Exception as e:
            t.warnings.append(f"热力图数据生成失败（已降级忽略）：{str(e)}")
            t.heatmap_data = HeatmapData()

        # Persist files (safe filename, per task dir)
        set_status(TaskStatus.exporting)
        out_dir = _task_dir(job_id, task_id)
        slug = safe_slug(t.url)
        comments_path = os.path.join(out_dir, f"{slug}.comments.json")
        report_path = os.path.join(out_dir, f"{slug}.report.md")
        dump_json(comments_path, state.cleaned_comments)
        report = await asyncio.get_running_loop().run_in_executor(
            executor, build_report, state.raw_comments, state.cleaned_comments, clean_stats,
            t.video_summary.model_dump() if t.video_summary else None,
            t.video_type.model_dump() if t.video_type else None,
            t.cleaning_summary.model_dump() if t.cleaning_summary else None,
            t.content_comment_comparison.model_dump() if t.content_comment_comparison else None,
            t.visualization_recommendation.model_dump() if t.visualization_recommendation else None,
        )
        dump_text(report_path, report)

        state.comments_path = comments_path
        state.report_path = report_path
        t.files = FilesInfo(
            json=f"/api/jobs/{job_id}/{task_id}/comments",
            markdown=f"/api/jobs/{job_id}/{task_id}/report",
            pdf="",
        )

        # PDF export (best-effort; must not break main flow)
        try:
            pdf_fn = partial(
                export_pdf,
                backend_dir=os.path.dirname(__file__),
                platform=(t.platform.value if t.platform else ""),
                video_id=t.video_id or "",
                stance_stats=t.stance_stats or {},
                top_influence_comments=t.top_influence_comments or [],
                clusters=t.clusters or [],
                controversies=t.controversies or [],
                summary_lines=[summary] if summary else [],
                video_summary=t.video_summary.model_dump() if t.video_summary else None,
                video_type=t.video_type.model_dump() if t.video_type else None,
                cleaning_summary=t.cleaning_summary.model_dump() if t.cleaning_summary else None,
                content_comment_comparison=t.content_comment_comparison.model_dump() if t.content_comment_comparison else None,
                visualization_recommendation=t.visualization_recommendation.model_dump() if t.visualization_recommendation else None,
                heatmap_data=t.heatmap_data.model_dump() if t.heatmap_data else None,
            )
            pdf_path = await asyncio.get_running_loop().run_in_executor(executor, pdf_fn)
            state.pdf_path = pdf_path
            t.files.pdf = f"/api/jobs/{job_id}/{task_id}/pdf"
        except Exception as e:
            t.warnings.append(f"PDF 导出失败（已降级忽略）：{str(e) or e.__class__.__name__}")

        try:
            persist_job(job)
        except Exception:
            pass
        set_status(TaskStatus.done)
    except Exception as e:
        # Per-task try/except: failure doesn't affect others
        raw_msg = str(e) or e.__class__.__name__
        # Map to user-friendly message
        user_msg = _map_error_to_user_message(raw_msg)
        set_status(TaskStatus.failed, err=user_msg)


@app.post("/api/jobs", response_model=JobCreateResponse)
async def create_job(req: JobCreateRequest) -> JobCreateResponse:
    urls = [u.strip() for u in req.urls if u and u.strip()]
    if not urls:
        raise HTTPException(status_code=400, detail="urls 不能为空")

    job_id = random_id(14)
    job = JobState(job_id)
    job.force_refresh = bool(req.force_refresh)
    job.include_replies = bool(req.include_replies)
    jobs[job_id] = job

    tasks: List[TaskInfo] = []
    now = now_local_str()
    for url in urls:
        # Parse platform & video_id immediately (for cache key & API response)
        try:
            platform = detect_platform(url)
            if platform == Platform.bilibili:
                vid = bilibili.parse_video_id(url)
            else:
                vid = youtube.parse_video_id(url)
        except Exception as e:
            platform = None
            vid = ""
            # Create failed task but still return a task entry
            # (User asked platform/video_id not null; assumes valid URLs in normal use.)
            pass

        task_id = random_id(10)
        ti = TaskInfo(
            task_id=task_id,
            url=url,
            platform=platform,
            video_id=vid,
            status=TaskStatus.pending,
            source="fresh",
            limit=req.limit,
            include_replies=bool(req.include_replies),
            progress=0,
            raw_count=0,
            cleaned_count=0,
            main_count=0,
            reply_count=0,
            stance_stats={"support": 0, "oppose": 0, "neutral": 0, "joke": 0, "question": 0},
            top_influence_comments=[],
            clusters=[],
            opinion_clusters=OpinionClusters(),
            controversies=[],
            summary="",
            video_summary=VideoSummary(),
            video_type=VideoType(),
            cleaning_summary=CleaningSummary(),
            content_comment_comparison=ContentCommentComparison(),
            visualization_recommendation=VisualizationRecommendation(),
            heatmap_data=HeatmapData(),
            files=FilesInfo(),
            error="",
            warnings=[],
            created_at=now,
            updated_at=now,
        )
        if platform is None or not vid:
            ti.status = TaskStatus.failed
            ti.error = "URL 解析失败：仅支持 bilibili.com/b23.tv（BV号）或 youtube.com/youtu.be（VIDEO_ID）的有效视频链接"
        job.tasks[task_id] = TaskState(ti)
        tasks.append(ti)

    # Persist initial state on creation
    try:
        persist_job(job)
    except Exception:
        pass

    # Fire & forget background tasks
    for t in tasks:
        if t.status != TaskStatus.failed:
            asyncio.create_task(run_task(job_id, t.task_id))

    return JobCreateResponse(job_id=job_id, tasks=tasks)


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    job = jobs.get(job_id)
    if not job:
        job = load_job_from_disk(job_id)
        if job:
            jobs[job_id] = job
        else:
            raise HTTPException(status_code=404, detail="job_id 不存在或已过期")
    tasks = [s.task for s in job.tasks.values()]
    failed = [t for t in tasks if t.status == TaskStatus.failed]
    if failed:
        status = "failed"
        # Use friendly error messages
        errors = list({_map_error_to_user_message(t.error) for t in failed if t.error})
        error = "; ".join(errors) if errors else "部分任务失败"
    elif all(t.status == TaskStatus.done for t in tasks):
        status = "done"
        error = ""
    else:
        status = "running"
        error = ""
    return JobStatusResponse(job_id=job_id, status=status, error=error, tasks=tasks)


def _get_task(job_id: str, task_id: str) -> TaskState:
    job = jobs.get(job_id)
    if not job:
        job = load_job_from_disk(job_id)
        if job:
            jobs[job_id] = job
        else:
            raise HTTPException(status_code=404, detail="job_id 不存在或已过期")
    state = job.tasks.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="task_id 不存在")
    return state


@app.get("/api/jobs/{job_id}/{task_id}/comments")
async def download_comments(job_id: str, task_id: str):
    state = _get_task(job_id, task_id)
    if state.task.status != TaskStatus.done or not state.comments_path or not os.path.exists(state.comments_path):
        raise HTTPException(status_code=404, detail="comments 尚未生成")
    return FileResponse(state.comments_path, media_type="application/json", filename=os.path.basename(state.comments_path))


@app.get("/api/jobs/{job_id}/{task_id}/report")
async def download_report(job_id: str, task_id: str):
    state = _get_task(job_id, task_id)
    if state.task.status != TaskStatus.done or not state.report_path or not os.path.exists(state.report_path):
        raise HTTPException(status_code=404, detail="report 尚未生成")
    return FileResponse(state.report_path, media_type="text/markdown", filename=os.path.basename(state.report_path))


@app.get("/api/jobs/{job_id}/{task_id}/pdf")
async def download_pdf(job_id: str, task_id: str):
    state = _get_task(job_id, task_id)
    if state.task.status != TaskStatus.done or not state.pdf_path or not os.path.exists(state.pdf_path):
        raise HTTPException(status_code=404, detail="pdf 尚未生成")
    return FileResponse(state.pdf_path, media_type="application/pdf", filename=os.path.basename(state.pdf_path))


# ──────────────────────────────────────────────────
# AI Chat Endpoint
# ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户问题")
    history: List[Dict[str, str]] = Field(default_factory=list, description="对话历史")
    analysis_context: Dict[str, Any] = Field(default_factory=dict, description="分析上下文")


class ChatResponse(BaseModel):
    reply: str = ""
    error: Optional[str] = None


# Irrelevant question keywords
IRRELEVANT_PATTERNS = [
    # Weather related
    [r"天气", r"下雨", r"气温", r"温度"],
    # Programming homework
    [r"帮我写代码", r"作业", r"代码实现", r"编程"],
    # Emotional consulting
    [r"情感问题", r"失恋", r"追求", r"谈恋爱"],
    # Random chat
    [r"你好吗", r"今天怎么样", r"在吗", r"吃了没"],
    # Completely unrelated
    [r"股票", r"足球", r"篮球", r"游戏攻略(?!视频)"],
]


def is_irrelevant_question(message: str) -> tuple[bool, str]:
    """Simple keyword-based check for irrelevant questions."""
    msg_lower = message.lower()

    # Check for weather patterns
    weather_keywords = ["天气", "下雨", "气温", "温度", "天气怎么样"]
    if any(kw in msg_lower for kw in weather_keywords):
        return True, "这个问题与当前视频分析关系较弱。你可以问：评论区争议、用户需求、内容改进、比赛PPT表达等问题。"

    # Check for homework/coding
    homework_keywords = ["帮我写代码", "作业", "代码实现", "写一个程序"]
    if any(kw in msg_lower for kw in homework_keywords):
        return True, "这个问题与当前视频分析关系较弱。你可以问：评论区争议、用户需求、内容改进、比赛PPT表达等问题。"

    # Check for emotional/relationship
    emotion_keywords = ["情感问题", "失恋", "追求", "谈恋爱", "表白"]
    if any(kw in msg_lower for kw in emotion_keywords):
        return True, "这个问题与当前视频分析关系较弱。你可以问：评论区争议、用户需求、内容改进、比赛PPT表达等问题。"

    # Check for random chat
    random_keywords = ["你好吗", "今天怎么样", "在吗", "吃了没", "你好啊"]
    if any(kw in msg_lower for kw in random_keywords) and len(message) < 20:
        return True, "这个问题与当前视频分析关系较弱。你可以问：评论区争议、用户需求、内容改进、比赛PPT表达等问题。"

    return False, ""


def sanitize_analysis_context(raw_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract only allowed fields from analysis_context.
    Prevent large data like comments, examples, heatmap values from being sent.
    """
    ctx = {}

    # video_type
    vt = raw_context.get("video_type", {}) or {}
    ctx["video_type"] = {
        "primary": str(vt.get("primary", "") or ""),
        "secondary": str(vt.get("secondary", "") or ""),
    }

    # video_summary
    vs = raw_context.get("video_summary", {}) or {}
    ctx["video_summary"] = {
        "summary": str(vs.get("summary", "") or "")[:500],  # Limit summary length
        "key_points": (vs.get("key_points", []) or [])[:5],  # Max 5 key points
    }

    # content_comment_comparison
    cc = raw_context.get("content_comment_comparison", {}) or {}
    ctx["content_comment_comparison"] = {
        "video_focus": (cc.get("video_focus", []) or [])[:5],
        "audience_focus": (cc.get("audience_focus", []) or [])[:5],
        "gap_analysis": str(cc.get("gap_analysis", "") or "")[:300],
    }

    # top_insights - only first 5
    insights = raw_context.get("top_insights", []) or []
    if isinstance(insights, list):
        ctx["top_insights"] = [str(i)[:200] for i in insights[:5]]

    return ctx


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    AI chat endpoint for video comment analysis assistant.
    """
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        return ChatResponse(reply="", error="OPENAI_API_KEY_NOT_CONFIGURED")

    # Check message length
    message = request.message[:1000] if request.message else ""

    # Check max turns (count user messages)
    user_turns = sum(1 for h in request.history if h.get("role") == "user")
    if user_turns >= 10:
        return ChatResponse(reply="", error="MAX_TURNS_EXCEEDED")

    # Check for irrelevant questions
    is_irrelevant, guidance = is_irrelevant_question(message)
    if is_irrelevant:
        return ChatResponse(reply=guidance, error="IRRELEVANT_QUESTION")

    # Build context from history (use last 6 turns = 12 messages)
    history = (request.history or [])[-12:]

    # Sanitize analysis context
    context = sanitize_analysis_context(request.analysis_context or {})

    # Build system prompt
    system_prompt = """你是 ViewLens 的视频评论洞察助手。
你的任务是基于当前视频分析结果，帮助用户理解评论区观点结构、用户需求、争议焦点和内容改进方向。

回答要求：
1. 使用结构化表达。
2. 优先输出：核心结论、依据、建议。
3. 只能基于提供的 analysis_context 作答。
4. 不要编造不存在的数据。
5. 如果依据不足，要明确说"当前数据不足以支持该结论"。
6. 评论区反馈不等于客观事实，必须表述为"评论区反馈显示"。
7. 回答风格要像产品经理或数据分析师，而不是闲聊机器人。"""

    # Build context string
    context_str = ""
    if context:
        context_str = "\n\n=== 当前视频分析上下文 ===\n"

        if context.get("video_type", {}).get("primary"):
            vt = context["video_type"]
            context_str += f"视频类型：{vt['primary']}"
            if vt.get("secondary"):
                context_str += f"（辅助：{vt['secondary']}）"
            context_str += "\n"

        if context.get("video_summary", {}).get("summary"):
            vs = context["video_summary"]
            context_str += f"\n视频摘要：{vs['summary'][:300]}\n"
            if vs.get("key_points"):
                context_str += f"关键内容：{'、'.join(vs['key_points'][:5])}\n"

        if context.get("content_comment_comparison"):
            cc = context["content_comment_comparison"]
            if cc.get("video_focus"):
                context_str += f"\n视频关注点：{'、'.join(cc['video_focus'][:5])}\n"
            if cc.get("audience_focus"):
                context_str += f"评论区关注点：{'、'.join(cc['audience_focus'][:5])}\n"
            if cc.get("gap_analysis"):
                context_str += f"差异分析：{cc['gap_analysis'][:300]}\n"

        if context.get("top_insights"):
            insights = context["top_insights"]
            context_str += f"\n核心洞察（{len(insights)}条）：\n"
            for i, insight in enumerate(insights[:5], 1):
                context_str += f"{i}. {str(insight)[:150]}\n"

        context_str += "=" * 40 + "\n"

    # Build messages for OpenAI
    messages = [{"role": "system", "content": system_prompt + context_str}]

    # Add history
    for h in history:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ["user", "assistant"]:
            messages.append({"role": role, "content": content[:500]})

    # Add current message
    messages.append({"role": "user", "content": message})

    # Call LLM using unified module
    from backend.llm import call_llm, get_llm_config
    
    config = get_llm_config()
    if not config["api_key"]:
        return ChatResponse(reply="", error="OPENAI_API_KEY 未配置，请联系管理员")
    
    success, result = call_llm(
        prompt=message,
        system_prompt=system_prompt + context_str,
        model=model,
        temperature=0.3,
        max_tokens=1000,
    )
    
    if result["ok"]:
        return ChatResponse(reply=result["content"], error=None)
    else:
        return ChatResponse(reply="", error=result["error"])


@app.get("/api/health")
async def health():
    return JSONResponse({"ok": True, "jobs": len(jobs)})


@app.get("/api/ai/health")
async def ai_health():
    """Check AI service health status"""
    from backend.llm import check_llm_health
    health = check_llm_health()
    return JSONResponse(health)


@app.get("/api/cors-diagnostic")
async def cors_diagnostic():
    """Debug: returns the effective CORS configuration."""
    raw = os.getenv("CORS_ORIGINS", "").strip()
    return {
        "CORS_ORIGINS_raw": raw or "(not set — defaults to localhost)",
        "effective_allow_origins": _cors_origins,
        "allow_credentials": False,
        "allow_methods": "*",
        "allow_headers": "*",
    }

