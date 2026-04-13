'use client';

import { PremiumCard, PremiumCardContent } from '@/components/ui/premium-card';
import { HeartIcon } from '@/components/ui/common';
import { formatDate } from '@/lib/utils';

// [QA 수정] 실제 운영 import — CSS 변수 기반 색상 적용
export function EstrusAlertBanner({ notifications = [], buildings = [] }) {
  const estrusNotifications = notifications.filter((notification) => notification.type === 'estrus');

  if (estrusNotifications.length === 0) {
    return null;
  }

  const todayCount = estrusNotifications.filter((notification) => notification.daysLeft === 0).length;

  return (
    <PremiumCard
      className="animate-fadeInUp mb-4"
      style={{ animationDelay: '100ms', borderColor: 'var(--premium-card-badge-negative-border)' }}
    >
      <PremiumCardContent className="p-4">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
          <span className="alert-icon"><HeartIcon /></span>
          <span style={{ fontWeight: 700, fontSize: '15px', letterSpacing: '-0.3px' }}>
            🔔 발정 알림 — {todayCount > 0 ? `오늘 ${todayCount}두` : `${estrusNotifications.length}두 임박`}
          </span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {estrusNotifications.map((notification, index) => {
            const building = buildings.find((item) => item.id === notification.buildingId);
            const daysLeft = notification.daysLeft ?? 0;

            return (
              <div
                key={notification.id}
                className="animate-fadeInUp"
                style={{
                  background: 'color-mix(in srgb, var(--color-surface-elevated) 80%, transparent)',
                  borderRadius: 'var(--radius-md)',
                  padding: '8px 14px',
                  fontSize: '13px',
                  border: '1px solid var(--color-surface-stroke, rgba(255,255,255,0.1))',
                  transition: 'all var(--transition-fast)',
                  animationDelay: `${150 + index * 50}ms`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'color-mix(in srgb, var(--color-surface-elevated) 90%, transparent)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'color-mix(in srgb, var(--color-surface-elevated) 80%, transparent)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <strong style={{ color: 'var(--color-estrus)' }}>{notification.cattleName}</strong> ·{' '}
                <span style={{ color: 'var(--color-text-secondary)' }}>{building?.name || '미지정'} {notification.penNumber}번</span> ·{' '}
                <span style={{ fontWeight: 700, color: 'var(--color-estrus)' }}>
                  {daysLeft === 0 ? ' ⚡오늘!' : `D-${daysLeft}`}
                </span>
              </div>
            );
          })}
        </div>
      </PremiumCardContent>
    </PremiumCard>
  );
}

// [QA 수정] 분만 알림 — CSS 변수 기반 색상 + 문자 깨짐(쨌→·) 수정
export function CalvingAlertBanner({ notifications = [], buildings = [] }) {
  const calvingNotifications = notifications.filter((notification) => notification.type === 'calving');

  if (calvingNotifications.length === 0) {
    return null;
  }

  return (
    <PremiumCard
      className="animate-fadeInUp mb-4"
      style={{ animationDelay: '150ms', borderColor: 'color-mix(in srgb, var(--color-calving) 24%, transparent)' }}
    >
      <PremiumCardContent className="p-4">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
          <span style={{ fontSize: '18px' }} className="animate-bounce">🍼</span>
          <span style={{ fontWeight: 700, fontSize: '15px', letterSpacing: '-0.3px' }}>
            분만 알림 — {calvingNotifications.length}두 분만 임박 (14일 이내)
          </span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {calvingNotifications.map((notification, index) => {
            const building = buildings.find((item) => item.id === notification.buildingId);
            const daysLeft = notification.daysLeft ?? 0;

            return (
              <div
                key={notification.id}
                className="animate-fadeInUp"
                style={{
                  background: 'color-mix(in srgb, var(--color-surface-elevated) 80%, transparent)',
                  borderRadius: 'var(--radius-md)',
                  padding: '8px 14px',
                  fontSize: '13px',
                  border: '1px solid var(--color-surface-stroke, rgba(255,255,255,0.1))',
                  transition: 'all var(--transition-fast)',
                  animationDelay: `${200 + index * 50}ms`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'color-mix(in srgb, var(--color-surface-elevated) 90%, transparent)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'color-mix(in srgb, var(--color-surface-elevated) 80%, transparent)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <strong style={{ color: 'var(--color-calving)' }}>{notification.cattleName}</strong> ·{' '}
                <span style={{ color: 'var(--color-text-secondary)' }}>{building?.name || '미지정'} {notification.penNumber}번</span> ·{' '}
                <span style={{ fontWeight: 700, color: 'var(--color-calving)' }}>D-{daysLeft}</span>{' '}
                <span style={{ color: 'var(--color-text-muted)' }}>· 예정 {notification.targetDate ? formatDate(notification.targetDate) : '-'}</span>
              </div>
            );
          })}
        </div>
      </PremiumCardContent>
    </PremiumCard>
  );
}
