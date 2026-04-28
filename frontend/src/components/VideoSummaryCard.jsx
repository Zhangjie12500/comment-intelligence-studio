import { FileText, AlertCircle, CheckCircle2, Sparkles, Lightbulb } from 'lucide-react';
import Card from './Card';

// ──────────────────────────────────────────────────
// Video Summary Card
// ──────────────────────────────────────────────────
export default function VideoSummaryCard({ videoSummary }) {
  // Handle missing or invalid data gracefully
  if (!videoSummary) {
    return (
      <Card>
        <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
          <div className="flex items-center gap-2">
            <Sparkles size={15} className="text-[#9CA3AF]" />
            <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
              视频内容摘要
            </span>
          </div>
        </div>
        <div className="p-5">
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-3"
              style={{ background: '#F3F4F6', border: '1px dashed #E5E7EB' }}>
              <FileText size={22} className="text-[#D1D5DB]" />
            </div>
            <p className="text-sm font-medium text-[#6B7280]">暂未生成视频内容摘要</p>
            <p className="text-xs text-[#9CA3AF] mt-1">
              提交视频链接并等待分析完成后即可查看
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const hasSubtitle = videoSummary.has_subtitle ?? false;
  const summary = videoSummary.summary || '';
  const keyPoints = videoSummary.key_points || [];
  const accuracyNote = videoSummary.accuracy_note || '';

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <div className="flex items-center gap-2">
          <Sparkles size={15} className="text-[#9CA3AF]" />
          <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
            视频内容摘要
          </span>
        </div>
      </div>

      <div className="p-5 flex flex-col gap-5">
        {/* ── Subtitle Status ── */}
        <div className="flex items-center gap-3">
          <div 
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: hasSubtitle ? '#D1FAE5' : '#FEF3C7' }}
          >
            {hasSubtitle ? (
              <CheckCircle2 size={16} className="text-[#059669]" />
            ) : (
              <AlertCircle size={16} className="text-[#D97706]" />
            )}
          </div>
          <div>
            <span className="text-sm font-medium" style={{ color: hasSubtitle ? '#059669' : '#B45309' }}>
              {hasSubtitle ? '已检测到字幕' : '未检测到字幕'}
            </span>
            <p className="text-xs text-[#9CA3AF]">
              {hasSubtitle 
                ? '基于字幕内容生成摘要' 
                : '基于评论和标题生成推测摘要'
              }
            </p>
          </div>
        </div>

        {/* ── Summary Text ── */}
        {summary && (
          <div className="bg-slate-50 rounded-lg p-4">
            <h4 className="text-xs font-semibold text-[#6B7280] mb-2 uppercase tracking-wide">
              内容摘要
            </h4>
            <p 
              className="text-sm leading-7 break-words whitespace-pre-wrap" 
              style={{ color: '#374151' }}
            >
              {summary}
            </p>
          </div>
        )}

        {/* ── Key Points ── */}
        {keyPoints && keyPoints.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-[#6B7280] mb-3 uppercase tracking-wide">
              关键内容
            </h4>
            <div className="flex flex-wrap gap-2">
              {keyPoints.map((point, index) => (
                <span 
                  key={index}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm
                    transition-all duration-180"
                  style={{
                    background: hasSubtitle ? '#DBEAFE' : '#FEF3C7',
                    color: hasSubtitle ? '#1D4ED8' : '#B45309',
                    border: `1px solid ${hasSubtitle ? '#BFDBFE' : '#FDE68A'}`,
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <Lightbulb size={12} />
                  {point}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ── Accuracy Note ── */}
        {accuracyNote && (
          <div 
            className="p-3 rounded-lg"
            style={{ 
              background: hasSubtitle ? '#F0FDF4' : '#FFFBEB',
              border: `1px solid ${hasSubtitle ? '#A7F3D0' : '#FDE68A'}`,
            }}
          >
            <div className="flex items-start gap-2">
              <AlertCircle 
                size={14} 
                className="flex-shrink-0 mt-0.5"
                style={{ color: hasSubtitle ? '#059669' : '#D97706' }}
              />
              <div>
                <span 
                  className="text-xs font-medium"
                  style={{ color: hasSubtitle ? '#059669' : '#B45309' }}
                >
                  {hasSubtitle ? '可靠性说明' : '准确性提示'}
                </span>
                <p className="text-xs mt-0.5" style={{ color: hasSubtitle ? '#047857' : '#92400E' }}>
                  {accuracyNote}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
