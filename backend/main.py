from __future__ import annotations

import asyncio
import os
import json
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    clean_and_merge,
    compute_stance_stats,
    compute_top_influence,
    compute_clusters,
    compute_controversies,
    compute_summary,
)
from backend.cache import read_cache, write_cache
from backend.pdf_exporter import export_pdf
from backend.schemas import FilesInfo, JobCreateRequest, JobCreateResponse, JobStatusResponse, Platform, TaskInfo, TaskStatus
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
        # Collect distinct errors
        errors = list({s.task.error for s in failed_tasks if s.task.error})
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
    raise ValueError("无法识别平台：仅支持 bilibili.com/b23.tv 与 youtube.com/youtu.be")


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


# Allowlist origins for CORS. Set CORS_ORIGINS env var (comma-separated) in production.
# Example: CORS_ORIGINS=https://your-app.vercel.app,https://your-app-git-branch.vercel.app
# In development (no CORS_ORIGINS set), defaults to localhost:5173 only.
_cors_raw = os.getenv("CORS_ORIGINS", "").strip()
_cors_origins = (
    [o.strip() for o in _cors_raw.split(",") if o.strip()]
    if _cors_raw
    else ["http://localhost:5173", "http://127.0.0.1:5173"]
)

app = FastAPI(title=APP_TITLE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        cleaned, clean_stats = await asyncio.get_running_loop().run_in_executor(executor, clean_and_merge, state.raw_comments)
        state.cleaned_comments = cleaned or []
        t.cleaned_count = len(state.cleaned_comments)
        t.main_count = sum(1 for c in state.cleaned_comments if c.get("type") == "main")
        t.reply_count = sum(1 for c in state.cleaned_comments if c.get("type") == "reply")

        # Run all local analysis and write results back to the task fields
        stance_stats = await asyncio.get_running_loop().run_in_executor(executor, compute_stance_stats, state.cleaned_comments)
        top_influence = await asyncio.get_running_loop().run_in_executor(executor, compute_top_influence, state.cleaned_comments, 10)
        clusters = await asyncio.get_running_loop().run_in_executor(executor, compute_clusters, state.cleaned_comments)
        controversies = await asyncio.get_running_loop().run_in_executor(executor, compute_controversies, stance_stats, top_influence)
        platform_val = t.platform.value if t.platform else ""
        summary = await asyncio.get_running_loop().run_in_executor(
            executor, compute_summary, stance_stats, clusters, t.cleaned_count, t.raw_count or 0, platform_val
        )

        t.stance_stats = stance_stats
        t.top_influence_comments = top_influence
        t.clusters = clusters
        t.controversies = controversies
        t.summary = summary

        # Persist files (safe filename, per task dir)
        set_status(TaskStatus.exporting)
        out_dir = _task_dir(job_id, task_id)
        slug = safe_slug(t.url)
        comments_path = os.path.join(out_dir, f"{slug}.comments.json")
        report_path = os.path.join(out_dir, f"{slug}.report.md")
        dump_json(comments_path, state.cleaned_comments)
        report = await asyncio.get_running_loop().run_in_executor(
            executor, build_report, state.raw_comments, state.cleaned_comments, clean_stats
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
        msg = str(e) or e.__class__.__name__
        set_status(TaskStatus.failed, err=msg)


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
            controversies=[],
            summary="",
            files=FilesInfo(),
            error="",
            warnings=[],
            created_at=now,
            updated_at=now,
        )
        if platform is None or not vid:
            ti.status = TaskStatus.failed
            ti.error = "URL 解析失败：请确认是 bilibili.com/b23.tv 或 youtube.com/youtu.be 的有效视频链接"
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
        errors = list({t.error for t in failed if t.error})
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


@app.get("/api/health")
async def health():
    return JSONResponse({"ok": True, "jobs": len(jobs)})

