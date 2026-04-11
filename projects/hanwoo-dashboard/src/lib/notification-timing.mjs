const ESTRUS_CYCLE_DAYS = 21;
const CALVING_DAYS = 285;

function parseDate(value) {
  if (!value) {
    return null;
  }

  const parsed = value instanceof Date ? new Date(value.getTime()) : new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function addDays(value, dayCount) {
  const parsed = parseDate(value);
  if (!parsed) {
    return null;
  }

  parsed.setDate(parsed.getDate() + dayCount);
  return parsed;
}

export function formatNotificationTime(value) {
  const parsed = parseDate(value);
  if (!parsed) {
    return '-';
  }

  return parsed.toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getNotificationTargetDate(type, sourceDate, { now = new Date() } = {}) {
  if (type === 'estrus') {
    const nextEstrusDate = parseDate(sourceDate);
    const referenceNow = parseDate(now);
    if (!nextEstrusDate || !referenceNow) {
      return null;
    }

    while (nextEstrusDate <= referenceNow) {
      nextEstrusDate.setDate(nextEstrusDate.getDate() + ESTRUS_CYCLE_DAYS);
    }

    return nextEstrusDate;
  }

  if (type === 'calving') {
    return addDays(sourceDate, CALVING_DAYS);
  }

  return parseDate(sourceDate);
}

export function buildNotificationTiming(type, sourceDate, options) {
  const targetDate = getNotificationTargetDate(type, sourceDate, options);
  if (!targetDate) {
    return {
      date: null,
      time: '-',
      targetDate: null,
    };
  }

  const isoString = targetDate.toISOString();
  return {
    date: isoString,
    time: formatNotificationTime(targetDate),
    targetDate: isoString,
  };
}
