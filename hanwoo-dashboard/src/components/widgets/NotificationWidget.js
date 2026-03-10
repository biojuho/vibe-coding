
'use client';

import { useState, useEffect } from 'react';
import { getNotifications } from '@/lib/actions';

export default function NotificationWidget() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getNotifications();
        setNotifications(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return null; // Don't show anything while loading to avoid CLS or show skeleton
  if (notifications.length === 0) return null; // Hide if no notifications

  return (
    <div className="animate-fadeInDown" style={{marginBottom:"24px"}}>
        <div style={{display:"flex", alignItems:"center", marginBottom:"12px", gap:"8px"}}>
            <span style={{fontSize:"18px"}}>🔔</span>
            <div style={{fontWeight:800, fontSize:"16px", color:"var(--color-text)"}}>주요 알림</div>
            <div style={{fontSize:"11px", background:"var(--color-danger)", color:"white", padding:"2px 8px", borderRadius:"100px", fontWeight:700}}>
                {notifications.length}건
            </div>
        </div>

        <div style={{display:"flex", flexDirection:"column", gap:"10px"}}>
            {notifications.map((note) => (
                <div key={note.id} style={{
                    background: "var(--color-bg-card)",
                    borderRadius: "12px",
                    padding: "16px",
                    borderLeft: `5px solid ${note.type === 'estrus' ? '#E91E63' : '#2196F3'}`,
                    boxShadow: "var(--shadow-sm)",
                    display: "flex",
                    alignItems: "center",
                    gap: "14px"
                }}>
                    <div style={{
                        width:"40px", height:"40px",
                        borderRadius:"50%",
                        background: note.type === 'estrus' ? '#FCE4EC' : '#E3F2FD',
                        display:"flex", alignItems:"center", justifyContent:"center",
                        fontSize:"20px", flexShrink: 0
                    }}>
                        {note.type === 'estrus' ? '💕' : '👶'}
                    </div>
                    <div>
                        <div style={{fontWeight:800, fontSize:"14px", color:"var(--color-text)", marginBottom:"2px"}}>
                            {note.title}
                            {note.level === 'critical' && <span className="animate-pulse" style={{marginLeft:"6px", fontSize:"10px", color:"var(--color-danger)"}}>긴급</span>}
                        </div>
                        <div style={{fontSize:"13px", color:"var(--color-text-secondary)"}}>{note.message}</div>
                    </div>
                </div>
            ))}
        </div>
    </div>
  );
}
