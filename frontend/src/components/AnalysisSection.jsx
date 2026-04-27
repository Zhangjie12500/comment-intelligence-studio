import { BarChart2, TrendingUp, Users, MessageSquare, Inbox } from 'lucide-react';
import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';
import Card from './Card';

// ──────────────────────────────────────────────────
// 1. Summary
// ──────────────────────────────────────────────────
function SummaryCard({ summary }) {
  return (
    <Card>
      <div className="px-4 pt-4 pb-3 border-b border-white/8">
        <div className="flex items-center gap-2">
          <Inbox size={13} className="text-white/40" />
          <span className="text-xs font-medium text-white/60 tracking-wide uppercase">分析总结</span>
        </div>
      </div>
      <div className="p-4">
        {summary ? (
          <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.72)' }}>
            {summary}
          </p>
        ) : (
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.2)' }}>暂无分析结果</p>
        )}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────────
// 2. Stance Pie Chart
// ──────────────────────────────────────────────────
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
    const LABEL_MAP = { support: '支持', oppose: '反对', neutral: '中立', joke: '调侃', question: '提问' };
    const COLOR_MAP = { support: '#4ade80', oppose: '#f87171', neutral: '#71717a', joke: '#c084fc', question: '#60a5fa' };

    const data = Object.entries(stats)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({
        name: LABEL_MAP[k] || k,
        value: v,
        itemStyle: { color: COLOR_MAP[k] || '#71717a' },
      }));

    inst.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(10,10,10,0.92)',
        borderColor: 'rgba(255,255,255,0.08)',
        textStyle: { color: '#fafafa', fontSize: 12 },
        formatter: p => `${p.name}：${p.value} (${total > 0 ? ((p.value / total) * 100).toFixed(1) : 0}%)`,
      },
      legend: {
        bottom: 4,
        textStyle: { color: 'rgba(255,255,255,0.45)', fontSize: 11 },
        icon: 'circle',
        itemWidth: 7,
        itemHeight: 7,
        itemGap: 14,
      },
      series: [{
        type: 'pie',
        radius: ['42%', '66%'],
        center: ['50%', '46%'],
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
      <div className="px-4 pt-4 pb-3 border-b border-white/8">
        <div className="flex items-center gap-2">
          <BarChart2 size={13} className="text-white/40" />
          <span className="text-xs font-medium text-white/60 tracking-wide uppercase">立场分布</span>
        </div>
      </div>
      <div className="p-4">
        {hasData ? (
          <div ref={chartRef} style={{ width: '100%', height: 200 }} />
        ) : (
          <div className="h-[200px] flex items-center justify-center">
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>暂无数据</span>
          </div>
        )}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────────
// 3. Top Influence Comments
// ──────────────────────────────────────────────────
const STANCE_COLOR = {
  support:  { color: '#4ade80', bg: 'rgba(74,222,128,0.08)',  border: 'rgba(74,222,128,0.18)' },
  oppose:   { color: '#f87171', bg: 'rgba(248,113,113,0.08)', border: 'rgba(248,113,113,0.18)' },
  question: { color: '#60a5fa', bg: 'rgba(96,165,250,0.08)',  border: 'rgba(96,165,250,0.18)' },
  joke:     { color: '#c084fc', bg: 'rgba(192,132,252,0.08)', border: 'rgba(192,132,252,0.18)' },
  neutral:  { color: '#71717a', bg: 'rgba(113,113,122,0.08)', border: 'rgba(113,113,122,0.15)' },
};
const STANCE_LABEL = { support: '支持', oppose: '反对', question: '提问', joke: '调侃', neutral: '中立' };

function TopCommentsCard({ comments }) {
  const list = comments && comments.length > 0 ? comments : null;

  return (
    <Card>
      <div className="px-4 pt-4 pb-3 border-b border-white/8">
        <div className="flex items-center gap-2">
          <TrendingUp size={13} className="text-white/40" />
          <span className="text-xs font-medium text-white/60 tracking-wide uppercase">高影响评论 Top 10</span>
        </div>
      </div>
      <div className="p-4 flex flex-col gap-2">
        {!list ? (
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>暂无数据</p>
        ) : (
          list.map((c, i) => {
            const sc = STANCE_COLOR[c.stance] || STANCE_COLOR.neutral;
            const label = STANCE_LABEL[c.stance] || '中立';
            return (
              <div key={i} className="flex gap-3 p-3 rounded-lg transition-colors duration-150 hover:bg-white/5"
                style={{ background: 'rgba(0,0,0,0.15)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div className="flex flex-col items-center gap-1 min-w-[28px]">
                  <span className="text-xs font-mono font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>#{i + 1}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded text-[10px] font-medium"
                    style={{ background: sc.bg, border: `1px solid ${sc.border}`, color: sc.color }}>
                    {label}
                  </span>
                </div>
                <div className="flex-1 min-w-0 flex flex-col gap-1.5">
                  <p className="text-xs leading-relaxed line-clamp-2" style={{ color: 'rgba(255,255,255,0.72)' }}>
                    {c.text || '—'}
                  </p>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.3)' }}>
                      {c.user || '匿名'}
                    </span>
                    {c.like > 0 && (
                      <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.35)' }}>
                        👍 {Number(c.like).toLocaleString()}
                      </span>
                    )}
                    {c.reply_count > 0 && (
                      <span className="text-[10px]" style={{ color: 'rgba(255,255,255,0.35)' }}>
                        💬 {c.reply_count}
                      </span>
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
// 4. Clusters
// ──────────────────────────────────────────────────
const CLUSTER_COLORS = ['#c9a87c', '#60a5fa', '#4ade80', '#fbbf24', '#c084fc', '#f87171'];

function ClustersCard({ clusters }) {
  const list = clusters && clusters.length > 0 ? clusters : null;

  return (
    <Card>
      <div className="px-4 pt-4 pb-3 border-b border-white/8">
        <div className="flex items-center gap-2">
          <Users size={13} className="text-white/40" />
          <span className="text-xs font-medium text-white/60 tracking-wide uppercase">观点聚类</span>
        </div>
      </div>
      <div className="p-4 flex flex-col gap-2">
        {!list ? (
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>暂无数据</p>
        ) : (
          list.map((cl, i) => {
            const color = CLUSTER_COLORS[i % CLUSTER_COLORS.length];
            const reps = (cl.representative_comments || []).slice(0, 3);
            return (
              <div key={i} className="p-3 rounded-lg"
                style={{ background: 'rgba(0,0,0,0.15)', border: `1px solid ${color}18` }}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                  <span className="text-xs font-medium" style={{ color }}>{cl.title || `聚类 ${i + 1}`}</span>
                  <span className="text-xs ml-auto" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    {cl.count || 0} 条
                  </span>
                </div>
                {(cl.keywords || []).length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {(cl.keywords || []).slice(0, 5).map((kw, ki) => (
                      <span key={ki} className="text-[10px] px-1.5 py-0.5 rounded"
                        style={{ background: `${color}12`, color: `${color}aa`, border: `1px solid ${color}22` }}>
                        {kw}
                      </span>
                    ))}
                  </div>
                )}
                {reps.length > 0 && (
                  <div className="flex flex-col gap-1">
                    {reps.map((rep, ri) => (
                      <p key={ri} className="text-[11px] leading-relaxed line-clamp-1"
                        style={{ color: 'rgba(255,255,255,0.4)', paddingLeft: '0.5rem', borderLeft: `2px solid ${color}30` }}>
                        {rep.text || '—'}
                        {rep.like > 0 && <span className="ml-2" style={{ color: 'rgba(255,255,255,0.2)' }}>👍{Number(rep.like).toLocaleString()}</span>}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}

// ──────────────────────────────────────────────────
// 5. Controversies
// ──────────────────────────────────────────────────
function ControversiesCard({ controversies }) {
  const list = controversies && controversies.length > 0 ? controversies : null;

  return (
    <Card>
      <div className="px-4 pt-4 pb-3 border-b border-white/8">
        <div className="flex items-center gap-2">
          <MessageSquare size={13} className="text-white/40" />
          <span className="text-xs font-medium text-white/60 tracking-wide uppercase">争议点</span>
        </div>
      </div>
      <div className="p-4 flex flex-col gap-2">
        {!list ? (
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>暂无数据</p>
        ) : list.length === 0 ? (
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.2)' }}>暂无明显争议</p>
        ) : (
          list.map((co, i) => (
            <div key={i} className="p-3 rounded-lg"
              style={{ background: 'rgba(251,191,36,0.04)', border: '1px solid rgba(251,191,36,0.12)' }}>
              <p className="text-xs font-medium mb-1" style={{ color: 'rgba(251,191,36,0.85)' }}>
                {co.title || `争议点 ${i + 1}`}
              </p>
              {co.description && (
                <p className="text-xs leading-relaxed mb-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
                  {co.description}
                </p>
              )}
              {(co.sample_comments || []).length > 0 && (
                <div className="flex flex-col gap-0.5">
                  {(co.sample_comments || []).slice(0, 2).map((s, ri) => (
                    <p key={ri} className="text-[11px] line-clamp-1"
                      style={{ color: 'rgba(255,255,255,0.3)', paddingLeft: '0.5rem', borderLeft: '2px solid rgba(251,191,36,0.2)' }}>
                      · {String(s).slice(0, 80)}
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
// Main: ordered analysis section
// ──────────────────────────────────────────────────
export default function AnalysisSection({ report, job }) {
  // Find first done task with analysis data
  const task = (job?.tasks || [])
    .filter(t => t.status === 'done')
    .sort((a, b) => (b.cleaned_count || 0) - (a.cleaned_count || 0))[0];

  const stats = task?.stance_stats || report?.stance_stats || null;
  const topComments = task?.top_influence_comments || report?.top_influence_comments || null;
  const clusters = task?.clusters || report?.clusters || null;
  const controversies = task?.controversies || report?.controversies || null;
  const summary = task?.summary || report?.summary || null;

  const hasAny = !!(stats || topComments || clusters || controversies || summary);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.06)' }} />
        <span className="text-[10px] tracking-widest text-white/20 uppercase">分析结果</span>
        <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.06)' }} />
      </div>

      {!hasAny ? (
        <Card>
          <div className="p-8 flex flex-col items-center gap-3">
            <div className="w-10 h-10 rounded-full flex items-center justify-center"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px dashed rgba(255,255,255,0.07)' }}>
              <BarChart2 size={18} className="text-white/15" />
            </div>
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.2)' }}>暂无分析结果</p>
            <p className="text-xs" style={{ color: 'rgba(255,255,255,0.1)' }}>提交链接并等待任务完成后即可查看</p>
          </div>
        </Card>
      ) : (
        <>
          {summary && <SummaryCard summary={summary} />}
          <StanceChartCard stats={stats} />
          <TopCommentsCard comments={topComments} />
          <ClustersCard clusters={clusters} />
          <ControversiesCard controversies={controversies} />
        </>
      )}
    </div>
  );
}
