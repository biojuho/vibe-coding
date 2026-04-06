import {
  getDaysUntilCalving,
  getDaysUntilEstrus,
  isCalvingAlert,
  isEstrusAlert,
} from './utils';

function formatNotificationTime(value) {
  return new Date(value).toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function buildNotifications(cattle = []) {
  const notifications = [];

  cattle.forEach((cow) => {
    if ((cow.status === '번식우' || cow.status === '육성우') && cow.lastEstrus && isEstrusAlert(cow.lastEstrus)) {
      const daysLeft = getDaysUntilEstrus(cow.lastEstrus);
      const createdAt = new Date();

      notifications.push({
        id: `estrus-${cow.id}`,
        type: 'estrus',
        level: daysLeft <= 1 ? 'critical' : 'warning',
        title: daysLeft === 0 ? '오늘 발정 예정' : '발정 임박',
        message: `${cow.name} (${cow.tagNumber}) 발정 예정일이 ${daysLeft}일 남았습니다.`,
        date: createdAt.toISOString(),
        time: formatNotificationTime(createdAt),
      });
    }

    if (cow.status === '임신우' && cow.pregnancyDate && isCalvingAlert(cow.pregnancyDate)) {
      const daysLeft = getDaysUntilCalving(cow.pregnancyDate);
      const createdAt = new Date();

      notifications.push({
        id: `calving-${cow.id}`,
        type: 'calving',
        level: daysLeft <= 3 ? 'critical' : 'warning',
        title: daysLeft === 0 ? '오늘 분만 예정' : '분만 임박',
        message: `${cow.name} (${cow.tagNumber}) 분만 예정일이 ${daysLeft}일 남았습니다.`,
        date: createdAt.toISOString(),
        time: formatNotificationTime(createdAt),
      });
    }
  });

  notifications.sort((a, b) => {
    if (a.level === 'critical' && b.level !== 'critical') return -1;
    if (a.level !== 'critical' && b.level === 'critical') return 1;
    return 0;
  });

  return notifications;
}
