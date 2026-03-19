import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import {
  TODAY,
  ESTRUS_CYCLE_DAYS,
  ESTRUS_ALERT_WINDOW,
  CALVING_DAYS,
  CALVING_ALERT_WINDOW,
} from './constants';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function getMonthAge(birthDate) {
  if (!birthDate) return 0;
  const date = birthDate instanceof Date ? birthDate : new Date(birthDate);
  return Math.max(1, (TODAY.getFullYear() - date.getFullYear()) * 12 + TODAY.getMonth() - date.getMonth());
}

export function getNextEstrusDate(lastEstrus) {
  if (!lastEstrus) return null;
  const next = new Date(lastEstrus instanceof Date ? lastEstrus : new Date(lastEstrus));

  while (next <= TODAY) next.setDate(next.getDate() + ESTRUS_CYCLE_DAYS);

  return next;
}

export function getDaysUntilEstrus(lastEstrus) {
  const next = getNextEstrusDate(lastEstrus);
  return next ? Math.ceil((next - TODAY) / 86400000) : null;
}

export function isEstrusAlert(lastEstrus) {
  const days = getDaysUntilEstrus(lastEstrus);
  return days !== null && days >= 0 && days <= ESTRUS_ALERT_WINDOW;
}

export function isEstrusToday(lastEstrus) {
  return getDaysUntilEstrus(lastEstrus) === 0;
}

export function getCalvingDate(pregnancyDate) {
  if (!pregnancyDate) return null;
  return new Date(new Date(pregnancyDate).getTime() + CALVING_DAYS * 86400000);
}

export function getDaysUntilCalving(pregnancyDate) {
  const calvingDate = getCalvingDate(pregnancyDate);
  return calvingDate ? Math.ceil((calvingDate - TODAY) / 86400000) : null;
}

export function isCalvingAlert(pregnancyDate) {
  const days = getDaysUntilCalving(pregnancyDate);
  return days !== null && days >= 0 && days <= CALVING_ALERT_WINDOW;
}

export function formatDate(value) {
  if (!value) return '-';
  return (value instanceof Date ? value : new Date(value)).toLocaleDateString('ko-KR');
}

export function toInputDate(value) {
  if (!value) return '';
  return (value instanceof Date ? value : new Date(value)).toISOString().split('T')[0];
}

export function calcTHI(temp, humidity) {
  return (1.8 * temp + 32) - (0.55 - 0.0055 * humidity) * (1.8 * temp - 26);
}

export function getTHILevel(thi) {
  if (thi < 72) {
    return {
      label: '정상',
      color: '#7f9a76',
      bg: '#e7efe3',
      desc: '한우 활동에 적합한 안정 구간입니다.',
    };
  }

  if (thi < 78) {
    return {
      label: '주의',
      color: '#d39a63',
      bg: '#f7ead9',
      desc: '가벼운 스트레스 구간으로 환기 상태를 확인하세요.',
    };
  }

  if (thi < 89) {
    return {
      label: '경고',
      color: '#cf7f76',
      bg: '#f5e1dd',
      desc: '급수량 확보와 송풍 강화가 필요한 수준입니다.',
    };
  }

  return {
    label: '위험',
    color: '#a54f49',
    bg: '#f1d7d3',
    desc: '즉시 냉방과 살수 조치가 필요한 고위험 상태입니다.',
  };
}

export function getWeatherIcon(code) {
  if (code === 0) return '☀️';
  if (code <= 3) return '⛅';
  if (code <= 48) return '🌫️';
  if (code <= 67) return '🌧️';
  if (code <= 77) return '❄️';
  return '⛈️';
}

export function getWeatherDesc(code) {
  if (code === 0) return '맑음';
  if (code <= 2) return '구름 조금';
  if (code === 3) return '흐림';
  if (code <= 48) return '안개';
  if (code <= 55) return '이슬비';
  if (code <= 65) return '비';
  if (code <= 75) return '눈';
  return '폭우';
}

export function formatMoney(value) {
  return new Intl.NumberFormat('ko-KR').format(value);
}

export function getLivestockWeatherAlerts(forecast = []) {
  const alerts = [];

  forecast.forEach((day) => {
    const label = new Date(day.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });

    if (day.tempMax >= 35) {
      alerts.push({
        type: 'heat',
        level: 'danger',
        msg: `${label} 폭염 경보 (${day.tempMax}°C) - 냉방과 살수 조치가 필요합니다.`,
        icon: '🔥',
      });
    } else if (day.tempMax >= 33) {
      alerts.push({
        type: 'heat',
        level: 'warning',
        msg: `${label} 고온 주의 (${day.tempMax}°C) - 환기와 급수 상태를 강화하세요.`,
        icon: '🌡️',
      });
    }

    if (day.tempMin <= -10) {
      alerts.push({
        type: 'cold',
        level: 'danger',
        msg: `${label} 한파 경보 (${day.tempMin}°C) - 보온 설비 점검이 필요합니다.`,
        icon: '🥶',
      });
    } else if (day.tempMin <= -5) {
      alerts.push({
        type: 'cold',
        level: 'warning',
        msg: `${label} 저온 주의 (${day.tempMin}°C) - 보온 상태를 확인하세요.`,
        icon: '🧣',
      });
    }

    if (day.precipProb >= 80) {
      alerts.push({
        type: 'rain',
        level: 'warning',
        msg: `${label} 강수 확률 ${day.precipProb}% - 축사 누수와 바닥 상태를 점검하세요.`,
        icon: '🌧️',
      });
    }
  });

  return alerts;
}
