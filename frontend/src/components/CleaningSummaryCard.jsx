import { BarChart3, CheckCircle2, XCircle, Copy, Filter } from 'lucide-react';
import Card from './Card';

export default function CleaningSummaryCard({ cleaningSummary }) {
  // Handle missing or invalid data gracefully
  if (!cleaningSummary) {
    return (
      <Card>
        <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
          <div className="flex items-center gap-2">
            <Filter size={15} className="text-[#9CA3AF]" />
            <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
              数据清洗概览
            </span>
          </div>
        </div>
        <div className="p-5">
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-3"
              style={{ background: '#F3F4F6', border: '1px dashed #E5E7EB' }}>
              <BarChart3 size={22} className="text-[#D1D5DB]" />
            </div>
            <p className="text-sm font-medium text-[#6B7280]">暂未生成清洗统计</p>
            <p className="text-xs text-[#9CA3AF] mt-1">
              提交视频链接并等待分析完成后即可查看
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const originalCount = cleaningSummary.original_count || 0;
  const cleanedCount = cleaningSummary.cleaned_count || 0;
  const removedCount = cleaningSummary.removed_count || 0;
  const lowInfoCount = cleaningSummary.low_info_count || 0;
  const duplicateCount = cleaningSummary.duplicate_count || 0;
  const strategy = cleaningSummary.strategy || '';

  // Calculate percentages
  const cleanedRate = originalCount > 0 ? Math.round((cleanedCount / originalCount) * 100) : 0;
  const removedRate = originalCount > 0 ? Math.round((removedCount / originalCount) * 100) : 0;

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <div className="flex items-center gap-2">
          <Filter size={15} className="text-[#9CA3AF]" />
          <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
            数据清洗概览
          </span>
        </div>
      </div>

      <div className="p-5 flex flex-col gap-4">
        {/* Main stats row */}
        <div className="grid grid-cols-3 gap-3">
          {/* Original count */}
          <div className="p-3 rounded-lg text-center" style={{ background: '#F9FAFB', border: '1px solid #F3F4F6' }}>
            <div className="text-2xl font-bold" style={{ color: '#374151' }}>
              {originalCount}
            </div>
            <div className="text-xs text-[#9CA3AF] mt-1">原始评论</div>
          </div>

          {/* Cleaned count */}
          <div className="p-3 rounded-lg text-center" style={{ background: '#F0FDF4', border: '1px solid #A7F3D0' }}>
            <div className="text-2xl font-bold" style={{ color: '#059669' }}>
              {cleanedCount}
            </div>
            <div className="text-xs text-[#9CA3AF] mt-1">保留</div>
          </div>

          {/* Removed count */}
          <div className="p-3 rounded-lg text-center" style={{ background: '#FEF2F2', border: '1px solid #FECACA' }}>
            <div className="text-2xl font-bold" style={{ color: '#DC2626' }}>
              {removedCount}
            </div>
            <div className="text-xs text-[#9CA3AF] mt-1">删除</div>
          </div>
        </div>

        {/* Progress bar */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-[#6B7280]">保留率</span>
            <span className="text-xs font-medium" style={{ color: cleanedRate >= 70 ? '#059669' : '#DC2626' }}>
              {cleanedRate}% 保留
            </span>
          </div>
          <div className="w-full h-2 rounded-full overflow-hidden flex" style={{ background: '#F3F4F6' }}>
            <div 
              className="h-full transition-all duration-500"
              style={{ width: `${cleanedRate}%`, background: '#10B981' }}
            />
            <div 
              className="h-full transition-all duration-500"
              style={{ width: `${removedRate}%`, background: '#EF4444' }}
            />
          </div>
        </div>

        {/* Detail breakdown */}
        <div className="flex flex-wrap gap-2">
          <div 
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-all duration-180"
            style={{ background: '#FEF3C7', color: '#B45309', border: '1px solid #FDE68A' }}
          >
            <BarChart3 size={12} />
            低信息密度: {lowInfoCount}
          </div>
          <div 
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-all duration-180"
            style={{ background: '#E0E7FF', color: '#4338CA', border: '1px solid #C7D2FE' }}
          >
            <Copy size={12} />
            重复评论: {duplicateCount}
          </div>
        </div>

        {/* Strategy */}
        {strategy && (
          <div 
            className="p-3 rounded-lg text-xs leading-relaxed"
            style={{ background: '#F3F4F6', color: '#4B5563', border: '1px solid #E5E7EB' }}
          >
            <span className="font-medium">清洗策略：</span>{strategy}
          </div>
        )}
      </div>
    </Card>
  );
}
