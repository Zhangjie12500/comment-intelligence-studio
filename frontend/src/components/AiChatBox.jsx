import { useState, useRef, useEffect } from 'react';
import { Send, RefreshCw, Loader2, MessageCircle } from 'lucide-react';
import Card from './Card';

const MAX_TURNS = 10;

const QUICK_QUESTIONS = [
  { id: 1, text: '评论区最大争议是什么？' },
  { id: 2, text: '观众最真实的需求是什么？' },
  { id: 3, text: '给创作者三条优化建议' },
  { id: 4, text: '如何把这个结果写进比赛PPT？' },
];

// Error messages mapping
const ERROR_MESSAGES = {
  'OPENAI_API_KEY_NOT_CONFIGURED': '当前未配置 AI 服务，无法使用对话助手。',
  'MAX_TURNS_EXCEEDED': '当前对话已达到 10 轮上限，请重置对话后继续。',
  'IRRELEVANT_QUESTION': null, // Use reply from server
  'DEFAULT': 'AI 对话请求失败，请检查后端服务或网络连接。',
};

export default function AiChatBox({ analysisData }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8010/api';

  // Get analysis context from props
  const getAnalysisContext = () => {
    if (!analysisData) return {};

    const context = {};

    // video_type
    if (analysisData.video_type) {
      context.video_type = {
        primary: analysisData.video_type.primary || '',
        secondary: analysisData.video_type.secondary || '',
      };
    }

    // video_summary
    if (analysisData.video_summary) {
      context.video_summary = {
        summary: analysisData.video_summary.summary || '',
        key_points: analysisData.video_summary.key_points || [],
      };
    }

    // content_comment_comparison
    if (analysisData.content_comment_comparison) {
      context.content_comment_comparison = {
        video_focus: analysisData.content_comment_comparison.video_focus || [],
        audience_focus: analysisData.content_comment_comparison.audience_focus || [],
        gap_analysis: analysisData.content_comment_comparison.gap_analysis || '',
      };
    }

    // top insights from clusters and controversies
    const topInsights = [];
    if (analysisData.clusters) {
      analysisData.clusters.slice(0, 3).forEach(cl => {
        if (cl.title) topInsights.push(`观点聚类：${cl.title}`);
      });
    }
    if (analysisData.controversies) {
      analysisData.controversies.slice(0, 2).forEach(co => {
        if (co.title) topInsights.push(`争议点：${co.title}`);
      });
    }
    if (topInsights.length > 0) {
      context.top_insights = topInsights;
    }

    return context;
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const currentTurns = messages.filter(m => m.role === 'user').length;
  const isDisabled = currentTurns >= MAX_TURNS;

  const handleSend = async (text = input) => {
    if (!text.trim() || isLoading || isDisabled) return;

    const userMessage = { role: 'user', content: text.trim() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setError(null);
    setIsLoading(true);

    try {
      // Build history for API
      const history = messages.map(m => ({ role: m.role, content: m.content }));

      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text.trim(),
          history,
          analysis_context: getAnalysisContext(),
        }),
      });

      const data = await response.json();

      if (data.error) {
        if (data.error === 'IRRELEVANT_QUESTION') {
          // Show guidance as AI response
          setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
        } else {
          // Show error message
          const errorMsg = ERROR_MESSAGES[data.error] || ERROR_MESSAGES['DEFAULT'];
          setError(errorMsg);
        }
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
      }
    } catch (err) {
      setError('AI 对话请求失败，请检查后端服务或网络连接。');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([]);
    setInput('');
    setError(null);
    setIsLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickQuestion = (question) => {
    handleSend(question);
  };

  return (
    <Card>
      <div className="px-5 pt-5 pb-4 border-b border-[#F3F4F6]">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <MessageCircle size={15} className="text-[#2563EB]" />
              <span className="text-xs font-semibold text-[#6B7280] tracking-wide uppercase">
                Ask ViewLens AI
              </span>
            </div>
            <p className="text-xs text-[#9CA3AF] mt-1">
              基于当前视频分析结果继续提问
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[#9CA3AF]">
              {currentTurns} / {MAX_TURNS}
            </span>
            {messages.length > 0 && (
              <button
                onClick={handleReset}
                className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg transition-all duration-180"
                style={{
                  background: '#F3F4F6',
                  color: '#6B7280',
                  border: '1px solid #E5E7EB',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = '#E5E7EB';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = '#F3F4F6';
                }}
              >
                <RefreshCw size={12} />
                重置对话
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-col" style={{ height: '400px' }}>
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {/* Show quick questions when no messages */}
          {messages.length === 0 && (
            <div className="mb-4">
              <p className="text-xs text-[#9CA3AF] mb-3">快捷问题：</p>
              <div className="flex flex-wrap gap-2">
                {QUICK_QUESTIONS.map(q => (
                  <button
                    key={q.id}
                    onClick={() => handleQuickQuestion(q.text)}
                    disabled={isLoading || isDisabled}
                    className="text-xs px-3 py-2 rounded-lg transition-all duration-180"
                    style={{
                      background: '#EFF6FF',
                      color: '#2563EB',
                      border: '1px solid #BFDBFE',
                    }}
                    onMouseEnter={e => {
                      if (!isLoading && !isDisabled) {
                        e.currentTarget.style.background = '#DBEAFE';
                        e.currentTarget.style.transform = 'translateY(-1px)';
                      }
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.background = '#EFF6FF';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }}
                  >
                    {q.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* No analysis context warning */}
          {messages.length === 0 && !analysisData && (
            <div className="p-3 rounded-lg text-xs" style={{ background: '#FEF3C7', color: '#B45309', border: '1px solid #FDE68A' }}>
              暂无视频分析结果，对话将基于通用知识回答。建议先分析一个视频以获得更准确的洞察。
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="p-3 rounded-lg text-sm" style={{ background: '#FEE2E2', color: '#B91C1C', border: '1px solid #FECACA' }}>
              {error}
            </div>
          )}

          {/* Messages */}
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className="max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed"
                style={
                  msg.role === 'user'
                    ? {
                        background: '#2563EB',
                        color: '#FFFFFF',
                        borderBottomRightRadius: '4px',
                      }
                    : {
                        background: '#F3F4F6',
                        color: '#374151',
                        borderBottomLeftRadius: '4px',
                      }
                }
              >
                {msg.content}
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div
                className="px-4 py-3 rounded-2xl text-sm flex items-center gap-2"
                style={{ background: '#F3F4F6', color: '#6B7280', borderBottomLeftRadius: '4px' }}
              >
                <Loader2 size={14} className="animate-spin" />
                ViewLens AI 正在分析...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="p-4 border-t border-[#F3F4F6]">
          <div className="flex gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isDisabled ? '已达到对话上限，请重置对话' : '输入问题...'}
              disabled={isDisabled || isLoading}
              rows={2}
              className="flex-1 px-3 py-2 text-sm rounded-lg resize-none transition-all duration-180 focus:outline-none focus:ring-2"
              style={{
                background: '#F9FAFB',
                border: '1px solid #E5E7EB',
                color: '#374151',
              }}
              onFocus={e => {
                e.currentTarget.style.borderColor = '#2563EB';
                e.currentTarget.style.boxShadow = '0 0 0 2px rgba(37,99,235,0.1)';
              }}
              onBlur={e => {
                e.currentTarget.style.borderColor = '#E5E7EB';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading || isDisabled}
              className="px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-all duration-180 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: '#2563EB',
                color: '#FFFFFF',
              }}
              onMouseEnter={e => {
                if (!e.currentTarget.disabled) {
                  e.currentTarget.style.background = '#1D4ED8';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = '#2563EB';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              {isLoading ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Send size={16} />
              )}
              发送
            </button>
          </div>
          <p className="text-xs text-[#9CA3AF] mt-2">
            Enter 发送 · Shift + Enter 换行
          </p>
        </div>
      </div>
    </Card>
  );
}
