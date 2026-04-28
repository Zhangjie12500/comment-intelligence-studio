import { Loader2, CheckCircle2, Circle } from 'lucide-react';

// Loading steps for analysis process
export const LOADING_STEPS = [
  { id: 'parsing', label: '正在解析视频链接', icon: 'link' },
  { id: 'fetching', label: '正在抓取评论', icon: 'download' },
  { id: 'cleaning', label: '正在清洗评论', icon: 'filter' },
  { id: 'analyzing', label: '正在生成 AI 分析', icon: 'sparkles' },
  { id: 'visualizing', label: '正在生成可视化结果', icon: 'chart' },
  { id: 'complete', label: '分析完成', icon: 'check' },
];

// Get step index based on job status
export function getStepIndex(job, isSubmitting) {
  if (isSubmitting) return 0; // "正在解析视频链接"
  
  const tasks = job?.tasks || [];
  const allDone = tasks.length > 0 && tasks.every(t => t.status === 'done' || t.status === 'failed');
  const anyAnalyzing = tasks.some(t => t.status === 'analyzing');
  const anyFetching = tasks.some(t => t.status === 'fetching');
  const anyExporting = tasks.some(t => t.status === 'exporting');
  
  if (allDone) return 5; // "分析完成"
  if (anyExporting) return 4; // "正在生成可视化结果"
  if (anyAnalyzing) return 3; // "正在生成 AI 分析"
  if (anyFetching) return 2; // "正在抓取评论" or "正在清洗评论"
  if (tasks.length > 0) return 1; // "正在解析视频链接"
  
  return 0;
}

// Loading Progress Card
export default function LoadingState({ job, isSubmitting }) {
  const currentStep = getStepIndex(job, isSubmitting);
  
  return (
    <div className="bg-white rounded-xl border border-[#E5E7EB] shadow-sm p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-blue-50 border border-[#DBEAFE] flex items-center justify-center">
          <Loader2 size={20} className="text-[#2563EB] animate-spin" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-[#111827]">正在分析中</h3>
          <p className="text-xs text-[#9CA3AF]">请稍候，正在处理你的请求</p>
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {LOADING_STEPS.map((step, index) => {
          const isComplete = index < currentStep;
          const isCurrent = index === currentStep;
          const isPending = index > currentStep;

          return (
            <div key={step.id} className="flex items-center gap-3">
              {/* Step indicator */}
              <div 
                className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-all duration-300"
                style={{
                  background: isComplete 
                    ? '#D1FAE5' 
                    : isCurrent 
                      ? '#DBEAFE' 
                      : '#F3F4F6',
                  border: isComplete 
                    ? '2px solid #10B981' 
                    : isCurrent 
                      ? '2px solid #2563EB' 
                      : '2px solid #E5E7EB',
                }}
              >
                {isComplete ? (
                  <CheckCircle2 size={14} className="text-[#059669]" />
                ) : isCurrent ? (
                  <div className="w-2 h-2 rounded-full bg-[#2563EB] animate-pulse" />
                ) : (
                  <Circle size={10} className="text-[#D1D5DB]" />
                )}
              </div>

              {/* Step label */}
              <span 
                className="text-sm transition-all duration-300"
                style={{
                  color: isComplete 
                    ? '#059669' 
                    : isCurrent 
                      ? '#2563EB' 
                      : '#9CA3AF',
                  fontWeight: isCurrent ? '600' : '400',
                }}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="mt-6">
        <div className="w-full h-1.5 rounded-full bg-[#F3F4F6] overflow-hidden">
          <div 
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{ 
              width: `${((currentStep + 1) / LOADING_STEPS.length) * 100}%`,
              background: currentStep === LOADING_STEPS.length - 1 
                ? '#10B981' 
                : '#2563EB'
            }}
          />
        </div>
      </div>
    </div>
  );
}
