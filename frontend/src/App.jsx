import { useState, useEffect, useCallback, useRef } from 'react';
import { Circle, AlertTriangle } from 'lucide-react';
import { createJob, getJob } from './lib/api';
import InputPanel from './components/InputPanel';
import JobStatusPanel from './components/JobStatusPanel';
import TaskCard from './components/TaskCard';
import AnalysisSection from './components/AnalysisSection';

const POLL_MS = 2000;
const COLD_START_THRESHOLD_MS = 15000;

export default function App() {
  const [job, setJob] = useState(null);
  const [report, setReport] = useState(null);
  /** isSubmitting = POST request in flight (cold-start window) */
  const [isSubmitting, setIsSubmitting] = useState(false);
  /** isLoading = polling active */
  const [isLoading, setIsLoading] = useState(false);
  const [pageError, setPageError] = useState('');
  /** coldStartHint = true when POST succeeded but no polling started after 15s */
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

    // Mark submission start — button enters "后端启动中" state
    setIsSubmitting(true);
    submittingSinceRef.current = Date.now();

    try {
      const data = await createJob(payload);
      setJob(data);
      setPageError(data.error || '');

      // Immediate polling start (even if all done, for consistency)
      startPolling(data.job_id);
    } catch (err) {
      submittingSinceRef.current = null;
      setIsSubmitting(false);
      setPageError(err.message || '请求失败，请检查后端是否启动');
    }
  }

  // Cold-start detector: show hint after 15s if POST succeeded but no job yet
  useEffect(() => {
    if (!submittingSinceRef.current) return;
    const timer = setTimeout(() => {
      // Still submitting after 15s → cold start likely
      if (submittingSinceRef.current && !job) {
        setColdStartHint(true);
      }
    }, COLD_START_THRESHOLD_MS);
    return () => clearTimeout(timer);
  }, [isSubmitting, job]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const tasks = job?.tasks || [];
  const anySubmitting = isSubmitting || isLoading;

  return (
    <div style={{ minHeight: '100vh', background: '#09090b' }}>
      {/* ── Header ── */}
      <header style={{
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        padding: '0 32px',
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
        position: 'sticky',
        top: 0,
        zIndex: 50,
        background: 'rgba(9,9,11,0.85)',
        backdropFilter: 'blur(12px)',
      }}>
        <div>
          <h1 style={{ fontSize: 15, fontWeight: 600, color: '#fafafa', lineHeight: 1.2 }}>
            评论区智能分析工作台
          </h1>
          <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginTop: 1 }}>
            B站 &amp; YouTube 评论分析引擎
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Circle size={7} className="text-green-400 fill-green-400" />
          <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>后端在线 · 端口 8010</span>
        </div>
      </header>

      {/* ── Main grid ── */}
      <main style={{
        padding: '24px 32px 48px',
        maxWidth: 1400,
        margin: '0 auto',
      }}>
        {/* page-level error */}
        {pageError && (
          <div style={{
            marginBottom: 20,
            padding: '12px 16px',
            borderRadius: 10,
            background: 'rgba(248,113,113,0.08)',
            border: '1px solid rgba(248,113,113,0.2)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 8,
          }}>
            <span style={{ fontSize: 12, color: '#f87171', lineHeight: 1.6 }}>{pageError}</span>
          </div>
        )}

        {/* cold-start hint */}
        {coldStartHint && (
          <div style={{
            marginBottom: 20,
            padding: '12px 16px',
            borderRadius: 10,
            background: 'rgba(251,191,36,0.06)',
            border: '1px solid rgba(251,191,36,0.2)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 8,
          }}>
            <AlertTriangle size={14} style={{ color: '#fbbf24', marginTop: 1, flexShrink: 0 }} />
            <div>
              <p style={{ fontSize: 12, color: '#fbbf24', lineHeight: 1.5, fontWeight: 500 }}>
                后端可能正在冷启动，首次请求通常需要 20–40 秒，请稍候…
              </p>
              <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginTop: 3 }}>
                Render 免费版在 15 分钟无活动后会休眠，唤醒需要等待。
              </p>
            </div>
          </div>
        )}

        <div style={{
          display: 'grid',
          gridTemplateColumns: '300px 1fr 280px',
          gap: 20,
          alignItems: 'start',
        }}>
          {/* ── Left: Input ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <InputPanel
              onSubmit={handleSubmit}
              isSubmitting={isSubmitting}
              isPolling={isLoading}
            />
          </div>

          {/* ── Center: Analysis ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <AnalysisSection report={report} job={job} />
          </div>

          {/* ── Right: Job status + tasks ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <JobStatusPanel job={job} />

            {/* Task cards */}
            {tasks.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ padding: '0 4px', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.1em', color: 'rgba(255,255,255,0.25)', textTransform: 'uppercase' }}>
                    任务列表
                  </span>
                  <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />
                </div>
                {tasks.map((t, i) => (
                  <TaskCard key={t.task_id || i} task={t} jobId={job.job_id} index={i} />
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
