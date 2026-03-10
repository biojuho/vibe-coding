'use client';
import { useState, useRef, useEffect } from 'react';

export default function AIChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'system', content: '안녕하세요! Joolife AI 농장 비서입니다. 🐮\n궁금한 점이 있으신가요? (예: 송아지 설사, 사료 급여...)' }
  ]);
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isOpen]);

  const handleSend = () => {
    if (!input.trim()) return;
    
    // User Message
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');

    // AI Response (Mock Logic)
    setTimeout(() => {
      let reply = "죄송해요, 아직 배우고 있는 중이라 잘 모르겠어요. 😅\n수의사 선생님께 문의해보시는 건 어떨까요?";
      
      const q = userMsg.content.toLowerCase();
      if (q.includes('설사')) reply = "🚨 **송아지 설사**가 의심되시나요?\n\n1. 즉시 **절식**시키고 전해질 제제를 급여하세요.\n2. 탈수가 심하면 수의사를 호출하세요.\n3. 보온에 신경 써주세요.";
      else if (q.includes('발정')) reply = "💗 **발정 징후** 체크리스트:\n\n- 승가 허용 (가장 확실)\n- 외음부 부종 및 점액 유출\n- 불안한 행동 및 울음\n\n발정 발견 후 **12~18시간** 사이가 적기입니다.";
      else if (q.includes('사료') || q.includes('급여')) reply = "🌾 **사료 급여 가이드**:\n\n- **송아지**: 입붙이기 사료 + 양질의 건초 무제한\n- **번식우**: 조사료 위주 (살이 찌지 않게 관리)\n- **비육우**: 농후사료 비율 점진적 증량";
      else if (q.includes('안녕')) reply = "안녕하세요! 오늘도 농장 관리 파이팅입니다! 💪";

      setMessages(prev => [...prev, { role: 'system', content: reply }]);
    }, 1000);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="animate-scaleIn"
        style={{
          position: "fixed",
          bottom: "90px",
          right: "20px",
          width: "60px",
          height: "60px",
          borderRadius: "var(--radius-full)",
          background: "linear-gradient(135deg, var(--color-primary-light), var(--color-primary))",
          color: "white",
          boxShadow: "0 6px 20px rgba(62, 47, 28, 0.4)",
          border: "none",
          fontSize: "26px",
          cursor: "pointer",
          zIndex: 999,
          transition: "all var(--transition-normal)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center"
        }}
        onMouseEnter={e => {
          e.currentTarget.style.transform = "scale(1.1)";
          e.currentTarget.style.boxShadow = "0 8px 28px rgba(62, 47, 28, 0.5)";
        }}
        onMouseLeave={e => {
          e.currentTarget.style.transform = "scale(1)";
          e.currentTarget.style.boxShadow = "0 6px 20px rgba(62, 47, 28, 0.4)";
        }}
      >
        🤖
      </button>
    );
  }

  return (
    <div
      className="animate-scaleIn"
      style={{
        position: "fixed",
        bottom: "90px",
        right: "20px",
        width: "340px",
        height: "500px",
        background: "var(--color-bg-card)",
        borderRadius: "var(--radius-xl)",
        boxShadow: "var(--shadow-lg)",
        zIndex: 999,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        border: "1px solid var(--color-border)"
      }}
    >
      {/* Header */}
      <div style={{
        padding: "16px 20px",
        background: "linear-gradient(135deg, var(--color-primary-light), var(--color-primary))",
        color: "white",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
      }}>
        <div style={{fontWeight: 700, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px"}}>
          <span className="animate-bounce">🤖</span> AI 농장 비서
        </div>
        <button
          onClick={() => setIsOpen(false)}
          style={{
            background: "rgba(255,255,255,0.2)",
            border: "none",
            color: "white",
            fontSize: "16px",
            cursor: "pointer",
            width: "28px",
            height: "28px",
            borderRadius: "var(--radius-full)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "all var(--transition-fast)"
          }}
          onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.3)"}
          onMouseLeave={e => e.currentTarget.style.background = "rgba(255,255,255,0.2)"}
        >×</button>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          padding: "18px",
          overflowY: "auto",
          background: "var(--color-border-light)",
          display: "flex",
          flexDirection: "column",
          gap: "14px"
        }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className="animate-fadeInUp"
            style={{
              alignSelf: m.role === 'user' ? "flex-end" : "flex-start",
              maxWidth: "85%",
              background: m.role === 'user'
                ? "linear-gradient(135deg, var(--color-primary-light), var(--color-primary))"
                : "var(--color-bg-card)",
              color: m.role === 'user' ? "white" : "var(--color-text)",
              padding: "12px 16px",
              borderRadius: "var(--radius-lg)",
              borderBottomRightRadius: m.role === 'user' ? "4px" : "var(--radius-lg)",
              borderTopLeftRadius: m.role === 'system' ? "4px" : "var(--radius-lg)",
              fontSize: "13px",
              lineHeight: "1.6",
              boxShadow: "var(--shadow-sm)",
              whiteSpace: "pre-wrap",
              animationDelay: `${i * 50}ms`
            }}
          >
            {m.content}
          </div>
        ))}
      </div>

      {/* Input */}
      <div style={{
        padding: "14px",
        background: "var(--color-bg-card)",
        borderTop: "1px solid var(--color-border)",
        display: "flex",
        gap: "10px"
      }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="질문을 입력하세요..."
          className="input"
          style={{
            flex: 1,
            padding: "12px 16px",
            borderRadius: "var(--radius-full)",
            border: "1.5px solid var(--color-border)",
            fontSize: "13px"
          }}
        />
        <button
          onClick={handleSend}
          className="btn btn-primary btn-icon"
          style={{
            width: "42px",
            height: "42px",
            padding: 0,
            fontSize: "16px",
            flexShrink: 0
          }}
        >↑</button>
      </div>
    </div>
  );
}
