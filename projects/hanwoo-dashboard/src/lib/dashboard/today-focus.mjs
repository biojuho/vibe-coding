function startOfDay(value) {
  const date = value instanceof Date ? new Date(value) : new Date(value);
  date.setHours(0, 0, 0, 0);
  return date;
}

function toValidDate(value) {
  const date = value instanceof Date ? new Date(value.getTime()) : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function isLowStock(item) {
  return item?.threshold !== null && item?.threshold !== undefined && Number(item.quantity) <= Number(item.threshold);
}

function formatDaysLeft(target, today) {
  const daysLeft = Math.ceil((startOfDay(target) - today) / 86400000);
  if (daysLeft <= 0) return '오늘';
  if (daysLeft === 1) return '내일';
  return `D-${daysLeft}`;
}

export function buildTodayFocusItems({
  notifications = [],
  scheduleEvents = [],
  inventoryList = [],
  monthlySalesCount = 0,
  isOnline = true,
  now = new Date(),
} = {}) {
  const today = startOfDay(now);
  const items = [];

  if (!isOnline) {
    items.push({
      id: 'offline',
      type: 'offline',
      title: '오프라인 작업 대기',
      detail: '연결이 복구되면 저장된 작업을 자동 동기화합니다.',
      meta: '동기화 확인',
      tone: 'warning',
      targetTab: 'settings',
    });
  }

  const criticalNotifications = notifications.filter((notification) => notification.level === 'critical');
  if (criticalNotifications.length > 0) {
    const first = criticalNotifications[0];
    items.push({
      id: 'critical-alerts',
      type: 'alert',
      title: `${criticalNotifications.length}건의 긴급 알림`,
      detail: first.message || first.title || '발정/분만 알림을 확인해 주세요.',
      meta: '알림 보기',
      tone: 'danger',
      targetTab: 'home',
    });
  }

  const nextEvent = scheduleEvents
    .map((event) => ({ event, date: toValidDate(event.date) }))
    .filter(({ event, date }) => date && !event.isCompleted && date >= today)
    .sort((first, second) => first.date - second.date)[0]?.event;
  if (nextEvent) {
    items.push({
      id: 'next-schedule',
      type: 'schedule',
      title: nextEvent.title,
      detail: `${formatDaysLeft(nextEvent.date, today)} 예정`,
      meta: '일정 열기',
      tone: 'info',
      targetTab: 'schedule',
    });
  }

  const lowStockItems = inventoryList.filter(isLowStock);
  if (lowStockItems.length > 0) {
    const first = lowStockItems[0];
    items.push({
      id: 'low-stock',
      type: 'stock',
      title: `${lowStockItems.length}개 재고 부족`,
      detail: `${first.name}: ${first.quantity}${first.unit || ''} 남음`,
      meta: '재고 보충',
      tone: 'warning',
      targetTab: 'inventory',
    });
  }

  items.push({
    id: 'monthly-sales',
    type: 'sales',
    title: `이번 달 출하 ${monthlySalesCount}두`,
    detail: monthlySalesCount > 0 ? '매출 흐름을 분석 탭에서 확인하세요.' : '출하 기록을 추가하면 월간 흐름이 살아납니다.',
    meta: monthlySalesCount > 0 ? '분석 보기' : '출하 기록',
    tone: monthlySalesCount > 0 ? 'success' : 'neutral',
    targetTab: monthlySalesCount > 0 ? 'analysis' : 'sales',
  });

  return items.slice(0, 4);
}
