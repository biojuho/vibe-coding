'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Bot, Loader2, Send, X } from 'lucide-react';

const INITIAL_MESSAGES = [
  {
    role: 'system',
    content: '안녕하세요. Joolife AI 농장 비서입니다.\n발정, 사양, 급여, 시세 등 궁금한 점을 물어보세요.',
  },
];

function buildOfflineReply(question) {
  const q = question.toLowerCase();
  if (q.includes('발정')) {
    return '발정 징후 체크리스트:\n- 활동량 증가\n- 울음 증가\n- 외음부 점액 확인\n- 12~18시간 이내 수정 적기 확인';
  }
  if (q.includes('급여') || q.includes('사료')) {
    return '급여 가이드:\n- 송아지: 초기 사료와 건초를 같이 관리\n- 번식우: 체형 유지 위주\n- 비육우: 후기 사료 비중을 단계적으로 조정';
  }
  if (q.includes('안녕')) {
    return '안녕하세요. 오늘 농장 운영에서 어떤 부분이 궁금하신가요?';
  }
  return '지금은 기본 농장 운영 질문 위주로 안내하고 있어요.\n발정, 급여, 건강관리처럼 구체적으로 물어보시면 더 정확히 도와드릴게요.';
}

function buildApiHistory(messages) {
  const history = [];
  let hasUserTurn = false;

  messages.forEach((message) => {
    if (!message.content) return;
    if (message.role === 'user') {
      hasUserTurn = true;
      history.push({ role: 'user', content: message.content });
    } else if (hasUserTurn && message.role === 'system') {
      history.push({ role: 'system', content: message.content });
    }
  });

  return history;
}

async function streamChat({
  message,
  history,
  signal,
  onChunk,
  onDone,
  onError,
}) {
  try {
    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
      signal,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `서버 오류 (${res.status})`);
    }

    if (!res.body) {
      throw new Error('응답 스트림을 열 수 없습니다.');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;
        const payload = trimmed.slice(6);

        if (payload === '[DONE]') {
          onDone();
          return;
        }

        try {
          const parsed = JSON.parse(payload);
          if (parsed.error) {
            onError(parsed.error);
            return;
          }
          if (parsed.text) {
            onChunk(parsed.text);
          }
        } catch {
          /* ignore malformed JSON chunks */
        }
      }
    }
    onDone();
  } catch (error) {
    if (error.name !== 'AbortError') {
      onError(error.message || '연결 오류가 발생했습니다.');
    }
  }
}

