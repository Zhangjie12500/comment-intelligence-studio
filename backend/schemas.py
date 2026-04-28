from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    bilibili = "bilibili"
    youtube = "youtube"


class TaskStatus(str, Enum):
    pending = "pending"
    fetching = "fetching"
    analyzing = "analyzing"
    exporting = "exporting"
    done = "done"
    failed = "failed"


class JobCreateRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1, description="每行一个视频链接")
    limit: int = Field(1000, ge=1, le=50000)
    force_refresh: bool = False
    include_replies: bool = True


class FilesInfo(BaseModel):
    json: str = ""
    markdown: str = ""
    pdf: str = ""


class VideoSummary(BaseModel):
    has_subtitle: bool = False
    summary: str = ""
    key_points: List[str] = Field(default_factory=list)
    accuracy_note: str = ""


class VideoType(BaseModel):
    primary: str = ""
    secondary: str = ""
    confidence: float = 0.0
    reason: str = ""


class CleaningSummary(BaseModel):
    original_count: int = 0
    cleaned_count: int = 0
    removed_count: int = 0
    low_info_count: int = 0
    duplicate_count: int = 0
    strategy: str = ""


class ContentCommentComparison(BaseModel):
    video_focus: List[str] = Field(default_factory=list)
    audience_focus: List[str] = Field(default_factory=list)
    gap_analysis: str = ""
    audience_needs: List[str] = Field(default_factory=list)
    missed_topics: List[str] = Field(default_factory=list)


class VisualizationRecommendation(BaseModel):
    chart_type: str = ""
    reason: str = ""
    fallback: str = ""
    data_status: str = "insufficient"


class HeatmapValue(BaseModel):
    product: str = ""
    aspect: str = ""
    value: float = 0.0
    sentiment: str = "neutral"
    count: int = 0
    examples: List[str] = Field(default_factory=list)


class HeatmapData(BaseModel):
    x_axis: List[str] = Field(default_factory=list)
    y_axis: List[str] = Field(default_factory=list)
    unit: str = "评论倾向值"
    value_explanation: str = ""
    values: List[HeatmapValue] = Field(default_factory=list)


class OpinionCluster(BaseModel):
    summary: str = ""
    sentiment: str = "neutral"
    ratio: float = 0.0
    examples: List[str] = Field(default_factory=list)


class OpinionClusters(BaseModel):
    opinion_clusters: List[OpinionCluster] = Field(default_factory=list)


class TaskInfo(BaseModel):
    task_id: str
    url: str
    platform: Optional[Platform] = None
    video_id: str = ""
    status: TaskStatus
    source: str = Field("fresh", description="cache/fresh")
    limit: int = Field(1000, ge=1, le=50000)
    include_replies: bool = True
    progress: int = 0
    raw_count: int = 0
    cleaned_count: int = 0
    main_count: int = 0
    reply_count: int = 0
    stance_stats: Dict[str, int] = Field(default_factory=lambda: {"support": 0, "oppose": 0, "neutral": 0, "joke": 0, "question": 0})
    top_influence_comments: List[Dict[str, Any]] = Field(default_factory=list)
    clusters: List[Dict[str, Any]] = Field(default_factory=list)
    opinion_clusters: OpinionClusters = Field(default_factory=OpinionClusters)
    controversies: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    ai_status: Dict[str, Any] = Field(default_factory=lambda: {"enabled": False, "model": "gpt-4o-mini", "message": "AI总结不可用，已使用规则分析结果。", "error": None})
    video_summary: VideoSummary = Field(default_factory=VideoSummary)
    video_type: VideoType = Field(default_factory=VideoType)
    cleaning_summary: CleaningSummary = Field(default_factory=CleaningSummary)
    content_comment_comparison: ContentCommentComparison = Field(default_factory=ContentCommentComparison)
    visualization_recommendation: VisualizationRecommendation = Field(default_factory=VisualizationRecommendation)
    heatmap_data: HeatmapData = Field(default_factory=HeatmapData)
    files: FilesInfo = Field(default_factory=FilesInfo)
    error: str = ""
    warnings: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class JobCreateResponse(BaseModel):
    job_id: str
    tasks: List[TaskInfo]


class JobStatusResponse(BaseModel):
    job_id: str
    status: str = Field("running", description="running/done/failed")
    error: str = Field("", description="主要错误信息，任一task失败时汇总显示")
    tasks: List[TaskInfo]


class CommentItem(BaseModel):
    platform: Platform
    video_id: str = ""
    user: str
    text: str
    like: int = 0
    reply_count: int = 0
    time: str
    type: str = Field(..., description="main/reply")
    parent: str = ""
    translation_zh: str = ""
    stance: str = Field("neutral", description="support/oppose/neutral/joke/question")
    influence_score: float = 0.0
    cluster_id: str = ""
    extra: Dict[str, Any] = Field(default_factory=dict)

