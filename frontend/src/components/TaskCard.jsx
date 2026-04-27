import { FileJson, FileText, FileDown, AlertTriangle } from 'lucide-react';
import { getFileUrl } from '../lib/api';
import { StatusBadge } from './JobStatusPanel';
import Card from './Card';

const PLATFORM_COLORS = {
  bilibili: '#23aaf2',
  youtube: '#ff0000',
};

export default function TaskCard({ task, jobId, index }) {
  if (!task) return null;
  const platform = task.platform || 'unknown';
  const pColor = PLATFORM_COLORS[platform] || 'rgba(255,255,255,0.4)';
  const files = task.files || {};

  return (
    <Card className="flex flex-col gap-0">
      {/* header row */}
      <div className="px-4 py-3 border-b border-white/8 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs px-1.5 py-0.5 rounded font-mono font-medium flex-shrink-0"
            style={{ background: `${pColor}18`, color: pColor, border: `1px solid ${pColor}30` }}>
            {platform === 'bilibili' ? 'B站' : platform === 'youtube' ? 'YT' : '?'}
          </span>
          <span className="text-xs font-mono text-white/40 truncate">
            {task.video_id || '—'}
          </span>
        </div>
        <StatusBadge status={task.status} />
      </div>

      {/* counts */}
      <div className="px-4 py-3 border-b border-white/8 grid grid-cols-3 gap-3">
        {[
          { label: '原始', value: task.raw_count ?? '—' },
          { label: '清洗后', value: task.cleaned_count ?? '—' },
          { label: task.source === 'fresh' ? '来源' : '来源', value: task.source === 'fresh' ? '实时' : '缓存' },
        ].map(({ label, value }) => (
          <div key={label} className="flex flex-col gap-1 p-2.5 rounded-lg"
            style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>{label}</span>
            <span className="text-sm font-medium font-mono" style={{ color: 'rgba(255,255,255,0.75)' }}>{value}</span>
          </div>
        ))}
      </div>

      {/* error */}
      {task.error && (
        <div className="px-4 py-3 flex items-start gap-2"
          style={{ background: 'rgba(248,113,113,0.07)', borderBottom: '1px solid rgba(248,113,113,0.15)' }}>
          <AlertTriangle size={12} className="text-red-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-red-400 leading-relaxed">{task.error}</p>
        </div>
      )}

      {/* downloads */}
      {(task.status === 'done') && hasDownloads(files) && (
        <div className="px-4 py-3 flex flex-wrap gap-2">
          {files.json && (
            <DownloadBtn href={getFileUrl(jobId, task.task_id, 'comments')} label="JSON" icon={<FileJson size={11} />} />
          )}
          {files.markdown && (
            <DownloadBtn href={getFileUrl(jobId, task.task_id, 'report')} label="Markdown" icon={<FileText size={11} />} />
          )}
          {files.pdf && (
            <DownloadBtn href={getFileUrl(jobId, task.task_id, 'pdf')} label="PDF" icon={<FileDown size={11} />} />
          )}
        </div>
      )}
    </Card>
  );
}

function DownloadBtn({ href, label, icon }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 hover:bg-white/10"
      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.55)' }}
    >
      {icon}
      {label}
    </a>
  );
}

function hasDownloads(files) {
  return files && (files.json || files.markdown || files.pdf);
}
