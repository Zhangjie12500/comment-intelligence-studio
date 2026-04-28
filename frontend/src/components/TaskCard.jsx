import { FileJson, FileText, FileDown, AlertTriangle, ExternalLink } from 'lucide-react';
import { getFileUrl } from '../lib/api';
import { StatusBadge } from './JobStatusPanel';
import Card from './Card';

const PLATFORM_CONFIG = {
  bilibili: { label: 'B站', color: '#23aaf2', bg: '#e6f4fc' },
  youtube: { label: 'YouTube', color: '#ff0000', bg: '#fee8e8' },
};

export default function TaskCard({ task, jobId, index }) {
  if (!task) return null;
  
  const platform = task.platform || 'unknown';
  const pConfig = PLATFORM_CONFIG[platform] || { label: '?', color: '#6B7280', bg: '#F3F4F6' };
  const files = task.files || {};

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-[#F3F4F6] flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          {/* Platform badge */}
          <span 
            className="tag text-xs flex-shrink-0"
            style={{ 
              background: pConfig.bg, 
              color: pConfig.color,
              fontWeight: '600',
            }}
          >
            {pConfig.label}
          </span>
          
          {/* Video ID */}
          <span 
            className="text-xs font-mono text-[#6B7280] truncate" 
            title={task.video_id}
          >
            {task.video_id || '—'}
          </span>
        </div>
        
        <StatusBadge status={task.status} />
      </div>

      {/* Stats grid */}
      <div className="px-5 py-4 border-b border-[#F3F4F6]">
        <div className="grid grid-cols-3 gap-3">
          <StatItem 
            label="原始" 
            value={task.raw_count ?? '—'} 
            color="#6B7280" 
          />
          <StatItem 
            label="清洗后" 
            value={task.cleaned_count ?? '—'} 
            color="#2563EB" 
          />
          <StatItem 
            label="来源" 
            value={task.source === 'fresh' ? '实时' : '缓存'} 
            color="#10B981" 
          />
        </div>
      </div>

      {/* Error message */}
      {task.error && (
        <div 
          className="px-5 py-3 flex items-start gap-2"
          style={{ background: '#FEF2F2', borderBottom: '1px solid #FECACA' }}
        >
          <AlertTriangle size={14} className="text-[#DC2626] mt-0.5 flex-shrink-0" />
          <p className="text-xs text-[#991B1B] leading-relaxed">{task.error}</p>
        </div>
      )}

      {/* Download links */}
      {task.status === 'done' && hasDownloads(files) && (
        <div className="px-5 py-4 flex flex-wrap gap-2">
          {files.json && (
            <DownloadBtn 
              href={getFileUrl(jobId, task.task_id, 'comments')} 
              label="JSON"
              icon={<FileJson size={13} />}
            />
          )}
          {files.markdown && (
            <DownloadBtn 
              href={getFileUrl(jobId, task.task_id, 'report')} 
              label="Markdown"
              icon={<FileText size={13} />}
            />
          )}
          {files.pdf && (
            <DownloadBtn 
              href={getFileUrl(jobId, task.task_id, 'pdf')} 
              label="PDF"
              icon={<FileDown size={13} />}
            />
          )}
        </div>
      )}
    </Card>
  );
}

function StatItem({ label, value, color }) {
  return (
    <div 
      className="p-3 rounded-lg text-center"
      style={{ background: '#F9FAFB', border: '1px solid #F3F4F6' }}
    >
      <div className="text-xs text-[#9CA3AF] mb-1">{label}</div>
      <div className="text-base font-semibold font-mono" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

function DownloadBtn({ href, label, icon }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium
        transition-all duration-180 hover:-translate-y-0.5"
      style={{ 
        background: '#F3F4F6', 
        border: '1px solid #E5E7EB', 
        color: '#374151',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = '#2563EB';
        e.currentTarget.style.color = '#FFFFFF';
        e.currentTarget.style.borderColor = '#2563EB';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = '#F3F4F6';
        e.currentTarget.style.color = '#374151';
        e.currentTarget.style.borderColor = '#E5E7EB';
      }}
    >
      {icon}
      {label}
    </a>
  );
}

function hasDownloads(files) {
  return files && (files.json || files.markdown || files.pdf);
}
