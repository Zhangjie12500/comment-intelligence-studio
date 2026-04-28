import { useState } from 'react';
import { Clock, Copy, CheckCheck, Loader2, AlertTriangle, WifiOff } from 'lucide-react';
import Card from './Card';

const STATUS_MAP = {
  pending:   { label: '等待中',   color: '#6B7280', bg: '#F3F4F6', border: '#E5E7EB' },
  fetching:  { label: '抓取中',   color: '#1D4ED8', bg: '#DBEAFE', border: '#BFDBFE' },
  cleaning:  { label: '清洗中',   color: '#6D28D9', bg: '#EDE9FE', border: '#DDD6FE' },
  analyzing: { label: '分析中',   color: '#6D28D9', bg: '#EDE9FE', border: '#DDD6FE' },
  exporting: { label: '导出中',   color: '#B45309', bg: '#FEF3C7', border: '#FDE68A' },
  done:      { label: '已完成',   color: '#047857', bg: '#D1FAE5', border: '#A7F3D0' },
  failed:    { label: '失败',     color: '#B91C1C', bg: '#FEE2E2', border: '#FECACA' },
};

export function StatusBadge({ status, size = 'sm' }) {
  const s = STATUS_MAP[status] || STATUS_MAP.pending;
  const padding = size === 'sm' ? 'px-2 py-0.5' : 'px-3 py-1';
  const fontSize = size === 'sm' ? 'text-xs' : 'text-sm';
  
  return (
    <span 
      className={`inline-flex items-center rounded-md font-medium ${padding} ${fontSize}`}
      style={{ 
        background: s.bg, 
        border: `1px solid ${s.border}`, 
        color: s.color 
      }}
    >
      {status === 'fetching' && <Loader2 size={10} className="mr-1 animate-spin" />}
      {status === 'analyzing' && <Loader2 size={10} className="mr-1 animate-spin" />}
      {status === 'exporting' && <Loader2 size={10} className="mr-1 animate-spin" />}
      {s.label}
    </span>
  );
}

export default function JobStatusPanel({ job }) {
  const [copied, setCopied] = useState(false);

  if (!job) {
    return (
      <Card>
        <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
          <div className="flex items-center gap-2">
            <Clock size={15} className="text-[#9CA3AF]" />
            <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
              任务状态
            </span>
          </div>
        </div>
        <div className="p-8 flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ background: '#F3F4F6', border: '1px dashed #E5E7EB' }}>
            <Clock size={22} className="text-[#D1D5DB]" />
          </div>
          <p className="text-sm font-medium text-[#6B7280]">暂无任务</p>
          <p className="text-xs text-[#9CA3AF]">提交链接后开始分析</p>
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
  const progressPercent = tasks.length > 0 ? (doneCount / tasks.length) * 100 : 0;

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <div className="flex items-center gap-2">
          <Clock size={15} className="text-[#9CA3AF]" />
          <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
            任务状态
          </span>
        </div>
      </div>

      <div className="p-5 flex flex-col gap-4">
        {/* Job error */}
        {job.error && (
          <div className="flex items-start gap-3 p-3 rounded-lg"
            style={{ background: '#FEF2F2', border: '1px solid #FECACA' }}>
            <AlertTriangle size={14} className="text-[#DC2626] mt-0.5 flex-shrink-0" />
            <p className="text-xs text-[#991B1B] leading-relaxed">{job.error}</p>
          </div>
        )}

        {/* Job ID */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-[#9CA3AF]">Job ID</span>
          <div className="flex items-center gap-2">
            <code 
              className="text-xs px-2.5 py-1 rounded-md font-mono max-w-[120px] truncate block"
              style={{ background: '#F3F4F6', color: '#4B5563', border: '1px solid #E5E7EB' }}
              title={job.job_id}
            >
              {job.job_id}
            </code>
            <button 
              onClick={copyId} 
              className="p-1.5 rounded-md transition-colors hover:bg-[#F3F4F6] border border-transparent hover:border-[#E5E7EB]"
            >
              {copied
                ? <CheckCheck size={13} className="text-[#059669]" />
                : <Copy size={13} className="text-[#9CA3AF]" />}
            </button>
          </div>
        </div>

        {/* Overall status */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-[#9CA3AF]">总体状态</span>
          <StatusBadge status={job.status} />
        </div>

        {/* Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#9CA3AF]">进度</span>
            <span className="text-xs font-medium" style={{ color: failCount > 0 ? '#DC2626' : '#374151' }}>
              {doneCount}/{tasks.length} 完成
              {failCount > 0 && <span className="ml-1">· {failCount} 失败</span>}
            </span>
          </div>
          <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: '#F3F4F6' }}>
            <div 
              className="h-full rounded-full transition-all duration-500 ease-out"
              style={{
                width: `${progressPercent}%`,
                background: failCount > 0
                  ? 'linear-gradient(90deg, #10B981, #DC2626)'
                  : '#10B981',
              }}
            />
          </div>
        </div>

        {/* Timestamps */}
        <div className="space-y-2 pt-1">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#9CA3AF]">创建时间</span>
            <span className="text-xs font-mono" style={{ color: '#6B7280' }}>
              {job.created_at ? fmtTime(job.created_at) : '—'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#9CA3AF]">更新时间</span>
            <span className="text-xs font-mono" style={{ color: '#6B7280' }}>
              {job.updated_at ? fmtTime(job.updated_at) : '—'}
            </span>
          </div>
        </div>

        {/* Polling hint */}
        {!allDone && job.status === 'running' && (
          <div className="flex items-center gap-2 pt-1">
            <Loader2 size={11} className="text-[#2563EB] animate-spin" />
            <span className="text-xs" style={{ color: '#9CA3AF' }}>每 2 秒自动刷新</span>
          </div>
        )}
      </div>
    </Card>
  );
}

function fmtTime(iso) {
  try {
    const d = new Date(iso);
    return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
  } catch { return iso; }
}
