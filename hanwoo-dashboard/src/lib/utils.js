import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { TODAY, ESTRUS_CYCLE_DAYS, ESTRUS_ALERT_WINDOW, CALVING_DAYS, CALVING_ALERT_WINDOW } from './constants';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function getMonthAge(bd) {
  if (!bd) return 0;
  const d = bd instanceof Date ? bd : new Date(bd);
  return Math.max(1, (TODAY.getFullYear()-d.getFullYear())*12 + TODAY.getMonth()-d.getMonth());
}
export function getNextEstrusDate(le) {
  if (!le) return null;
  const n = new Date(le instanceof Date ? le : new Date(le));
  while (n <= TODAY) n.setDate(n.getDate() + ESTRUS_CYCLE_DAYS);
  return n;
}
export function getDaysUntilEstrus(le) {
  const n = getNextEstrusDate(le); return n ? Math.ceil((n - TODAY) / 86400000) : null;
}
export function isEstrusAlert(le) { const d = getDaysUntilEstrus(le); return d !== null && d >= 0 && d <= ESTRUS_ALERT_WINDOW; }
export function isEstrusToday(le) { return getDaysUntilEstrus(le) === 0; }

export function getCalvingDate(pregnancyDate) {
  if (!pregnancyDate) return null;
  return new Date(new Date(pregnancyDate).getTime() + CALVING_DAYS * 86400000);
}
export function getDaysUntilCalving(pregnancyDate) {
  const cd = getCalvingDate(pregnancyDate);
  return cd ? Math.ceil((cd - TODAY) / 86400000) : null;
}
export function isCalvingAlert(pregnancyDate) {
  const d = getDaysUntilCalving(pregnancyDate);
  return d !== null && d >= 0 && d <= CALVING_ALERT_WINDOW;
}

export function formatDate(d) { if (!d) return "-"; return (d instanceof Date ? d : new Date(d)).toLocaleDateString("ko-KR"); }
export function toInputDate(d) { if (!d) return ""; return (d instanceof Date ? d : new Date(d)).toISOString().split("T")[0]; }
export function calcTHI(t, h) { return (1.8*t+32)-(0.55-0.0055*h)*(1.8*t-26); }
export function getTHILevel(thi) {
  if (thi<72) return {label:"정상",color:"#4CAF50",bg:"#E8F5E9",desc:"한우 활동에 적합한 환경"};
  if (thi<78) return {label:"주의",color:"#FF9800",bg:"#FFF3E0",desc:"경미한 스트레스, 환기 확인"};
  if (thi<89) return {label:"경고",color:"#F44336",bg:"#FFEBEE",desc:"급수량 증가, 환기 강화 필요"};
  return {label:"위험",color:"#B71C1C",bg:"#FFCDD2",desc:"긴급 냉방/살수 필요"};
}
export function getWeatherIcon(c) { if(c===0)return"☀️";if(c<=3)return"⛅";if(c<=48)return"🌫️";if(c<=67)return"🌧️";if(c<=77)return"🌨️";return"⛈️"; }
export function getWeatherDesc(c) { if(c===0)return"맑음";if(c<=2)return"구름 조금";if(c===3)return"흐림";if(c<=48)return"안개";if(c<=55)return"이슬비";if(c<=65)return"비";if(c<=75)return"눈";return"뇌우"; }
export function formatMoney(n) { return new Intl.NumberFormat('ko-KR').format(n); }

export function getLivestockWeatherAlerts(forecast = []) {
  const alerts = [];
  forecast.forEach(day => {
    const label = new Date(day.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
    if (day.tempMax >= 35) alerts.push({ type: 'heat', level: 'danger', msg: `${label} 폭염 경보 (${day.tempMax}°C) - 냉방/살수 필요`, icon: '🥵' });
    else if (day.tempMax >= 33) alerts.push({ type: 'heat', level: 'warning', msg: `${label} 고온 주의 (${day.tempMax}°C) - 환기 강화`, icon: '🌡️' });
    if (day.tempMin <= -10) alerts.push({ type: 'cold', level: 'danger', msg: `${label} 한파 경보 (${day.tempMin}°C) - 보온 필수`, icon: '🥶' });
    else if (day.tempMin <= -5) alerts.push({ type: 'cold', level: 'warning', msg: `${label} 저온 주의 (${day.tempMin}°C) - 보온 확인`, icon: '❄️' });
    if (day.precipProb >= 80) alerts.push({ type: 'rain', level: 'warning', msg: `${label} 강수 확률 ${day.precipProb}% - 축사 점검`, icon: '🌧️' });
  });
  return alerts;
}
