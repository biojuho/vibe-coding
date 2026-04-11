'use client';

import { useEffect, useRef, useState } from 'react';

const INITIAL_MESSAGES = [
  {
    role: 'system',
    content: '안녕하세요. Joolife AI 농장 비서입니다.\n발정, 사양, 급여 기록 같은 질문을 도와드릴게요.',
  },
];

function buildReply(question) {
  const normalized = question.toLowerCase();

  if (normalized.includes('발정')) {
    return '발정 징후 체크리스트:\n- 활동량 증가\n- 울음 증가\n- 외음부 점액 확인\n- 12~18시간 이내 수정 적기 확인';
  }

  if (normalized.includes('급여') || normalized.includes('사료')) {
    return '급여 가이드:\n- 송아지: 초기 사료와 건초를 같이 관리\n- 번식우: 체형 유지 위주\n- 비육우: 후기 사료 비중을 단계적으로 조정';
  }

  if (normalized.includes('안녕')) {
    return '안녕하세요. 오늘 농장 운영에서 어떤 부분이 궁금하신가요?';
  }

  return '지금은 기본 농장 운영 질문 위주로 안내하고 있어요. 발정, 급여, 건강관리처럼 구체적으로 물어보시면 더 정확히 도와드릴게요.';
}

export default function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);
  const pendingTimeoutsRef = useRef(new Set());

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isOpen, messages]);

  useEffect(() => {
    const pendingTimeouts = pendingTimeoutsRef.current;
    return () => {
      pendingTimeouts.forEach((timeoutId) => window.clearTimeout(timeoutId));
      pendingTimeouts.clear();
    };
  }, []);

  const closeWidget = () => {
    pendingTimeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
    pendingTimeoutsRef.current.clear();
    setIsOpen(false);
  };

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) {
      return;
    }

    const userMessage = { role: 'user', content: trimmed };
    setMessages((previous) => [...previous, userMessage]);
    setInput('');

    const timeoutId = window.setTimeout(() => {
      pendingTimeoutsRef.current.delete(timeoutId);
      setMessages((previous) => [...previous, { role: 'system', content: buildReply(trimmed) }]);
    }, 1000);

    pendingTimeoutsRef.current.add(timeoutId);
  };

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
          <span>AI</span>
          <span>농장 비서</span>
        </div>
        <button
          type="button"
          onClick={closeWidget}
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
          ×
        </button>
      </div>

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
            {message.content}
          </div>
        ))}
      </div>

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
          placeholder="질문을 입력해 주세요."
          className="input"
          style={{
            flex: 1,
            padding: '12px 16px',
            borderRadius: 'var(--radius-full)',
            border: '1.5px solid var(--color-border)',
            fontSize: '13px',
          }}
        />
        <button
          type="button"
          onClick={handleSend}
          className="btn btn-primary btn-icon"
          style={{
            width: '42px',
            height: '42px',
            padding: 0,
            fontSize: '16px',
            flexShrink: 0,
          }}
        >
          →
        </button>
      </div>
    </div>
  );
}
