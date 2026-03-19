'use client';

import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, PlusCircle } from 'lucide-react';

const TYPE_STYLES = {
  Vaccination: { label: '백신', color: 'var(--chart-clay-4)' },
  Checkup: { label: '검진', color: 'var(--chart-clay-5)' },
  Breeding: { label: '번식', color: 'var(--color-calving)' },
  Other: { label: '기타', color: 'var(--color-text-muted)' },
  General: { label: '일반', color: 'var(--chart-clay-1)' },
};

export default function ScheduleTab({ events, onCreateEvent, onToggleEvent }) {
  const [isAdding, setIsAdding] = useState(false);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [formData, setFormData] = useState({
    title: '',
    date: new Date().toISOString().split('T')[0],
    type: 'General',
  });

  const monthDays = useMemo(() => {
    const days = [];
    const total = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0).getDate();
    const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1).getDay();

    for (let index = 0; index < firstDay; index += 1) days.push(null);
    for (let day = 1; day <= total; day += 1) days.push(new Date(currentDate.getFullYear(), currentDate.getMonth(), day));

    return days;
  }, [currentDate]);

  const currentMonthEvents = useMemo(
    () =>
      events.filter((event) => {
        const date = new Date(event.date);
        return date.getMonth() === currentDate.getMonth() && date.getFullYear() === currentDate.getFullYear();
      }),
    [events, currentDate]
  );

  const upcomingEvents = useMemo(() => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    return events
      .filter((event) => new Date(event.date) >= now && !event.isCompleted)
      .sort((first, second) => new Date(first.date) - new Date(second.date))
      .slice(0, 5);
  }, [events]);

  const handleSubmit = () => {
    if (!formData.title) {
      alert('일정 제목을 입력해 주세요.');
      return;
    }

    onCreateEvent({ ...formData, date: formData.date });
    setIsAdding(false);
    setFormData({ title: '', date: new Date().toISOString().split('T')[0], type: 'General' });
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--color-text)' }}>🗓️ 농장 일정 관리</div>
        <button
          type="button"
          onClick={() => setIsAdding((previous) => !previous)}
          className="clay-pressable inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-[color:var(--color-text)]"
        >
          <PlusCircle size={14} />
          {isAdding ? '취소' : '새 일정'}
        </button>
      </div>

      {isAdding ? (
        <div className="clay-page-section mb-4 p-4">
          <div className="mb-3 text-sm font-bold text-[color:var(--color-text)]">일정 등록</div>
          <div className="grid gap-3">
            <input
              placeholder="예: 1동 구제역 백신"
              value={formData.title}
              onChange={(event) => setFormData({ ...formData, title: event.target.value })}
              className="clay-inset rounded-[16px] px-4 py-3 text-sm text-[color:var(--color-text)] outline-none"
            />
            <div className="grid grid-cols-2 gap-3">
              <input
                type="date"
                value={formData.date}
                onChange={(event) => setFormData({ ...formData, date: event.target.value })}
                className="clay-inset rounded-[16px] px-4 py-3 text-sm text-[color:var(--color-text)] outline-none"
              />
              <select
                value={formData.type}
                onChange={(event) => setFormData({ ...formData, type: event.target.value })}
                className="clay-inset rounded-[16px] px-4 py-3 text-sm text-[color:var(--color-text)] outline-none"
              >
                <option value="General">일반</option>
                <option value="Vaccination">백신</option>
                <option value="Checkup">검진</option>
                <option value="Breeding">번식</option>
                <option value="Other">기타</option>
              </select>
            </div>
            <button
              type="button"
              onClick={handleSubmit}
              className="rounded-[18px] px-4 py-3 text-sm font-bold text-white"
              style={{
                background: 'var(--surface-gradient-primary)',
                boxShadow: 'var(--shadow-button-primary)',
              }}
            >
              일정 등록하기
            </button>
          </div>
        </div>
      ) : null}

      <div className="mb-3 flex items-center justify-between px-1">
        <button type="button" onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1))}>
          <ChevronLeft className="text-[color:var(--color-text-secondary)]" />
        </button>
        <div className="text-2xl font-bold text-[color:var(--color-text)]" style={{ fontFamily: 'var(--font-display-custom)' }}>
          {currentDate.getFullYear()}년 {currentDate.getMonth() + 1}월
        </div>
        <button type="button" onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1))}>
          <ChevronRight className="text-[color:var(--color-text-secondary)]" />
        </button>
      </div>

      <div className="clay-page-section mb-5 p-3">
        <div className="mb-2 grid grid-cols-7 gap-2 text-center">
          {['일', '월', '화', '수', '목', '금', '토'].map((label, index) => (
            <div key={label} className="text-[11px] font-semibold" style={{ color: index === 0 ? 'var(--color-danger)' : 'var(--color-text-secondary)' }}>
              {label}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-2">
          {monthDays.map((day, index) => {
            if (!day) {
              return <div key={`empty-${index}`} className="clay-inset min-h-[78px] rounded-[16px]" />;
            }

            const dateStr = day.toISOString().split('T')[0];
            const dayEvents = currentMonthEvents.filter((event) => new Date(event.date).toISOString().split('T')[0] === dateStr);
            const isToday = dateStr === new Date().toISOString().split('T')[0];

            return (
              <div
                key={dateStr}
                onClick={() => {
                  setFormData({ ...formData, date: dateStr });
                  setIsAdding(true);
                }}
                className="rounded-[16px] border p-2"
                style={{
                  minHeight: '78px',
                  background: isToday
                    ? 'color-mix(in srgb, var(--chart-clay-1) 14%, var(--color-surface-elevated))'
                    : 'var(--surface-gradient)',
                  borderColor: isToday ? 'color-mix(in srgb, var(--chart-clay-1) 38%, transparent)' : 'var(--color-surface-stroke)',
                  cursor: 'pointer',
                  boxShadow: 'var(--shadow-sm)',
                }}
              >
                <div className="mb-1 text-[11px] font-semibold text-[color:var(--color-text)]">{day.getDate()}</div>
                <div className="grid gap-1">
                  {dayEvents.slice(0, 3).map((event) => {
                    const typeStyle = TYPE_STYLES[event.type] || TYPE_STYLES.General;
                    return (
                      <div
                        key={event.id}
                        className="truncate rounded-full px-2 py-0.5 text-[9px] font-bold text-white"
                        style={{ background: typeStyle.color }}
                      >
                        {event.title}
                      </div>
                    );
                  })}
                  {dayEvents.length > 3 ? (
                    <div className="text-center text-[9px] font-semibold text-[color:var(--color-text-muted)]">+{dayEvents.length - 3}</div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mb-3 text-sm font-bold text-[color:var(--color-text)]">다가오는 일정</div>
      <div className="grid gap-3">
        {upcomingEvents.length > 0 ? (
          upcomingEvents.map((event) => {
            const daysLeft = Math.ceil((new Date(event.date) - new Date()) / (1000 * 60 * 60 * 24));
            const typeStyle = TYPE_STYLES[event.type] || TYPE_STYLES.General;

            return (
              <div
                key={event.id}
                className="clay-page-section flex items-center gap-3 p-4"
              >
                <input
                  type="checkbox"
                  checked={event.isCompleted}
                  onChange={() => onToggleEvent(event.id, !event.isCompleted)}
                  style={{ width: '18px', height: '18px', accentColor: 'var(--chart-clay-1)', cursor: 'pointer' }}
                />
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                    <span
                      className="inline-flex rounded-full px-3 py-1 text-[10px] font-bold text-white"
                      style={{ background: typeStyle.color }}
                    >
                      {typeStyle.label}
                    </span>
                    <span
                      className="text-xs font-medium"
                      style={{ color: daysLeft <= 3 ? 'var(--color-danger)' : 'var(--color-text-secondary)' }}
                    >
                      {new Date(event.date).toLocaleDateString()} {daysLeft === 0 ? '(오늘)' : `(D-${daysLeft})`}
                    </span>
                  </div>
                  <div className="text-sm font-semibold text-[color:var(--color-text)]">{event.title}</div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="clay-inset rounded-[24px] px-6 py-10 text-center text-sm text-[color:var(--color-text-muted)]">
            예정된 일정이 없습니다.
          </div>
        )}
      </div>
    </div>
  );
}
