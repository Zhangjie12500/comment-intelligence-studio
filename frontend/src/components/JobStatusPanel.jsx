import { useState } from 'react';
import { Copy, CheckCheck, AlertTriangle, Loader2, Clock, CheckCircle2, XCircle } from 'lucide-react';
import Card from './Card';

const STATUS_MAP = {
  pending:   { label: '等待中',   color: '#71717a', bg: 'rgba(113,113,122,0.1)', border: 'rgba(113,113,122,0.2)' },
  fetching:  { label: '抓取中',   color: '#60a5fa', bg: 'rgba(96,165,250,0.1)', border: 'rgba(96,165,250,0.2)' },
  analyzing: { label: '分析中',   color: '#a78bfa', bg: 'rgba(167,139,250,0.1)', border: 'rgba(167,139,250,0.2)' },
  exporting: { label: '导出中',   color: '#fbbf24', bg: 'rgba(251,191,36,0.1)', border: 'rgba(251,191,36,0.2)' },
  done:      { label: '已完成',   color: '#4ade80', bg: 'rgba(74,222,128,0.1)', border: 'rgba(74,222,128,0.2)' },
  failed:    { label: '失败',     color: '#f87171', bg: 'rgba(248,113,113,0.1)', border: 'rgba(248,113,113,0.2)' },
};

export default function JobStatusPanel({ job }) {
  const [copied, setCopied] = useState(false);

  if (!job) {
    return (
      <Card>
        <div className="px-4 pt-4 pb-3 border-b border-white/8">
          <div className="flex items-center gap-2">
            <Clock size={14} className="text-white/40" />
            <span className="text-xs font-medium text-white/60 tracking-wide uppercase">任务状态</span>
          </div>
        </div>
        <div className="p-8 flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px dashed rgba(255,255,255,0.08)' }}>
            <Clock size={18} className="text-white/20" />
          </div>
          <p className="text-xs text-white/30">暂无任务</p>
          <p className="text-xs text-white/20">提交链接后开始分析</p>
        </div>
      </Card>
    );
  }

  function copyId() {
    navigator.clipboard.writeText(job.job_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const tasks = job.tasks || [];
  const doneCount = tasks.filter(t => t.status === 'done').length;
  const failCount = tasks.filter(t => t.status === 'failed').length;
  const allDone = tasks.length > 0 && tasks.every(t => t.status === 'done' || t.status === 'failed');

  return (
    <Card>
      <div className="px-4 pt-4 pb-3 border-b border-white/8">
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-white/40" />
          <span className="text-xs font-medium text-white/60 tracking-wide uppercase">任务状态</span>
        </div>
      </div>
      <div className="p-4 flex flex-col gap-3">
        {/* job error */}
        {job.error && (
          <div className="flex items-start gap-2 p-3 rounded-lg"
            style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)' }}>
            <AlertTriangle size={13} className="text-red-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-red-400 leading-relaxed">{job.error}</p>
          </div>
        )}

        {/* job id */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-white/30">Job ID</span>
          <div className="flex items-center gap-1.5">
            <code className="text-xs px-2 py-0.5 rounded-md font-mono"
              style={{ background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.6)', border: '1px solid rgba(255,255,255,0.08)' }}>
              {job.job_id}
            </code>
            <button onClick={copyId} className="p-1 rounded transition-colors duration-150 hover:bg-white/5"
              style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
              {copied
                ? <CheckCheck size={12} className="text-green-400" />
                : <Copy size={12} className="text-white/30" />}
            </button>
          </div>
        </div>

        {/* overall status */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-white/30">总体状态</span>
          <StatusBadge status={job.status} />
        </div>

        {/* progress */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-white/30">进度</span>
          <span className="text-xs" style={{ color: 'rgba(255,255,255,0.45)' }}>
            {doneCount}/{tasks.length} 完成
            {failCount > 0 && <span className="text-red-400"> · {failCount} 失败</span>}
          </span>
        </div>
        {tasks.length > 0 && (
          <div className="w-full h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <div className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${(doneCount / tasks.length) * 100}%`,
                background: failCount > 0
                  ? 'linear-gradient(90deg, rgba(74,222,128,0.6), rgba(248,113,113,0.6))'
                  : 'rgba(74,222,128,0.6)',
              }} />
          </div>
        )}

        {/* timestamps */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-white/30">创建时间</span>
          <span className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.4)' }}>
            {job.created_at ? fmtTime(job.created_at) : '—'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-white/30">更新时间</span>
          <span className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.4)' }}>
            {job.updated_at ? fmtTime(job.updated_at) : '—'}
          </span>
        </div>

        {/* polling hint */}
        {!allDone && job.status === 'running' && (
          <div className="flex items-center gap-1.5 mt-1">
            <Loader2 size={10} className="text-blue-400 animate-spin" />
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.25)' }}>每 2 秒自动刷新</span>
          </div>
        )}
      </div>
    </Card>
  );
}

export function StatusBadge({ status }) {
  const s = STATUS_MAP[status] || STATUS_MAP.pending;
  return (
    <span className="text-xs px-2 py-0.5 rounded-md font-medium"
      style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.color }}>
      {s.label}
    </span>
  );
}

function fmtTime(iso) {
  try {
    const d = new Date(iso);
    return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
  } catch { return iso; }
}