export default function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isOpen, messages]);

  const closeWidget = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsStreaming(false);
    setIsOpen(false);
  }, []);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    const userMessage = { role: 'user', content: trimmed };
    const historyForApi = buildApiHistory(messages);

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const streamingMsg = { role: 'system', content: '' };
    setMessages((prev) => [...prev, streamingMsg]);

    let accumulated = '';

    await streamChat({
      message: trimmed,
      history: historyForApi,
      signal: controller.signal,
      onChunk: (text) => {
        accumulated += text;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'system',
            content: accumulated,
          };
          return updated;
        });
      },
      onDone: () => {
        setIsStreaming(false);
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
      },
      onError: (errorMsg) => {
        const isApiKeyError =
          errorMsg.includes('API') ||
          errorMsg.includes('설정되지') ||
          errorMsg.includes('500');

        const fallback = isApiKeyError
          ? buildOfflineReply(trimmed)
          : `오류: ${errorMsg}`;

        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'system',
            content: fallback,
          };
          return updated;
        });
        setIsStreaming(false);
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
      },
    });

    if (controller.signal.aborted && !accumulated) {
      setMessages((prev) => {
        const updated = [...prev];
        if (updated.at(-1)?.role === 'system' && updated.at(-1)?.content === '') {
          updated.pop();
        }
        return updated;
      });
    }
    if (abortRef.current === controller) {
      abortRef.current = null;
      setIsStreaming(false);
    }
  }, [input, isStreaming, messages]);

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="animate-scaleIn"
        style={{
          position: 'fixed',
          bottom: '90px',
          right: '20px',
          width: '60px',
          height: '60px',
          borderRadius: 'var(--radius-full)',
          background: 'linear-gradient(135deg, var(--color-primary-light), var(--color-primary))',
          color: 'white',
          boxShadow: '0 6px 20px rgba(62, 47, 28, 0.4)',
          border: 'none',
          fontSize: '26px',
          cursor: 'pointer',
          zIndex: 999,
          transition: 'all var(--transition-normal)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        AI
      </button>
    );
  }

  return (
    <div
      className="animate-scaleIn"
      style={{
        position: 'fixed',
        bottom: '90px',
        right: '20px',
        width: '340px',
        height: '500px',
        background: 'var(--color-bg-card)',
        borderRadius: 'var(--radius-xl)',
        boxShadow: 'var(--shadow-lg)',
        zIndex: 999,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        border: '1px solid var(--color-border)',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '16px 20px',
          background: 'linear-gradient(135deg, var(--color-primary-light), var(--color-primary))',
          color: 'white',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ fontWeight: 700, fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Bot size={17} aria-hidden="true" />
          <span>AI 농장 비서</span>
          {isStreaming && (
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#4ade80',
                animation: 'pulse 1s infinite',
              }}
            />
          )}
        </div>
        <button
          type="button"
          onClick={closeWidget}
          aria-label="채팅 닫기"
          style={{
            background: 'rgba(255,255,255,0.2)',
            border: 'none',
            color: 'white',
            fontSize: '16px',
            cursor: 'pointer',
            width: '28px',
            height: '28px',
            borderRadius: 'var(--radius-full)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          padding: '18px',
          overflowY: 'auto',
          background: 'var(--color-border-light)',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
      >
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className="animate-fadeInUp"
            style={{
              alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%',
              background:
                message.role === 'user'
                  ? 'linear-gradient(135deg, var(--color-primary-light), var(--color-primary))'
                  : 'var(--color-bg-card)',
              color: message.role === 'user' ? 'white' : 'var(--color-text)',
              padding: '12px 16px',
              borderRadius: 'var(--radius-lg)',
              borderBottomRightRadius: message.role === 'user' ? '4px' : 'var(--radius-lg)',
              borderTopLeftRadius: message.role === 'system' ? '4px' : 'var(--radius-lg)',
              fontSize: '13px',
              lineHeight: '1.6',
              boxShadow: 'var(--shadow-sm)',
              whiteSpace: 'pre-wrap',
            }}
          >
            {message.content || (isStreaming && index === messages.length - 1 ? '...' : '')}
          </div>
        ))}
      </div>

      {/* Input */}
      <div
        style={{
          padding: '14px',
          background: 'var(--color-bg-card)',
          borderTop: '1px solid var(--color-border)',
          display: 'flex',
          gap: '10px',
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? '답변 생성 중...' : '질문을 입력해 주세요.'}
          disabled={isStreaming}
          className="input"
          style={{
            flex: 1,
            padding: '12px 16px',
            borderRadius: 'var(--radius-full)',
            border: '1.5px solid var(--color-border)',
            fontSize: '13px',
            opacity: isStreaming ? 0.6 : 1,
          }}
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={isStreaming}
          className="btn btn-primary btn-icon"
          style={{
            width: '42px',
            height: '42px',
            padding: 0,
            fontSize: '16px',
            flexShrink: 0,
            opacity: isStreaming ? 0.6 : 1,
            cursor: isStreaming ? 'not-allowed' : 'pointer',
          }}
        >
          {isStreaming ? (
            <Loader2 size={16} aria-hidden="true" style={{ animation: 'spin 0.9s linear infinite' }} />
          ) : (
            <Send size={16} aria-hidden="true" />
          )}
        </button>
      </div>

      {/* Streaming indicators */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
