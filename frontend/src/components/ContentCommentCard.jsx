import { GitCompare, Target, MessageCircle, AlertTriangle, HelpCircle } from 'lucide-react';
import Card from './Card';

export default function ContentCommentCard({ comparison }) {
  // Handle missing or invalid data gracefully
  if (!comparison || (!comparison.video_focus?.length && !comparison.audience_focus?.length)) {
    return (
      <Card>
        <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
          <div className="flex items-center gap-2">
            <GitCompare size={15} className="text-[#9CA3AF]" />
            <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
              内容-评论对照
            </span>
          </div>
        </div>
        <div className="p-5">
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-3"
              style={{ background: '#F3F4F6', border: '1px dashed #E5E7EB' }}>
              <GitCompare size={22} className="text-[#D1D5DB]" />
            </div>
            <p className="text-sm font-medium text-[#6B7280]">暂未生成内容-评论对照分析</p>
            <p className="text-xs text-[#9CA3AF] mt-1">
              提交视频链接并等待分析完成后即可查看
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const videoFocus = comparison.video_focus || [];
  const audienceFocus = comparison.audience_focus || [];
  const gapAnalysis = comparison.gap_analysis || '';
  const audienceNeeds = comparison.audience_needs || [];
  const missedTopics = comparison.missed_topics || [];

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <div className="flex items-center gap-2">
          <GitCompare size={15} className="text-[#9CA3AF]" />
          <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
            内容-评论对照
          </span>
        </div>
      </div>

      <div className="p-5 flex flex-col gap-5">
        {/* Two-column comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Video Focus */}
          <div className="p-4 rounded-lg" style={{ background: '#EFF6FF', border: '1px solid #BFDBFE' }}>
            <div className="flex items-center gap-2 mb-3">
              <Target size={14} style={{ color: '#2563EB' }} />
              <span className="text-xs font-semibold" style={{ color: '#2563EB' }}>视频关注点</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {videoFocus.length > 0 ? (
                videoFocus.map((focus, i) => (
                  <span 
                    key={i}
                    className="text-xs px-2.5 py-1 rounded-md transition-all duration-180"
                    style={{ 
                      background: '#DBEAFE', 
                      color: '#1D4ED8',
                      border: '1px solid #BFDBFE'
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.transform = 'translateY(-1px)';
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(37,99,235,0.15)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    {focus}
                  </span>
                ))
              ) : (
                <span className="text-xs text-[#9CA3AF]">暂无数据</span>
              )}
            </div>
          </div>

          {/* Audience Focus */}
          <div className="p-4 rounded-lg" style={{ background: '#F0FDF4', border: '1px solid #A7F3D0' }}>
            <div className="flex items-center gap-2 mb-3">
              <MessageCircle size={14} style={{ color: '#059669' }} />
              <span className="text-xs font-semibold" style={{ color: '#059669' }}>评论区关注点</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {audienceFocus.length > 0 ? (
                audienceFocus.map((focus, i) => (
                  <span 
                    key={i}
                    className="text-xs px-2.5 py-1 rounded-md transition-all duration-180"
                    style={{ 
                      background: '#D1FAE5', 
                      color: '#047857',
                      border: '1px solid #A7F3D0'
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.transform = 'translateY(-1px)';
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(5,150,105,0.15)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    {focus}
                  </span>
                ))
              ) : (
                <span className="text-xs text-[#9CA3AF]">暂无数据</span>
              )}
            </div>
          </div>
        </div>

        {/* Gap Analysis */}
        {gapAnalysis && (
          <div className="p-4 rounded-lg" style={{ background: '#FFFBEB', border: '1px solid #FDE68A' }}>
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={14} style={{ color: '#B45309' }} />
              <span className="text-xs font-semibold" style={{ color: '#B45309' }}>差异分析</span>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: '#92400E' }}>
              {gapAnalysis}
            </p>
          </div>
        )}

        {/* Audience Needs and Missed Topics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Audience Needs */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <HelpCircle size={14} style={{ color: '#7C3AED' }} />
              <span className="text-xs font-semibold text-[#6B7280]">观众需求</span>
            </div>
            <div className="flex flex-col gap-2">
              {audienceNeeds.length > 0 ? (
                audienceNeeds.map((need, i) => (
                  <div 
                    key={i}
                    className="p-3 rounded-lg text-xs leading-relaxed transition-all duration-180"
                    style={{ 
                      background: '#F5F3FF', 
                      color: '#5B21B6',
                      border: '1px solid #DDD6FE'
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.background = '#EDE9FE';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.background = '#F5F3FF';
                    }}
                  >
                    {need}
                  </div>
                ))
              ) : (
                <span className="text-xs text-[#9CA3AF]">暂无数据</span>
              )}
            </div>
          </div>

          {/* Missed Topics */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle size={14} style={{ color: '#DC2626' }} />
              <span className="text-xs font-semibold text-[#6B7280]">遗漏话题</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {missedTopics.length > 0 ? (
                missedTopics.map((topic, i) => (
                  <span 
                    key={i}
                    className="text-xs px-2.5 py-1 rounded-md transition-all duration-180"
                    style={{ 
                      background: '#FEE2E2', 
                      color: '#B91C1C',
                      border: '1px solid #FECACA'
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.transform = 'translateY(-1px)';
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(220,38,38,0.15)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    {topic}
                  </span>
                ))
              ) : (
                <span className="text-xs text-[#9CA3AF]">暂无遗漏话题</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
