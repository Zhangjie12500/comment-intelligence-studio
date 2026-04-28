import { 
  AlertTriangle, 
  Info, 
  Wifi, 
  WifiOff, 
  CloudOff, 
  MessageSquare, 
  BrainCircuit, 
  FileDown, 
  RefreshCw, 
  ExternalLink,
} from 'lucide-react';

// ──────────────────────────────────────────────────
// Error Types
// ──────────────────────────────────────────────────
export const ERROR_TYPES = {
  INVALID_URL: {
    title: '链接格式无效',
    description: '请检查链接格式是否正确，支持 B站 和 YouTube 视频链接。',
    icon: ExternalLink,
    suggestion: '示例：B站链接 https://www.bilibili.com/video/BVxxxxxx',
    color: '#B45309',
    bg: '#FEF3C7',
  },
  CONNECTION_FAILED: {
    title: '后端连接失败',
    description: '无法连接到分析服务，请检查后端服务是否启动。',
    icon: WifiOff,
    suggestion: '确保后端服务运行在 http://localhost:8010',
    color: '#DC2626',
    bg: '#FEE2E2',
  },
  CORS_ERROR: {
    title: '跨域请求被阻止',
    description: '浏览器安全策略阻止了请求，请检查后端 CORS 配置。',
    icon: CloudOff,
    suggestion: '后端需要配置 CORS 允许前端域名访问',
    color: '#7C3AED',
    bg: '#EDE9FE',
  },
  FETCH_FAILED: {
    title: '评论抓取失败',
    description: '无法获取视频评论，可能视频不存在或评论已关闭。',
    icon: MessageSquare,
    suggestion: '请检查视频链接是否有效，或尝试增加评论数量',
    color: '#B45309',
    bg: '#FEF3C7',
  },
  ANALYSIS_FAILED: {
    title: 'AI 分析失败',
    description: '评论分析过程中出现错误，请稍后重试。',
    icon: BrainCircuit,
    suggestion: '可以尝试减少评论数量后重试',
    color: '#DC2626',
    bg: '#FEE2E2',
  },
  PDF_EXPORT_FAILED: {
    title: 'PDF 导出失败',
    description: '生成 PDF 报告时出现问题。',
    icon: FileDown,
    suggestion: '可以尝试导出 JSON 或 Markdown 格式',
    color: '#B45309',
    bg: '#FEF3C7',
  },
  UNKNOWN: {
    title: '发生未知错误',
    description: '操作未能完成，请查看详细信息或联系开发者。',
    icon: AlertTriangle,
    suggestion: '可以尝试刷新页面后重试',
    color: '#6B7280',
    bg: '#F3F4F6',
  },
};

// Detect error type from error message
export function detectErrorType(error) {
  const msg = (error || '').toLowerCase();
  
  if (msg.includes('cors') || msg.includes('cross-origin')) return 'CORS_ERROR';
  if (msg.includes('failed to fetch') || msg.includes('network') || msg.includes('net::')) return 'CONNECTION_FAILED';
  if (msg.includes('connection refused') || msg.includes('connection failed')) return 'CONNECTION_FAILED';
  if (msg.includes('invalid') && (msg.includes('url') || msg.includes('link'))) return 'INVALID_URL';
  if (msg.includes('fetch') && (msg.includes('comment') || msg.includes('评论'))) return 'FETCH_FAILED';
  if (msg.includes('pdf') || msg.includes('export')) return 'PDF_EXPORT_FAILED';
  if (msg.includes('analysis') || msg.includes('analyze') || msg.includes('ai')) return 'ANALYSIS_FAILED';
  
  return 'UNKNOWN';
}

