import { Tag, Info } from 'lucide-react';
import Card from './Card';

// Video type colors
const TYPE_COLORS = {
  '测评类': { bg: '#DBEAFE', color: '#1D4ED8', border: '#BFDBFE' },
  '多商品对比类': { bg: '#E0E7FF', color: '#4338CA', border: '#C7D2FE' },
  '攻略类': { bg: '#D1FAE5', color: '#047857', border: '#A7F3D0' },
  '科普类': { bg: '#FEF3C7', color: '#B45309', border: '#FDE68A' },
  '娱乐类': { bg: '#FCE7F3', color: '#BE185D', border: '#FBCFE8' },
  '观点类': { bg: '#E5E7EB', color: '#374151', border: '#D1D5DB' },
  '带货类': { bg: '#FEE2E2', color: '#B91C1C', border: '#FECACA' },
  'vlog类': { bg: '#F3E8FF', color: '#7C3AED', border: '#DDD6FE' },
  '其他': { bg: '#F3F4F6', color: '#6B7280', border: '#E5E7EB' },
};

function getTypeStyle(typeName) {
  return TYPE_COLORS[typeName] || TYPE_COLORS['其他'];
}

export default function VideoTypeCard({ videoType }) {
  // Handle missing or invalid data gracefully
  if (!videoType || !videoType.primary) {
    return (
      <Card>
        <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
          <div className="flex items-center gap-2">
            <Tag size={15} className="text-[#9CA3AF]" />
            <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
              视频类型判断
            </span>
          </div>
        </div>
        <div className="p-5">
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-3"
              style={{ background: '#F3F4F6', border: '1px dashed #E5E7EB' }}>
              <Tag size={22} className="text-[#D1D5DB]" />
            </div>
            <p className="text-sm font-medium text-[#6B7280]">暂未识别视频类型</p>
            <p className="text-xs text-[#9CA3AF] mt-1">
              提交视频链接并等待分析完成后即可查看
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const primary = videoType.primary || '其他';
  const secondary = videoType.secondary || '';
  const confidence = videoType.confidence || 0;
  const reason = videoType.reason || '';
  const primaryStyle = getTypeStyle(primary);
  const secondaryStyle = secondary ? getTypeStyle(secondary) : null;
  const confidencePercent = Math.round(confidence * 100);

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <div className="flex items-center gap-2">
          <Tag size={15} className="text-[#9CA3AF]" />
          <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
            视频类型判断
          </span>
        </div>
      </div>

      <div className="p-5 flex flex-col gap-5">
        {/* Type badges */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Primary type */}
          <span 
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold transition-all duration-180"
            style={{
              background: primaryStyle.bg,
              color: primaryStyle.color,
              border: `1px solid ${primaryStyle.border}`,
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            主 {primary}
          </span>

          {/* Secondary type */}
          {secondary && secondaryStyle && (
            <span 
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-180"
              style={{
                background: secondaryStyle.bg,
                color: secondaryStyle.color,
                border: `1px solid ${secondaryStyle.border}`,
              }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              辅 {secondary}
            </span>
          )}
        </div>

        {/* Confidence bar */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-[#6B7280]">置信度</span>
            <span className="text-sm font-semibold" style={{ color: primaryStyle.color }}>
              {confidencePercent}%
            </span>
          </div>
          <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: '#F3F4F6' }}>
            <div 
              className="h-full rounded-full transition-all duration-500"
              style={{ 
                width: `${confidencePercent}%`,
                background: confidencePercent >= 70 
                  ? '#10B981' 
                  : confidencePercent >= 40 
                    ? '#F59E0B' 
                    : '#6B7280'
              }}
            />
          </div>
        </div>

        {/* Reason */}
        {reason && (
          <div 
            className="p-3 rounded-lg flex items-start gap-2"
            style={{ background: '#F9FAFB', border: '1px solid #E5E7EB' }}
          >
            <Info size={14} className="text-[#9CA3AF] flex-shrink-0 mt-0.5" />
            <p className="text-xs leading-relaxed" style={{ color: '#6B7280' }}>
              {reason}
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
