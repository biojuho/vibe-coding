'use client';

export default function NotificationModal({ notifications, onClose, onTestSMS }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content animate-slideInUp"
        onClick={e => e.stopPropagation()}
        style={{maxWidth:"400px", borderRadius:"var(--radius-xl)"}}
      >
        {/* Modal Handle — wider for better grab affordance */}
        <div className="modal-handle" style={{width:"48px",height:"5px",borderRadius:"3px"}} />

        {/* Header */}
        <div style={{
          display:"flex",
          justifyContent:"space-between",
          alignItems:"center",
          marginBottom:"22px",
          paddingBottom:"14px",
          borderBottom:"1px solid color-mix(in srgb, var(--color-border-custom) 30%, transparent)"
        }}>
          <div style={{
            fontSize:"19px",
            fontWeight:800,
            color:"var(--color-text)",
            display:"flex",
            alignItems:"center",
            gap:"10px",
            letterSpacing:"-0.01em"
          }}>
            <span className="animate-bounce" style={{fontSize:"22px"}}>🔔</span> 알림 센터
          </div>
          <button
            onClick={onClose}
            className="btn btn-ghost btn-icon"
            style={{width:"34px", height:"34px", fontSize:"18px", transition:"all 0.2s cubic-bezier(0.22,1,0.36,1)"}}
          >×</button>
        </div>

        {/* Notification List */}
        <div style={{maxHeight:"320px", overflowY:"auto", marginBottom:"20px"}}>
          {notifications.length === 0 ? (
            <div className="animate-fadeIn" style={{
              textAlign:"center",
              color:"var(--color-text-muted)",
              padding:"40px 20px",
              fontSize:"14px"
            }}>
              <div style={{fontSize:"40px", marginBottom:"12px"}}>🎉</div>
              새로운 알림이 없습니다.
            </div>
          ) : (
            <div style={{display:"grid", gap:"12px"}}>
              {notifications.map((n, i) => (
                <div
                  key={i}
                  className="animate-fadeInUp"
                  style={{
                    background: n.level === 'critical' ? "var(--color-danger-light)" : "var(--color-border-light)",
                    padding:"14px 16px",
                    borderRadius:"var(--radius-md)",
                    borderLeft: n.level === 'critical' ? "4px solid var(--color-danger)" : "4px solid var(--color-text-muted)",
                    transition:"all 0.25s cubic-bezier(0.22,1,0.36,1)",
                    animationDelay:`${i * 50}ms`,
                    cursor:"default"
                  }}
                >
                  <div style={{
                    fontSize:"14px",
                    fontWeight:700,
                    marginBottom:"6px",
                    color:"var(--color-text)",
                    display:"flex",
                    alignItems:"center",
                    gap:"6px"
                  }}>
                    {n.type==='urgent' && <span className="animate-pulse">🚨</span>}
                    {n.title}
                  </div>
                  <div style={{fontSize:"13px", color:"var(--color-text-secondary)", lineHeight:"1.5"}}>{n.message}</div>
                  <div style={{fontSize:"11px", color:"var(--color-text-muted)", marginTop:"8px", textAlign:"right"}}>{n.time || '-'}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* SMS Section */}
        <div style={{
          borderTop:"1px solid var(--color-border)",
          paddingTop:"18px"
        }}>
          <div style={{
            fontSize:"13px",
            fontWeight:700,
            color:"var(--color-primary-light)",
            marginBottom:"10px",
            display:"flex",
            alignItems:"center",
            gap:"6px"
          }}>
            📱 SMS 알림 서비스
          </div>
          <div style={{
            display:"flex",
            gap:"10px",
            alignItems:"center",
            background:"var(--color-border-light)",
            padding:"12px 14px",
            borderRadius:"var(--radius-md)"
          }}>
            <span style={{fontSize:"12px", color:"var(--color-text-secondary)", flex:1}}>
              중요 알림을 문자로 받으시겠습니까?
            </span>
            <button
              onClick={onTestSMS}
              className="btn btn-primary"
              style={{
                padding:"8px 14px",
                fontSize:"12px",
                width:"auto"
              }}
            >
              테스트 전송
            </button>
          </div>
          <div style={{
            fontSize:"11px",
            color:"var(--color-text-muted)",
            marginTop:"8px"
          }}>* Twilio / Kakao API 연동 필요 (비용 발생 가능)</div>
        </div>
      </div>
    </div>
  );
}
