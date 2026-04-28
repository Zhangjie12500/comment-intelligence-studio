import { useState, useMemo } from 'react';
import { Play, ExternalLink , RefreshCw, MessageSquare, Info } from 'lucide-react';
import Card from './Card';

// ──────────────────────────────────────────────────
// Platform detection
// ──────────────────────────────────────────────────
function detectPlatform(url) {
  if (!url) return null;
  const lower = url.toLowerCase();
  if (lower.includes('bilibili.com') || lower.includes('b23.tv')) return 'bilibili';
  if (lower.includes('youtube.com') || lower.includes('youtu.be')) return 'youtube';
  return null;
}

const PLATFORM_INFO = {
  bilibili: { label: 'Bilibili', color: '#23aaf2', bg: '#e6f4fc' },
  youtube: { label: 'YouTube', color: '#ff0000', bg: '#fee8e8' },
};

// ──────────────────────────────────────────────────
// Toggle component
// ──────────────────────────────────────────────────
function Toggle({ label, sub, value, onChange, icon, disabled }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-[#9CA3AF]">{icon}</span>
        <span className="text-sm text-[#4B5563]">{label}</span>
        <span className="text-xs text-[#D1D5DB]">({sub})</span>
      </div>
      <button
        type="button"
        onClick={() => !disabled && onChange(v => !v)}
        disabled={disabled}
        className="w-10 h-5.5 rounded-full relative transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
        style={{
          background: value ? '#2563EB' : '#E5E7EB',
          border: `1px solid ${value ? '#2563EB' : '#D1D5DB'}`,
        }}
      >
        <span
          className="absolute top-0.5 w-4 h-4 rounded-full transition-all duration-200"
          style={{
            background: '#FFFFFF',
            left: value ? 'calc(100% - 18px)' : '3px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
          }}
        />
      </button>
    </div>
  );
}

// ──────────────────────────────────────────────────
// Example links
// ──────────────────────────────────────────────────
const EXAMPLES = [
  { url: 'https://www.bilibili.com/video/BV1GJ411x7h7', platform: 'bilibili' },
  { url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', platform: 'youtube' },
];

// ──────────────────────────────────────────────────
// Main InputPanel
// ──────────────────────────────────────────────────
export default function InputPanel({ onSubmit, isSubmitting, isPolling }) {
  const [url, setUrl] = useState('');
  const [limit, setLimit] = useState(50);
  const [forceRefresh, setForceRefresh] = useState(false);
  const [includeReplies, setIncludeReplies] = useState(true);

  const isActive = isSubmitting || isPolling;
  const platform = useMemo(() => detectPlatform(url), [url]);
  const platformInfo = platform ? PLATFORM_INFO[platform] : null;

  function handleSubmit(e) {
    e.preventDefault();
    const trimmedUrl = url.trim();
    if (!trimmedUrl) return;
    onSubmit({ 
      urls: [trimmedUrl], 
      limit, 
      force_refresh: forceRefresh, 
      include_replies: includeReplies 
    });
  }

  function handleExample(example) {
    setUrl(example.url);
  }

  function handleClear() {
    setUrl('');
  }

  const btnLabel = isSubmitting
    ? '后端启动中...'
    : isPolling
      ? '分析中...'
      : '开始分析';

  return (
    <Card>
      {/* ── Header ── */}
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <div className="flex items-center gap-2 mb-1">
        <ExternalLink size={15} className="text-[#9CA3AF]" />
          <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
            视频链接
          </span>
        </div>
        <p className="text-xs text-[#9CA3AF]">
          输入 B站 或 YouTube 视频链接
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col">
        {/* ── URL Input Area ── */}
        <div className="p-5 border-b border-[#F3F4F6]">
          <div className="relative">
            <input
              type="text"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://www.bilibili.com/video/BVxxxxxx"
              disabled={isActive}
              className="input-base pr-20"
            />
            
            {/* Platform badge */}
            {platformInfo && (
              <span 
                className="absolute right-3 top-1/2 -translate-y-1/2 tag text-xs"
                style={{ 
                  background: platformInfo.bg, 
                  color: platformInfo.color,
                  fontSize: '11px',
                  padding: '2px 8px'
                }}
              >
                {platformInfo.label}
              </span>
            )}

            {/* Clear button */}
            {url && !isActive && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-[#6B7280] transition-colors"
              >
                <span style={{ fontSize: '16px', lineHeight: 1 }}>×</span>
              </button>
            )}
          </div>

          {/* URL validation hint */}
          {url && !platform && (
            <div className="flex items-center gap-1.5 mt-2">
              <Info size={12} className="text-[#FBBF24]" />
              <span className="text-xs text-[#B45309]">
                无法识别的链接格式，请输入 B站 或 YouTube 链接
              </span>
            </div>
          )}

          {/* Example links */}
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <span className="text-xs text-[#9CA3AF]">示例：</span>
            {EXAMPLES.map((ex, i) => (
              <button
                key={i}
                type="button"
                onClick={() => handleExample(ex)}
                disabled={isActive}
                className="text-xs px-2 py-1 rounded-md border border-[#E5E7EB] text-[#6B7280] 
                  hover:border-[#2563EB] hover:text-[#2563EB] hover:bg-blue-50 transition-all duration-150
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {ex.platform === 'bilibili' ? 'B站示例' : 'YouTube示例'}
              </button>
            ))}
          </div>
        </div>

        {/* ── Parameters ── */}
        <div className="p-5 border-b border-[#F3F4F6] flex flex-col gap-4">
          {/* Comment limit */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <MessageSquare size={13} className="text-[#9CA3AF]" />
              <span className="text-sm text-[#4B5563]">评论数量</span>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={5}
                max={200}
                step={5}
                value={limit}
                onChange={e => setLimit(Number(e.target.value))}
                disabled={isActive}
                className="w-28 h-1.5 rounded-full appearance-none cursor-pointer bg-[#E5E7EB] 
                  disabled:cursor-not-allowed accent-[#2563EB]"
              />
              <span className="text-sm font-mono font-medium text-[#374151] w-10 text-right">
                {limit}
              </span>
            </div>
          </div>

          {/* Toggles */}
          <div className="flex flex-col gap-3 pt-1">
            <Toggle
              label="强制刷新"
              sub="忽略缓存"
              value={forceRefresh}
              onChange={setForceRefresh}
              icon={<RefreshCw size={12} />}
              disabled={isActive}
            />
            <Toggle
              label="包含回复"
              sub="抓取子回复"
              value={includeReplies}
              onChange={setIncludeReplies}
              icon={<MessageSquare size={12} />}
              disabled={isActive}
            />
          </div>
        </div>

        {/* ── Submit Button ── */}
        <div className="p-5">
          <button
            type="submit"
            disabled={isActive || !url.trim() || !platform}
            className="btn-primary w-full py-3 text-sm"
          >
            {isActive ? (
              <>
                <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                {btnLabel}
              </>
            ) : (
              <>
                <Play size={15} />
                {btnLabel}
              </>
            )}
          </button>
          
          {/* Hint text */}
          {!isActive && !url && (
            <p className="text-xs text-center text-[#9CA3AF] mt-3">
              输入链接后即可开始分析
            </p>
          )}
          {!isActive && url && !platform && (
            <p className="text-xs text-center text-[#B45309] mt-3">
              请输入有效的 B站 或 YouTube 链接
            </p>
          )}
        </div>
      </form>
    </Card>
  );
}
