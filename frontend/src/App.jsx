import { useState, useEffect, useCallback, useRef } from 'react';
import { Circle, Download, Info, FileJson, FileDown, FileText } from 'lucide-react';
import { createJob, getJob } from './lib/api';
import InputPanel from './components/InputPanel';
import JobStatusPanel from './components/JobStatusPanel';
import TaskCard from './components/TaskCard';
import AnalysisSection from './components/AnalysisSection';
import LoadingState from './components/LoadingState';
import { ErrorBanner, WarningBanner, ErrorCard, EmptyState } from './components/StatusStates';
import AiChatBox from "./components/AiChatBox";

const POLL_MS = 2000;
const COLD_START_THRESHOLD_MS = 15000;

export default function App() {
  const [job, setJob] = useState(null);
  const [report, setReport] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [pageError, setPageError] = useState('');
  const [coldStartHint, setColdStartHint] = useState(false);
  const pollRef = useRef(null);
  const submittingSinceRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  async function loadReport(jobData) {
    for (const t of (jobData.tasks || [])) {
      if (t.status === 'done' && t.files?.markdown) {
        try {
          const res = await fetch(t.files.markdown);
          if (res.ok) {
            const text = await res.text();
            try { setReport(JSON.parse(text)); }
            catch { setReport({ raw: text }); }
          }
        } catch { /* ignore */ }
        break;
      }
    }
  }

  const startPolling = useCallback((jobId) => {
    stopPolling();
    submittingSinceRef.current = null;
    setColdStartHint(false);
    setIsSubmitting(false);
    setIsLoading(true);
    pollRef.current = setInterval(async () => {
      try {
        const data = await getJob(jobId);
        setJob(data);
        setPageError(data.error || '');
        if (data.tasks?.every(t => t.status === 'done' || t.status === 'failed')) {
          stopPolling();
          setIsLoading(false);
          await loadReport(data);
        }
      } catch { /* ignore poll errors */ }
    }, POLL_MS);
  }, [stopPolling]);

  async function handleSubmit(payload) {
    setPageError('');
    setReport(null);
    setColdStartHint(false);
    stopPolling();
    setIsLoading(false);
    setIsSubmitting(true);
    submittingSinceRef.current = Date.now();

    try {
      const data = await createJob(payload);
      setJob(data);
      setPageError(data.error || '');
      startPolling(data.job_id);
    } catch (err) {
      submittingSinceRef.current = null;
      setIsSubmitting(false);
      setPageError(err.message || '请求失败，请检查后端是否启动');
    }
  }

  // Cold-start detector
  useEffect(() => {
    if (!submittingSinceRef.current) return;
    const timer = setTimeout(() => {
      if (submittingSinceRef.current && !job) {
        setColdStartHint(true);
      }
    }, COLD_START_THRESHOLD_MS);
    return () => clearTimeout(timer);
  }, [isSubmitting, job]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const tasks = job?.tasks || [];
  const anyActive = isSubmitting || isLoading;
  const isAnalyzing = isLoading && !job?.tasks?.every(t => t.status === 'done' || t.status === 'failed');
  const allDone = tasks.length > 0 && tasks.every(t => t.status === 'done' || t.status === 'failed');

  // Get done tasks for export
  const doneTasks = tasks.filter(t => t.status === 'done');

  return (
    <div style={{ minHeight: '100vh', background: '#F7F8FA' }}>
      {/* ── Header ── */}
      <header style={{
        borderBottom: '1px solid #E5E7EB',
        padding: '0 32px',
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: '#FFFFFF',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        {/* Logo & Title */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            {/* Logo mark */}
            <div style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(37, 99, 235, 0.25)',
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"/>
                <path d="m21 21-4.3-4.3"/>
              </svg>
            </div>
            <div>
              <h1 style={{ fontSize: 18, fontWeight: 700, color: '#111827', lineHeight: 1.2, letterSpacing: '-0.02em' }}>
                ViewLens
              </h1>
              <p style={{ fontSize: 11, color: '#9CA3AF', marginTop: 1 }}>
                AI-powered video comment insight system
              </p>
            </div>
          </div>
        </div>

        {/* Right side actions */}
        <div className="flex items-center gap-3">
          {/* Export buttons */}
          {allDone && doneTasks.length > 0 && (
            <div className="flex items-center gap-2 mr-4">
              <ExportButton 
                href={`/api/jobs/${job.job_id}/${doneTasks[0].task_id}/comments`}
                icon={<FileJson size={14} />}
                label="JSON"
              />
              <ExportButton 
                href={`/api/jobs/${job.job_id}/${doneTasks[0].task_id}/report`}
                icon={<FileText size={14} />}
                label="Markdown"
              />
              <ExportButton 
                href={`/api/jobs/${job.job_id}/${doneTasks[0].task_id}/pdf`}
                icon={<FileDown size={14} />}
                label="PDF"
              />
            </div>
          )}

          {/* About */}
          <button 
            className="btn-secondary"
            onClick={() => {
              alert('ViewLens v1.0\n\nAI-powered video comment insight system for Bilibili & YouTube.\n\nBuilt with React + ECharts');
            }}
          >
            <Info size={14} />
            About
          </button>

          {/* Status indicator */}
          <div className="flex items-center gap-2 pl-3" style={{ borderLeft: '1px solid #E5E7EB' }}>
            <Circle size={8} fill="#10B981" className="text-[#10B981]" />
            <span style={{ fontSize: 12, color: '#6B7280' }}>Jason</span>
          </div>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main style={{
        padding: '32px',
        maxWidth: 1440,
        margin: '0 auto',
      }}>
        {/* Error Banner */}
        {pageError && (
          <ErrorBanner 
            error={pageError} 
            onDismiss={() => setPageError('')} 
          />
        )}

        {/* Cold Start Warning */}
        {coldStartHint && (
          <WarningBanner 
            title="后端可能正在冷启动"
            onDismiss={() => setColdStartHint(false)}
          >
            首次请求通常需要 20–40 秒，请稍候…
            <br />
            Render 免费版在 15 分钟无活动后会休眠，唤醒需要等待。
          </WarningBanner>
        )}

        {/* Three Column Layout */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '340px 1fr 320px',
          gap: 24,
          alignItems: 'start',
        }}>
          {/* ── Left: Input Panel ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <InputPanel
              onSubmit={handleSubmit}
              isSubmitting={isSubmitting}
              isPolling={isLoading}
            />
          </div>

          {/* ── Center: Analysis Results ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Loading State */}
            {anyActive && !allDone && (
              <LoadingState job={job} isSubmitting={isSubmitting} />
            )}

            {/* Analysis Section */}
            <AnalysisSection 
              report={report} 
              job={job} 
              isLoading={anyActive}
            />
          </div>

          {/* ── Right: Job Status + Tasks ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <JobStatusPanel job={job} />

            {/* Task cards */}
            {tasks.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ 
                  padding: '0 4px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 12,
                }}>
                  <span style={{ 
                    fontSize: 11, 
                    fontWeight: 600, 
                    letterSpacing: '0.08em', 
                    color: '#9CA3AF', 
                    textTransform: 'uppercase'
                  }}>
                    任务列表
                  </span>
                  <div style={{ flex: 1, height: 1, background: '#E5E7EB' }} />
                </div>
                {tasks.map((t, i) => (
                  <TaskCard key={t.task_id || i} task={t} jobId={job.job_id} index={i} />
                ))}
              </div>
            )}
          </div>
        </div>
        {report && <AiChatBox analysis={report} />}
      </main>

      {/* ── Footer ── */}
      <footer style={{
        borderTop: '1px solid #E5E7EB',
        padding: '24px 32px',
        textAlign: 'center',
        background: '#FFFFFF',
      }}>
        <p style={{ fontSize: 12, color: '#9CA3AF' }}>
          ViewLens · AI-powered video comment insight system · Built by Jason
        </p>
      </footer>
    </div>
  );
}

// Export Button Component
function ExportButton({ href, icon, label }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-180"
      style={{
        background: '#F3F4F6',
        border: '1px solid #E5E7EB',
        color: '#374151',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = '#2563EB';
        e.currentTarget.style.color = '#FFFFFF';
        e.currentTarget.style.borderColor = '#2563EB';
        e.currentTarget.style.transform = 'translateY(-1px)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = '#F3F4F6';
        e.currentTarget.style.color = '#374151';
        e.currentTarget.style.borderColor = '#E5E7EB';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      {icon}
      {label}
    </a>
  );
}
