import { useEffect, useRef, useState } from 'react';
import { BarChart2, TrendingUp, Users, MessageSquare, Inbox, Sparkles, BrainCircuit } from 'lucide-react';
import * as echarts from 'echarts';
import Card from './Card';
import { CardTitle } from './Card';
import { EmptyState } from './StatusStates';
import VideoSummaryCard from './VideoSummaryCard';
import VideoTypeCard from './VideoTypeCard';
import CleaningSummaryCard from './CleaningSummaryCard';
import ContentCommentCard from './ContentCommentCard';
import VisualizationCard from './VisualizationCard';
import AiChatBox from './AiChatBox';

// ──────────────────────────────────────────────────
// Video Info Card
// ──────────────────────────────────────────────────
function VideoInfoCard({ video }) {
  if (!video) return null;

  return (
    <Card className="overflow-hidden">
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <CardTitle icon={BarChart2}>视频信息</CardTitle>
      </div>
      <div className="p-5">
        <div className="flex flex-col gap-3">
          <InfoRow label="标题" value={video.title || '—'} />
          <InfoRow label="作者" value={video.author || video.user || '—'} />
          <InfoRow label="评论数" value={video.comment_count?.toLocaleString() || '—'} />
          <InfoRow label="平台" value={video.platform === 'bilibili' ? 'B站' : video.platform === 'youtube' ? 'YouTube' : '—'} />
        </div>
      </div>
    </Card>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-start gap-3">
      <span className="text-xs text-[#9CA3AF] w-16 flex-shrink-0">{label}</span>
      <span className="text-sm text-[#374151] flex-1">{value}</span>
    </div>
  );
}