// ──────────────────────────────────────────────────
// Error Card Component
// ──────────────────────────────────────────────────
export function ErrorCard({ error, onRetry }) {
  const errorType = detectErrorType(error);
  const config = ERROR_TYPES[errorType] || ERROR_TYPES.UNKNOWN;
  const Icon = config.icon;

  return (
    <div 
      className="bg-white rounded-xl border border-[#E5E7EB] shadow-sm p-6 card-hover"
      style={{ borderLeft: `4px solid ${config.color}` }}
    >
      <div className="flex gap-4">
        {/* Icon */}
        <div 
          className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center"
          style={{ background: config.bg }}
        >
          <Icon size={24} style={{ color: config.color }} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-[#111827] mb-1">
            {config.title}
          </h3>
          <p className="text-sm text-[#6B7280] mb-3">
            {config.description}
          </p>
          
          {/* Suggestion */}
          <div className="flex items-start gap-2 p-3 rounded-lg" style={{ background: config.bg }}>
            <Info size={14} style={{ color: config.color }} className="flex-shrink-0 mt-0.5" />
            <p className="text-xs" style={{ color: config.color }}>
              {config.suggestion}
            </p>
          </div>

          {/* Original error message */}
          {error && (
            <p className="text-xs text-[#9CA3AF] mt-3 font-mono truncate">
              {error}
            </p>
          )}

          {/* Actions */}
          {onRetry && (
            <div className="flex gap-3 mt-4">
              <button
                onClick={onRetry}
                className="btn-primary px-4 py-2 text-sm"
              >
                <RefreshCw size={14} />
                重试
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────
// Empty State Component
// ──────────────────────────────────────────────────
export function EmptyState({ type = 'initial', onAction }) {
  if (type === 'initial') {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#9CA3AF]">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
        </div>
        <h3 className="empty-state-title">输入视频链接开始分析</h3>
        <p className="empty-state-desc">
          输入一个 B站 或 YouTube 视频链接，ViewLens 将为你生成评论洞察报告，包括情绪分析、观点聚类和争议点检测。
        </p>
        {onAction && (
          <button onClick={onAction} className="btn-primary mt-4 px-5 py-2 text-sm">
            <ExternalLink size={14} />
            立即体验
          </button>
        )}
      </div>
    );
  }

  if (type === 'insufficient') {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">
          <MessageSquare size={24} className="text-[#9CA3AF]" />
        </div>
        <h3 className="empty-state-title">评论数量不足</h3>
        <p className="empty-state-desc">
          暂时无法生成完整分析。当前抓取的评论数量不足以进行深度分析。你可以提高评论抓取数量后重试。
        </p>
        {onAction && (
          <button onClick={onAction} className="btn-primary mt-4 px-5 py-2 text-sm">
            <RefreshCw size={14} />
            重新抓取
          </button>
        )}
      </div>
    );
  }

  if (type === 'no-results') {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">
          <AlertTriangle size={24} className="text-[#FBBF24]" />
        </div>
        <h3 className="empty-state-title">暂无分析结果</h3>
        <p className="empty-state-desc">
          提交链接并等待任务完成后即可查看分析结果。
        </p>
      </div>
    );
  }

  return null;
}

// ──────────────────────────────────────────────────
// Page Level Error Banner
// ──────────────────────────────────────────────────
export function ErrorBanner({ error, onDismiss }) {
  if (!error) return null;
  
  return (
    <div 
      className="mb-6 p-4 rounded-xl border flex items-start gap-3"
      style={{ 
        background: '#FEF2F2', 
        border: '1px solid #FECACA',
      }}
    >
      <AlertTriangle size={18} className="text-[#DC2626] flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[#991B1B]">
          {error}
        </p>
      </div>
      {onDismiss && (
        <button 
          onClick={onDismiss}
          className="text-[#DC2626] hover:text-[#991B1B] transition-colors"
        >
          ×
        </button>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────
// Warning Banner (for cold start, etc.)
// ──────────────────────────────────────────────────
export function WarningBanner({ title, children, onDismiss }) {
  return (
    <div 
      className="mb-6 p-4 rounded-xl border flex items-start gap-3"
      style={{ 
        background: '#FFFBEB', 
        border: '1px solid #FDE68A',
      }}
    >
      <AlertTriangle size={18} className="text-[#D97706] flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        {title && <p className="text-sm font-medium text-[#92400E] mb-1">{title}</p>}
        <div className="text-sm text-[#B45309]">
          {children}
        </div>
      </div>
      {onDismiss && (
        <button 
          onClick={onDismiss}
          className="text-[#D97706] hover:text-[#92400E] transition-colors"
        >
          ×
        </button>
      )}
    </div>
  );
}
