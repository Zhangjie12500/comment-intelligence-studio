import { useState } from 'react';
import { ExternalLink, RefreshCw, MessageSquare, Play, X } from 'lucide-react';
import Card from './Card';

export default function InputPanel({ onSubmit, isSubmitting, isPolling }) {
  const [urls, setUrls] = useState('');
  const [limit, setLimit] = useState(20);
  const [forceRefresh, setForceRefresh] = useState(false);
  const [includeReplies, setIncludeReplies] = useState(true);

  const isActive = isSubmitting || isPolling;

  function handleSubmit(e) {
    e.preventDefault();
    const list = urls.split('\n').map(u => u.trim()).filter(Boolean);
    if (!list.length) return;
    onSubmit({ urls: list, limit, force_refresh: forceRefresh, include_replies: includeReplies });
  }

  const btnLabel = isSubmitting
    ? '后端启动中...'
    : isPolling
      ? '分析中，请稍候...'
      : '开始分析';

  const btnBg   = isActive ? 'rgba(255,255,255,0.04)' : '#fafafa';
  const btnColor = isActive ? 'rgba(255,255,255,0.30)' : '#09090b';

  return (
    <Card className="flex flex-col">
      {/* header */}
      <div className="px-4 pt-4 pb-3 border-b border-white/8">
        <div className="flex items-center gap-2">
          <ExternalLink size={14} className="text-white/40" />
          <span className="text-xs font-medium text-white/60 tracking-wide uppercase">视频链接输入</span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col flex-1 gap-0">
        {/* textarea */}
        <div className="p-4 border-b border-white/8">
          <textarea
            value={urls}
            onChange={e => setUrls(e.target.value)}
            placeholder="粘贴 B站 / YouTube 视频链接，每行一个&#10;&#10;示例：&#10;https://www.bilibili.com/video/BV1GJ411x7h7&#10;https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            rows={7}
            disabled={isActive}
            className="w-full bg-transparent text-sm text-white/80 placeholder-white/25 resize-none outline-none leading-relaxed disabled:opacity-40"
            style={{ fontFamily: 'inherit' }}
          />
        </div>

        {/* params */}
        <div className="p-4 border-b border-white/8 flex flex-col gap-4">
          {/* limit */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <MessageSquare size={12} className="text-white/30" />
              <span className="text-xs text-white/50">评论数量</span>
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
                className="w-24 h-1 rounded-full appearance-none cursor-pointer bg-white/10 disabled:cursor-not-allowed"
              />
              <span className="text-xs font-mono text-white/70 w-8 text-right">{limit}</span>
            </div>
          </div>

          {/* toggles */}
          <div className="flex flex-col gap-2">
            <Toggle
              label="强制刷新（忽略缓存）"
              sub="force_refresh"
              value={forceRefresh}
              onChange={setForceRefresh}
              icon={<RefreshCw size={10} />}
              disabled={isActive}
            />
            <Toggle
              label="包含回复"
              sub="include_replies"
              value={includeReplies}
              onChange={setIncludeReplies}
              icon={<MessageSquare size={10} />}
              disabled={isActive}
            />
          </div>
        </div>

        {/* submit */}
        <div className="p-4 mt-auto">
          <button
            type="submit"
            disabled={isActive || !urls.trim()}
            className="w-full py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all duration-150 disabled:cursor-not-allowed"
            style={{ background: btnBg, color: btnColor }}
          >
            {isActive ? (
              <>
                <span className="w-3.5 h-3.5 rounded-full border-2 border-current border-t-transparent animate-spin" />
                {btnLabel}
              </>
            ) : (
              <>
                <Play size={13} />
                {btnLabel}
              </>
            )}
          </button>
        </div>
      </form>
    </Card>
  );
}

function Toggle({ label, value, onChange, icon, sub, disabled }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-1.5">
        <span className="text-white/30">{icon}</span>
        <span className="text-xs text-white/50">{label}</span>
        <span className="text-xs text-white/20">({sub})</span>
      </div>
      <button
        type="button"
        onClick={() => !disabled && onChange(v => !v)}
        disabled={disabled}
        className="w-9 h-5 rounded-full relative transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
        style={{
          background: value ? 'rgba(250,250,250,0.7)' : 'rgba(255,255,255,0.08)',
          border: `1px solid ${value ? 'rgba(250,250,250,0.3)' : 'rgba(255,255,255,0.1)'}`,
        }}
      >
        <span
          className="absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all duration-200"
          style={{
            background: value ? '#09090b' : 'rgba(255,255,255,0.3)',
            left: value ? 'calc(100% - 15px)' : '3px',
          }}
        />
      </button>
    </div>
  );
}
