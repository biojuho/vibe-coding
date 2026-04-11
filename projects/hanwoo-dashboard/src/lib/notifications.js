import {
  getDaysUntilCalving,
  getDaysUntilEstrus,
  isCalvingAlert,
  isEstrusAlert,
} from './utils';
import { buildNotificationTiming } from './notification-timing.mjs';

export function buildNotifications(cattle = []) {
  const notifications = [];

  cattle.forEach((cow) => {
    if ((cow.status === '번식우' || cow.status === '육성우') && cow.lastEstrus && isEstrusAlert(cow.lastEstrus)) {
      const daysLeft = getDaysUntilEstrus(cow.lastEstrus);
      const timing = buildNotificationTiming('estrus', cow.lastEstrus);

      notifications.push({
        id: `estrus-${cow.id}`,
        type: 'estrus',
        level: daysLeft <= 1 ? 'critical' : 'warning',
        title: daysLeft === 0 ? '오늘 발정 예정' : '발정 임박',
        message: `${cow.name} (${cow.tagNumber}) 발정 예정일이 ${daysLeft}일 남았습니다.`,
        daysLeft,
        cattleId: cow.id,
        cattleName: cow.name,
        tagNumber: cow.tagNumber,
        buildingId: cow.buildingId,
        penNumber: cow.penNumber,
        ...timing,
      });
    }

    if (cow.status === '임신우' && cow.pregnancyDate && isCalvingAlert(cow.pregnancyDate)) {
      const daysLeft = getDaysUntilCalving(cow.pregnancyDate);
      const timing = buildNotificationTiming('calving', cow.pregnancyDate);

      notifications.push({
        id: `calving-${cow.id}`,
        type: 'calving',
        level: daysLeft <= 3 ? 'critical' : 'warning',
        title: daysLeft === 0 ? '오늘 분만 예정' : '분만 임박',
        message: `${cow.name} (${cow.tagNumber}) 분만 예정일이 ${daysLeft}일 남았습니다.`,
        daysLeft,
        cattleId: cow.id,
        cattleName: cow.name,
        tagNumber: cow.tagNumber,
        buildingId: cow.buildingId,
        penNumber: cow.penNumber,
        ...timing,
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
