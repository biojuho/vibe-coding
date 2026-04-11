'use client';

import { PremiumCard, PremiumCardContent } from '@/components/ui/premium-card';
import { HeartIcon } from '@/components/ui/common';
import { formatDate } from '@/lib/utils';

export function EstrusAlertBanner({ notifications = [], buildings = [] }) {
  const estrusNotifications = notifications.filter((notification) => notification.type === 'estrus');

  if (estrusNotifications.length === 0) {
    return null;
  }

  const todayCount = estrusNotifications.filter((notification) => notification.daysLeft === 0).length;

  return (
    <PremiumCard className="animate-fadeInUp mb-4 bg-pink-900/10 border-pink-500/20" style={{ animationDelay: '100ms' }}>
      <PremiumCardContent className="p-4">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
          <span className="alert-icon"><HeartIcon /></span>
          <span style={{ fontWeight: 700, fontSize: '15px', letterSpacing: '-0.3px' }}>
            발정 알림 {todayCount > 0 ? `오늘 ${todayCount}두` : `${estrusNotifications.length}두 임박`}
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
                  background: 'rgba(255,255,255,0.05)',
                  borderRadius: 'var(--radius-md)',
                  padding: '8px 14px',
                  fontSize: '13px',
                  border: '1px solid rgba(255,255,255,0.1)',
                  transition: 'all var(--transition-fast)',
                  animationDelay: `${150 + index * 50}ms`,
                }}
              >
                <strong className="text-pink-300">{notification.cattleName}</strong> 쨌{' '}
                <span className="text-slate-300">{building?.name || '미지정'} {notification.penNumber}번</span> 쨌{' '}
                <span style={{ fontWeight: 700 }} className="text-pink-400">
                  {daysLeft === 0 ? '오늘' : `D-${daysLeft}`}
                </span>
              </div>
            );
          })}
        </div>
      </PremiumCardContent>
    </PremiumCard>
  );
}

export function CalvingAlertBanner({ notifications = [], buildings = [] }) {
  const calvingNotifications = notifications.filter((notification) => notification.type === 'calving');

  if (calvingNotifications.length === 0) {
    return null;
  }

  return (
    <PremiumCard className="animate-fadeInUp mb-4 bg-indigo-900/10 border-indigo-500/20" style={{ animationDelay: '150ms' }}>
      <PremiumCardContent className="p-4">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
          <span style={{ fontSize: '18px' }} className="animate-bounce">?</span>
          <span style={{ fontWeight: 700, fontSize: '15px', letterSpacing: '-0.3px' }}>
            분만 알림 {calvingNotifications.length}두 임박
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
                  background: 'rgba(255,255,255,0.05)',
                  borderRadius: 'var(--radius-md)',
                  padding: '8px 14px',
                  fontSize: '13px',
                  border: '1px solid rgba(255,255,255,0.1)',
                  transition: 'all var(--transition-fast)',
                  animationDelay: `${200 + index * 50}ms`,
                }}
              >
                <strong className="text-indigo-300">{notification.cattleName}</strong> 쨌{' '}
                <span className="text-slate-300">{building?.name || '미지정'} {notification.penNumber}번</span> 쨌{' '}
                <span style={{ fontWeight: 700 }} className="text-indigo-400">D-{daysLeft}</span>{' '}
                <span className="text-slate-400">쨌 예정 {notification.targetDate ? formatDate(notification.targetDate) : '-'}</span>
              </div>
            );
          })}
        </div>
      </PremiumCardContent>
    </PremiumCard>
  );
}