// ──────────────────────────────────────────────────
// Summary Card - AI Analysis Summary
// ──────────────────────────────────────────────────
function SummaryCard({ summary, aiStatus }) {
  // Check if summary is structured (object) or plain text
  const isStructured = summary && typeof summary === 'object';
  const structuredData = isStructured ? summary : null;
  const plainText = isStructured ? structuredData.summary : summary;

  // AI status display
  const aiEnabled = aiStatus?.enabled;
  const aiModel = aiStatus?.model || 'gpt-4o-mini';
  const aiMessage = aiStatus?.message;
  const aiError = aiStatus?.error;

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <div className="flex items-center justify-between">
          <CardTitle icon={Sparkles}>AI 分析总结</CardTitle>
          {/* AI Status Badge */}
          <div className="flex items-center gap-2">
            {aiEnabled ? (
              <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                AI总结已启用 · {aiModel}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                {aiMessage || 'AI总结不可用，已使用规则分析结果。'}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="p-5">
        {!summary ? (
          <p className="text-sm" style={{ color: '#9CA3AF' }}>暂无分析结果</p>
        ) : isStructured ? (
          // Structured rendering - Medium/Zhihu style
          <div className="space-y-5">
            {/* Title */}
            {structuredData.title && (
              <h3 className="text-lg font-semibold leading-relaxed" style={{ color: '#111827' }}>
                {structuredData.title}
              </h3>
            )}

            {/* Summary paragraph */}
            {structuredData.summary && (
              <p
                className="text-sm leading-7 break-words whitespace-pre-wrap"
                style={{ color: '#374151' }}
              >
                {structuredData.summary}
              </p>
            )}

            {/* Key Points */}
            {structuredData.points && structuredData.points.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wide" style={{ color: '#6B7280' }}>
                  核心观点
                </h4>
                <ul className="list-disc pl-5 space-y-2">
                  {structuredData.points.map((point, i) => (
                    <li
                      key={i}
                      className="text-sm leading-6 break-words"
                      style={{ color: '#374151' }}
                    >
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Additional sections */}
            {structuredData.sections && Object.entries(structuredData.sections).map(([key, items]) => (
              items && items.length > 0 && (
                <div key={key} className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wide" style={{ color: '#6B7280' }}>
                    {key}
                  </h4>
                  <ul className="list-disc pl-5 space-y-1">
                    {items.map((item, i) => (
                      <li
                        key={i}
                        className="text-sm leading-6 break-words"
                        style={{ color: '#374151' }}
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )
            ))}

            {/* AI error info */}
            {aiError && (
              <div
                className="mt-4 p-3 rounded-lg border"
                style={{
                  background: '#FEF2F2',
                  borderColor: '#FECACA',
                }}
              >
                <p className="text-xs" style={{ color: '#991B1B' }}>
                  AI 错误: {aiError}
                </p>
              </div>
            )}
          </div>
        ) : (
          // Plain text fallback - improved styling
          <div
            className="text-sm leading-7 break-words whitespace-pre-wrap"
            style={{ color: '#374151' }}
          >
            {plainText}
          </div>
        )}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────────
// Stance Pie Chart Card
// ──────────────────────────────────────────────────
const STANCE_CONFIG = {
  support: { label: '支持', color: '#10B981' },
  oppose: { label: '反对', color: '#EF4444' },
  neutral: { label: '中立', color: '#6B7280' },
  joke: { label: '调侃', color: '#8B5CF6' },
  question: { label: '提问', color: '#3B82F6' },
};

function StanceChartCard({ stats }) {
  const chartRef = useRef(null);
  const instRef = useRef(null);

  const hasData = stats && Object.values(stats).some(v => v > 0);

  useEffect(() => {
    if (!chartRef.current) return;
    if (instRef.current) { instRef.current.dispose(); instRef.current = null; }
    if (!hasData) return;

    const inst = echarts.init(chartRef.current, null, { renderer: 'canvas' });
    instRef.current = inst;

    const total = Object.values(stats).reduce((a, b) => a + b, 0);
    const data = Object.entries(stats)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({
        name: STANCE_CONFIG[k]?.label || k,
        value: v,
        itemStyle: { color: STANCE_CONFIG[k]?.color || '#6B7280' },
      }));

    inst.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: '#FFFFFF',
        borderColor: '#E5E7EB',
        borderWidth: 1,
        textStyle: { color: '#374151', fontSize: 12 },
        formatter: p => `${p.name}：${p.value} (${total > 0 ? ((p.value / total) * 100).toFixed(1) : 0}%)`,
      },
      legend: {
        bottom: 4,
        textStyle: { color: '#6B7280', fontSize: 11 },
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 16,
      },
      series: [{
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        label: { show: false },
        data,
      }],
    });

    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(chartRef.current);
    return () => { ro.disconnect(); inst.dispose(); };
  }, [stats, hasData]);

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <CardTitle icon={BarChart2}>情绪分布</CardTitle>
      </div>
      <div className="p-5">
        {hasData ? (
          <div ref={chartRef} style={{ width: '100%', height: 220 }} />
        ) : (
          <div className="h-[220px] flex items-center justify-center">
            <span className="text-sm" style={{ color: '#9CA3AF' }}>暂无数据</span>
          </div>
        )}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────────
// Top Comments Card
// ──────────────────────────────────────────────────
const STANCE_STYLES = {
  support:  { color: '#059669', bg: '#D1FAE5', border: '#A7F3D0' },
  oppose:   { color: '#DC2626', bg: '#FEE2E2', border: '#FECACA' },
  question: { color: '#2563EB', bg: '#DBEAFE', border: '#BFDBFE' },
  joke:     { color: '#7C3AED', bg: '#EDE9FE', border: '#DDD6FE' },
  neutral:  { color: '#6B7280', bg: '#F3F4F6', border: '#E5E7EB' },
};

function TopCommentsCard({ comments }) {
  const list = comments && comments.length > 0 ? comments : null;

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <CardTitle icon={TrendingUp}>高影响评论 Top 10</CardTitle>
      </div>
      <div className="p-5 flex flex-col gap-3">
        {!list ? (
          <p className="text-sm" style={{ color: '#9CA3AF' }}>暂无数据</p>
        ) : (
          list.map((c, i) => {
            const style = STANCE_STYLES[c.stance] || STANCE_STYLES.neutral;
            const label = STANCE_CONFIG[c.stance]?.label || '中立';
            
            return (
              <div 
                key={i} 
                className="flex gap-4 p-4 rounded-lg transition-all duration-180 hover:-translate-y-0.5"
                style={{ 
                  background: '#FAFAFA', 
                  border: '1px solid #F3F4F6',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = '#F3F4F6';
                  e.currentTarget.style.borderColor = '#E5E7EB';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = '#FAFAFA';
                  e.currentTarget.style.borderColor = '#F3F4F6';
                }}
              >
                {/* Rank & stance */}
                <div className="flex flex-col items-center gap-2 min-w-[40px]">
                  <span className="text-sm font-mono font-semibold" style={{ color: '#9CA3AF' }}>
                    #{i + 1}
                  </span>
                  <span 
                    className="tag text-xs"
                    style={{ background: style.bg, color: style.color, fontSize: '11px' }}
                  >
                    {label}
                  </span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 flex flex-col gap-2">
                  <p className="text-sm leading-relaxed line-clamp-2" style={{ color: '#374151' }}>
                    {c.text || '—'}
                  </p>
                  <div className="flex items-center gap-4 text-xs" style={{ color: '#9CA3AF' }}>
                    <span>{c.user || '匿名'}</span>
                    {c.like > 0 && (
                      <span>👍 {Number(c.like).toLocaleString()}</span>
                    )}
                    {c.reply_count > 0 && (
                      <span>💬 {c.reply_count}</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────────
// Opinion Clusters Card - AI-powered clustering
// ──────────────────────────────────────────────────
const OPINION_SENTIMENT_CONFIG = {
  positive: { label: '正面', color: '#10B981', bg: '#D1FAE5', border: '#A7F3D0' },
  negative: { label: '负面', color: '#EF4444', bg: '#FEE2E2', border: '#FECACA' },
  neutral:  { label: '中性', color: '#6B7280', bg: '#F3F4F6', border: '#E5E7EB' },
  mixed:    { label: '混合', color: '#8B5CF6', bg: '#EDE9FE', border: '#DDD6FE' },
};

function OpinionClustersCard({ opinionClusters, aiStatus }) {
  const list = opinionClusters?.opinion_clusters || [];
  const aiEnabled = aiStatus?.enabled;

  // Show nothing if no clusters
  if (!list || list.length === 0) {
    return null;
  }

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <div className="flex items-center justify-between">
          <CardTitle icon={BrainCircuit}>AI 观点聚类</CardTitle>
          {aiEnabled ? (
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              AI聚类已启用
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              规则聚类
            </span>
          )}
        </div>
      </div>
      <div className="p-5">
        <div className="flex flex-col gap-4">
          {list.map((cluster, i) => {
            const sentiment = OPINION_SENTIMENT_CONFIG[cluster.sentiment] || OPINION_SENTIMENT_CONFIG.neutral;
            const ratio = cluster.ratio || 0;

            return (
              <div
                key={i}
                className="rounded-lg border border-[#E5E7EB] overflow-hidden"
              >
                {/* Header */}
                <div className="px-4 py-3 bg-gray-50 border-b border-[#E5E7EB]">
                  <div className="flex items-center gap-3">
                    <span
                      className="flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center text-xs font-bold text-white"
                      style={{ background: '#4F46E5' }}
                    >
                      {i + 1}
                    </span>
                    <span className="text-sm font-semibold" style={{ color: '#111827' }}>
                      {cluster.summary || `观点 ${i + 1}`}
                    </span>
                  </div>
                </div>

                {/* Meta info */}
                <div className="px-4 py-2 flex items-center gap-4 bg-white">
                  <span
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                    style={{ background: sentiment.bg, color: sentiment.color }}
                  >
                    {sentiment.label}
                  </span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${Math.round(ratio * 100)}%`, background: '#4F46E5' }}
                      />
                    </div>
                    <span className="text-xs font-medium" style={{ color: '#4F46E5' }}>
                      {Math.round(ratio * 100)}%
                    </span>
                  </div>
                </div>

                {/* Examples */}
                {cluster.examples && cluster.examples.length > 0 && (
                  <div className="px-4 py-3 bg-white">
                    <div className="flex flex-col gap-2">
                      {cluster.examples.slice(0, 2).map((ex, ri) => (
                        <div
                          key={ri}
                          className="p-3 rounded-lg text-sm leading-relaxed"
                          style={{
                            background: '#F9FAFB',
                            border: '1px solid #F3F4F6',
                            color: '#374151',
                          }}
                        >
                          {ex}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────────
// Clusters Card - LLM Semantic Clustering
// ──────────────────────────────────────────────────
const SENTIMENT_CONFIG = {
  positive: { label: '正面', color: '#10B981', bg: '#D1FAE5', border: '#A7F3D0' },
  negative: { label: '负面', color: '#EF4444', bg: '#FEE2E2', border: '#FECACA' },
  neutral:  { label: '中性', color: '#6B7280', bg: '#F3F4F6', border: '#E5E7EB' },
};

function ClustersCard({ clusters }) {
  const list = clusters && clusters.length > 0 ? clusters : null;

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <CardTitle icon={Users}>观点洞察</CardTitle>
      </div>
      <div className="p-5">
        {!list ? (
          <p className="text-sm" style={{ color: '#9CA3AF' }}>暂无数据</p>
        ) : list.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm" style={{ color: '#9CA3AF' }}>评论数量不足，暂无法生成观点洞察</p>
          </div>
        ) : (
          <div className="flex flex-col gap-5">
            {list.map((cluster, i) => {
              const sentiment = SENTIMENT_CONFIG[cluster.sentiment] || SENTIMENT_CONFIG.neutral;
              const ratio = cluster.ratio || 0;
              const count = cluster.count || Math.round(ratio * 100);
              
              return (
                <div 
                  key={i}
                  className="rounded-xl border border-[#E5E7EB] overflow-hidden transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
                >
                  {/* Header - viewpoint summary */}
                  <div className="px-5 py-4 bg-gradient-to-r from-slate-50 to-white border-b border-[#E5E7EB]">
                    <div className="flex items-start gap-3">
                      {/* Index badge */}
                      <span 
                        className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold text-white"
                        style={{ background: '#2563EB' }}
                      >
                        {i + 1}
                      </span>
                      
                      {/* Summary title */}
                      <div className="flex-1 min-w-0">
                        <h4 className="text-base font-bold leading-relaxed" style={{ color: '#111827' }}>
                          {cluster.summary || `观点 ${i + 1}`}
                        </h4>
                        
                        {/* Meta info row */}
                        <div className="flex items-center gap-3 mt-2 flex-wrap">
                          {/* Sentiment tag */}
                          <span 
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                            style={{ background: sentiment.bg, color: sentiment.color }}
                          >
                            <span 
                              className="w-1.5 h-1.5 rounded-full"
                              style={{ background: sentiment.color }}
                            />
                            {sentiment.label}
                          </span>
                          
                          {/* Ratio bar */}
                          <div className="flex items-center gap-2">
                            <div className="w-24 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                              <div 
                                className="h-full rounded-full transition-all duration-500"
                                style={{ 
                                  width: `${Math.round(ratio * 100)}%`,
                                  background: '#2563EB' 
                                }}
                              />
                            </div>
                            <span className="text-xs font-medium" style={{ color: '#2563EB' }}>
                              {Math.round(ratio * 100)}%
                            </span>
                            <span className="text-xs" style={{ color: '#9CA3AF' }}>
                              ({count} 条)
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Keywords (if available) */}
                  {(cluster.keywords || []).length > 0 && (
                    <div className="px-5 py-3 bg-gray-50 border-b border-[#E5E7EB]">
                      <div className="flex flex-wrap gap-2">
                        {(cluster.keywords || []).slice(0, 6).map((kw, ki) => (
                          <span 
                            key={ki}
                            className="text-xs px-2 py-1 rounded-md transition-colors duration-150 hover:bg-gray-100"
                            style={{ 
                              background: '#FFFFFF', 
                              color: '#6B7280',
                              border: '1px solid #E5E7EB',
                            }}
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Representative comments - support both formats */}
                  {((cluster.representative_comments || []).length > 0 || (cluster.examples || []).length > 0) && (
                    <div className="px-5 py-4 bg-white">
                      <p className="text-xs font-medium mb-3" style={{ color: '#6B7280' }}>
                        代表评论
                      </p>
                      <div className="flex flex-col gap-2">
                        {/* New format: examples (string array) */}
                        {(cluster.examples || []).slice(0, 2).map((ex, ri) => (
                          <div 
                            key={`ex-${ri}`}
                            className="p-3 rounded-lg transition-colors duration-150 hover:bg-gray-50"
                            style={{ 
                              background: '#F9FAFB', 
                              border: '1px solid #F3F4F6',
                            }}
                          >
                            <p className="text-sm leading-relaxed line-clamp-2 break-words" style={{ color: '#374151' }}>
                              {ex}
                            </p>
                          </div>
                        ))}
                        {/* Old format: representative_comments (object array) */}
                        {(cluster.representative_comments || []).slice(0, 3).map((rep, ri) => (
                          <div 
                            key={`rep-${ri}`}
                            className="p-3 rounded-lg transition-colors duration-150 hover:bg-gray-50"
                            style={{ 
                              background: '#F9FAFB', 
                              border: '1px solid #F3F4F6',
                            }}
                          >
                            <p className="text-sm leading-relaxed line-clamp-2 break-words" style={{ color: '#374151' }}>
                              {rep.text || '—'}
                            </p>
                            <div className="flex items-center gap-3 mt-2 text-xs" style={{ color: '#9CA3AF' }}>
                              {rep.user && <span>{rep.user}</span>}
                              {rep.like > 0 && (
                                <span className="flex items-center gap-1">
                                  👍 {Number(rep.like).toLocaleString()}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────────
// Controversies Card
// ──────────────────────────────────────────────────
function ControversiesCard({ controversies }) {
  const list = controversies && controversies.length > 0 ? controversies : null;

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <CardTitle icon={MessageSquare}>争议点</CardTitle>
      </div>
      <div className="p-5 flex flex-col gap-4">
        {!list ? (
          <p className="text-sm" style={{ color: '#9CA3AF' }}>暂无数据</p>
        ) : list.length === 0 ? (
          <div className="text-center py-6">
            <p className="text-sm" style={{ color: '#9CA3AF' }}>暂无明显争议</p>
          </div>
        ) : (
          list.map((co, i) => (
            <div 
              key={i} 
              className="p-4 rounded-lg transition-all duration-180 hover:-translate-y-0.5"
              style={{ background: '#FFFBEB', border: '1px solid #FDE68A' }}
              onMouseEnter={e => {
                e.currentTarget.style.background = '#FEF3C7';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = '#FFFBEB';
              }}
            >
              <p className="text-sm font-semibold mb-1.5" style={{ color: '#B45309' }}>
                {co.title || `争议点 ${i + 1}`}
              </p>
              {co.description && (
                <p className="text-sm leading-relaxed mb-3" style={{ color: '#92400E' }}>
                  {co.description}
                </p>
              )}
              {(co.sample_comments || []).length > 0 && (
                <div className="flex flex-col gap-1">
                  {(co.sample_comments || []).slice(0, 2).map((s, ri) => (
                    <p 
                      key={ri} 
                      className="text-xs line-clamp-1"
                      style={{ 
                        color: '#B45309', 
                        paddingLeft: '0.75rem', 
                        borderLeft: '2px solid #F59E0B' 
                      }}
                    >
                      · {String(s).slice(0, 100)}
                    </p>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────────
// Main Analysis Section
// ──────────────────────────────────────────────────
export default function AnalysisSection({ report, job, isLoading }) {
  // Find first done task with analysis data
  const task = (job?.tasks || [])
    .filter(t => t.status === 'done')
    .sort((a, b) => (b.cleaned_count || 0) - (a.cleaned_count || 0))[0];

  const stats = task?.stance_stats || report?.stance_stats || null;
  const topComments = task?.top_influence_comments || report?.top_influence_comments || null;
  const clusters = task?.clusters || report?.clusters || null;
  const controversies = task?.controversies || report?.controversies || null;
  const summary = task?.summary || report?.summary || null;
  const aiStatus = task?.ai_status || report?.ai_status || null;
  const video = task || report;
  const videoSummary = task?.video_summary || report?.video_summary || null;
  const videoType = task?.video_type || report?.video_type || null;
  const cleaningSummary = task?.cleaning_summary || report?.cleaning_summary || null;
  const contentCommentComparison = task?.content_comment_comparison || report?.content_comment_comparison || null;
  const visualizationRecommendation = task?.visualization_recommendation || report?.visualization_recommendation || null;
  const heatmapData = task?.heatmap_data || report?.heatmap_data || null;

  const hasAny = !!(stats || topComments || clusters || controversies || summary);

  // Show empty state when no analysis yet
  if (!hasAny && !isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <div className="divider">
          <div className="divider-line" />
          <span className="divider-text">分析结果</span>
          <div className="divider-line" />
        </div>
        <EmptyState type="initial" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Section header */}
      <div className="divider">
        <div className="divider-line" />
        <span className="divider-text">分析结果</span>
        <div className="divider-line" />
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Video Summary Card */}
        <div className="lg:col-span-2">
          <VideoSummaryCard videoSummary={videoSummary} />
        </div>

        {/* Video Type Card */}
        <div className="lg:col-span-2">
          <VideoTypeCard videoType={videoType} />
        </div>

        {/* Cleaning Summary Card */}
        <div className="lg:col-span-2">
          <CleaningSummaryCard cleaningSummary={cleaningSummary} />
        </div>

        {/* Content-Comment Comparison Card */}
        <div className="lg:col-span-2">
          <ContentCommentCard comparison={contentCommentComparison} />
        </div>

        {/* Visualization Recommendation Card */}
        <div className="lg:col-span-2">
          <VisualizationCard vizRecommendation={visualizationRecommendation} heatmapData={heatmapData} />
        </div>

        {summary && (
          <div className="lg:col-span-2">
            <SummaryCard summary={summary} aiStatus={aiStatus} />
          </div>
        )}

        {/* AI Opinion Clusters Card */}
        <div className="lg:col-span-2">
          <OpinionClustersCard opinionClusters={task?.opinion_clusters} aiStatus={aiStatus} />
        </div>

        <StanceChartCard stats={stats} />

        <VideoInfoCard video={video} />

        <div className="lg:col-span-2">
          <TopCommentsCard comments={topComments} />
        </div>

        <div className="lg:col-span-2">
          <ClustersCard clusters={clusters} />
        </div>

        <div className="lg:col-span-2">
          <ControversiesCard controversies={controversies} />
        </div>

        {/* AI Chat Box */}
        <div className="lg:col-span-2">
          <AiChatBox analysisData={{
            video_type: videoType,
            video_summary: videoSummary,
            content_comment_comparison: contentCommentComparison,
            clusters,
            controversies,
            stance_stats: stats,
            cleaning_summary: cleaningSummary,
          }} />
        </div>
      </div>
    </div>
  );
}
