import { BarChart2, Lightbulb, AlertCircle, CheckCircle2 } from 'lucide-react';
import Card from './Card';
import HeatmapChart from './HeatmapChart';

// Chart type recommendations by video type
const CHART_TYPE_COLORS = {
  'heatmap': { bg: '#FEE2E2', color: '#B91C1C', border: '#FECACA' },
  '高频问题卡片 + 关键词云': { bg: '#FEF3C7', color: '#B45309', border: '#FDE68A' },
  '知识点关注度 + 争议点列表': { bg: '#DBEAFE', color: '#1D4ED8', border: '#BFDBFE' },
  '情绪分布 + 热梗词云': { bg: '#FCE7F3', color: '#BE185D', border: '#FBCFE8' },
  '观点聚类 + 立场分布': { bg: '#E5E7EB', color: '#374151', border: '#D1D5DB' },
  '购买意向分析': { bg: '#D1FAE5', color: '#047857', border: '#A7F3D0' },
  '情感互动分析 + 社区氛围图': { bg: '#F3E8FF', color: '#7C3AED', border: '#DDD6FE' },
  '立场分布 + 观点聚类': { bg: '#E0E7FF', color: '#4338CA', border: '#C7D2FE' },
};

function getChartTypeStyle(chartType) {
  // Try exact match first
  if (CHART_TYPE_COLORS[chartType]) {
    return CHART_TYPE_COLORS[chartType];
  }
  // Try partial match
  for (const [key, value] of Object.entries(CHART_TYPE_COLORS)) {
    if (chartType && chartType.includes(key.split(' ')[0])) {
      return value;
    }
  }
  return { bg: '#F3F4F6', color: '#6B7280', border: '#E5E7EB' };
}

export default function VisualizationCard({ vizRecommendation, heatmapData }) {
  // Handle missing or invalid data gracefully
  if (!vizRecommendation || !vizRecommendation.chart_type) {
    return (
      <Card>
        <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
          <div className="flex items-center gap-2">
            <BarChart2 size={15} className="text-[#9CA3AF]" />
            <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
              推荐可视化方式
            </span>
          </div>
        </div>
        <div className="p-5">
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-3"
              style={{ background: '#F3F4F6', border: '1px dashed #E5E7EB' }}>
              <BarChart2 size={22} className="text-[#D1D5DB]" />
            </div>
            <p className="text-sm font-medium text-[#6B7280]">暂无可视化推荐</p>
            <p className="text-xs text-[#9CA3AF] mt-1">
              提交视频链接并等待分析完成后即可查看
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const chartType = vizRecommendation.chart_type || '';
  const reason = vizRecommendation.reason || '';
  const dataStatus = vizRecommendation.data_status || 'insufficient';
  const fallback = vizRecommendation.fallback || '';
  const isReady = dataStatus === 'ready';
  
  const chartStyle = getChartTypeStyle(chartType);

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <div className="flex items-center gap-2">
          <BarChart2 size={15} className="text-[#9CA3AF]" />
          <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
            推荐可视化方式
          </span>
        </div>
      </div>

      <div className="p-5 flex flex-col gap-5">
        {/* Chart Type Badge - Prominent display */}
        <div className="flex items-center gap-3">
          <span 
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-base font-bold transition-all duration-180"
            style={{
              background: chartStyle.bg,
              color: chartStyle.color,
              border: `2px solid ${chartStyle.border}`,
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = `0 4px 12px ${chartStyle.color}20`;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <BarChart2 size={20} />
            {chartType}
          </span>
          
          {/* Data Status Badge */}
          <span 
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium"
            style={{
              background: isReady ? '#D1FAE5' : '#FEE2E2',
              color: isReady ? '#047857' : '#B91C1C',
              border: `1px solid ${isReady ? '#A7F3D0' : '#FECACA'}`,
            }}
          >
            {isReady ? (
              <>
                <CheckCircle2 size={12} />
                数据充足
              </>
            ) : (
              <>
                <AlertCircle size={12} />
                数据不足
              </>
            )}
          </span>
        </div>

        {/* Reason */}
        {reason && (
          <div 
            className="p-4 rounded-lg"
            style={{ background: '#F9FAFB', border: '1px solid #E5E7EB' }}
          >
            <div className="flex items-start gap-2">
              <Lightbulb size={14} style={{ color: '#F59E0B' }} className="flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-medium text-[#6B7280] mb-1">推荐理由</p>
                <p className="text-sm leading-relaxed" style={{ color: '#374151' }}>
                  {reason}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Fallback (only show when data is insufficient) */}
        {!isReady && fallback && (
          <div 
            className="p-4 rounded-lg"
            style={{ background: '#FFFBEB', border: '1px solid #FDE68A' }}
          >
            <div className="flex items-start gap-2">
              <AlertCircle size={14} style={{ color: '#B45309' }} className="flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-medium" style={{ color: '#B45309' }} mb-1>建议的降级方案</p>
                <p className="text-sm leading-relaxed" style={{ color: '#92400E' }}>
                  {fallback}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Quick tips for different video types */}
        <div className="text-xs text-[#9CA3AF] border-t border-[#F3F4F6] pt-3">
          <p>提示：根据视频类型自动推荐最适合的可视化方式，不同类型视频推荐不同图表</p>
        </div>

        {/* Heatmap Section - Only show when heatmap is recommended and data is available */}
        {chartType === 'heatmap' && (
          <div className="border-t border-[#F3F4F6] pt-4 mt-4">
            <HeatmapChart heatmapData={heatmapData} />
          </div>
        )}
      </div>
    </Card>
  );
}
