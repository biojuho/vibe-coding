'use client';
import { useState, useMemo } from 'react';
import { ChevronLeft, ChevronRight, PlusCircle } from 'lucide-react';

export default function ScheduleTab({ events, onCreateEvent, onToggleEvent }) {
    const [isAdding, setIsAdding] = useState(false);
    const [currentDate, setCurrentDate] = useState(new Date());
    const [formData, setFormData] = useState({ title: "", date: new Date().toISOString().split('T')[0], type: "General" });

    const daysInMonth = (date) => new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
    const firstDayOfMonth = (date) => new Date(date.getFullYear(), date.getMonth(), 1).getDay();

    const monthDays = useMemo(() => {
        const days = [];
        const total = daysInMonth(currentDate);
        const startDay = firstDayOfMonth(currentDate);
        for (let i = 0; i < startDay; i++) {
            days.push(null);
        }
        for (let i = 1; i <= total; i++) {
            days.push(new Date(currentDate.getFullYear(), currentDate.getMonth(), i));
        }
        return days;
    }, [currentDate]);

    const handlePrevMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
    const handleNextMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));

    const handleSubmit = () => {
        if (!formData.title) return alert("일정 내용을 입력하세요.");
        onCreateEvent({ ...formData, date: formData.date });
        setIsAdding(false);
        setFormData({ title: "", date: new Date().toISOString().split('T')[0], type: "General" });
    };

    const typeColors = { "Vaccination": "#E91E63", "Checkup": "#2196F3", "Breeding": "#9C27B0", "Other": "#607D8B", "General": "#607D8B" };
    const typeLabels = { "Vaccination": "백신", "Checkup": "검진", "Breeding": "번식", "Other": "기타", "General": "일반" };

    const currentMonthEvents = useMemo(() => {
        return events.filter(e => {
            const d = new Date(e.date);
            return d.getMonth() === currentDate.getMonth() && d.getFullYear() === currentDate.getFullYear();
        });
    }, [events, currentDate]);

    const upcomingEvents = useMemo(() => {
        const now = new Date();
        now.setHours(0,0,0,0);
        return events.filter(e => new Date(e.date) >= now && !e.isCompleted).sort((a,b) => new Date(a.date) - new Date(b.date)).slice(0, 5);
    }, [events]);

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--color-text)" }}>🗓️ 농장 일정 관리</div>
                <button onClick={() => setIsAdding(!isAdding)} style={{ fontSize: "13px", fontWeight: 700, color: "var(--color-success)", background: "var(--color-bg-card)", border: "1px solid var(--color-success)", borderRadius: "8px", padding: "6px 12px", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px" }}>
                    <PlusCircle size={14} />
                    {isAdding ? "취소" : "새 일정"}
                </button>
            </div>

            {/* Event Form */}
            {isAdding && (
                <div style={{ background: "var(--color-bg)", borderRadius: "14px", padding: "16px", marginBottom: "16px", border: "1px solid var(--color-border)" }}>
                    <div style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px", color: "var(--color-text)" }}>새 일정 등록</div>
                    <div style={{ display: "grid", gap: "10px" }}>
                        <input placeholder="일정 내용 (예: 1동 구제역 백신)" value={formData.title} onChange={e => setFormData({ ...formData, title: e.target.value })} style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--color-border)", fontFamily: "inherit", background: "var(--color-bg-card)", color: "var(--color-text)" }} />
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                            <input type="date" value={formData.date} onChange={e => setFormData({ ...formData, date: e.target.value })} style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--color-border)", fontFamily: "inherit", background: "var(--color-bg-card)", color: "var(--color-text)" }} />
                            <select value={formData.type} onChange={e => setFormData({ ...formData, type: e.target.value })} style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--color-border)", fontFamily: "inherit", background: "var(--color-bg-card)", color: "var(--color-text)" }}>
                                <option value="General">일반</option><option value="Vaccination">예방접종</option><option value="Checkup">검진</option><option value="Breeding">번식</option>
                            </select>
                        </div>
                        <button onClick={handleSubmit} style={{ width: "100%", padding: "12px", background: "var(--color-success)", color: "white", borderRadius: "8px", border: "none", fontWeight: 700, marginTop: "8px", cursor: "pointer" }}>등록하기</button>
                    </div>
                </div>
            )}

            {/* Calendar Controls */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", padding: "0 4px" }}>
                <button onClick={handlePrevMonth} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-text-secondary)" }}><ChevronLeft /></button>
                <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--color-text)" }}>
                    {currentDate.getFullYear()}년 {currentDate.getMonth() + 1}월
                </div>
                <button onClick={handleNextMonth} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-text-secondary)" }}><ChevronRight /></button>
            </div>

            {/* Calendar Grid */}
            <div style={{ background: "var(--color-bg-card)", borderRadius: "12px", padding: "10px", border: "1px solid var(--color-border)", marginBottom: "20px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "2px", marginBottom: "4px", textAlign: "center" }}>
                    {['일', '월', '화', '수', '목', '금', '토'].map((d, i) => (
                        <div key={d} style={{ fontSize: "11px", fontWeight: 600, color: i === 0 ? "var(--color-danger)" : "var(--color-text-secondary)", padding: "4px" }}>{d}</div>
                    ))}
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "2px" }}>
                    {monthDays.map((day, idx) => {
                        if (!day) return <div key={`empty-${idx}`} style={{ minHeight: "60px", background: "var(--color-border-light)" }}></div>;
                        const dateStr = day.toISOString().split('T')[0];
                        const dayEvents = currentMonthEvents.filter(e => new Date(e.date).toISOString().split('T')[0] === dateStr);
                        const isToday = dateStr === new Date().toISOString().split('T')[0];

                        return (
                            <div key={idx}
                                onClick={() => { setFormData({ ...formData, date: dateStr }); setIsAdding(true); }}
                                style={{
                                    minHeight: "60px",
                                    padding: "4px",
                                    background: isToday ? "var(--color-success-light)" : "var(--color-bg-card)",
                                    border: isToday ? "1px solid var(--color-success)" : "1px solid var(--color-border-light)",
                                    borderRadius: "6px",
                                    cursor: "pointer",
                                    position: "relative"
                                }}
                            >
                                <div style={{ fontSize: "11px", fontWeight: isToday ? 700 : 400, color: "var(--color-text)", marginBottom: "2px" }}>{day.getDate()}</div>
                                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                    {dayEvents.slice(0, 3).map(ev => (
                                        <div key={ev.id} style={{ fontSize: "9px", background: typeColors[ev.type] || "var(--color-text-muted)", color: "white", borderRadius: "3px", padding: "1px 3px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                            {ev.title}
                                        </div>
                                    ))}
                                    {dayEvents.length > 3 && <div style={{ fontSize: "9px", color: "var(--color-text-muted)", textAlign: "center" }}>+{dayEvents.length - 3}</div>}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Upcoming List */}
            <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-text)", marginBottom: "10px" }}>🔜 다가오는 일정</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {upcomingEvents.length === 0 ? (
                    <div style={{ textAlign: "center", padding: "20px", color: "var(--color-text-muted)", fontSize: "13px" }}>예정된 일정이 없습니다.</div>
                ) : (
                    upcomingEvents.map(ev => {
                         const daysLeft = Math.ceil((new Date(ev.date) - new Date()) / (1000 * 60 * 60 * 24));
                         return (
                            <div key={ev.id} style={{ background: "var(--color-bg-card)", borderRadius: "10px", padding: "12px", border: "1px solid var(--color-border)", display: "flex", alignItems: "center", gap: "12px" }}>
                                <input type="checkbox" checked={ev.isCompleted} onChange={() => onToggleEvent(ev.id, !ev.isCompleted)} style={{ width: "18px", height: "18px", accentColor: "var(--color-success)", cursor:"pointer" }} />
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "2px" }}>
                                        <span style={{ fontSize: "11px", background: typeColors[ev.type], color: "white", padding: "2px 6px", borderRadius: "4px" }}>{typeLabels[ev.type]}</span>
                                        <span style={{ fontSize: "12px", color: daysLeft <= 3 ? "var(--color-danger)" : "var(--color-text-secondary)", fontWeight: daysLeft <= 3 ? 700 : 400 }}>
                                            {new Date(ev.date).toLocaleDateString()} {daysLeft === 0 ? "(오늘)" : `(${daysLeft}일 후)`}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--color-text)" }}>{ev.title}</div>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
