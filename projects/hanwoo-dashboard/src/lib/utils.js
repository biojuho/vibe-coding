import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import {
	CALVING_ALERT_WINDOW,
	CALVING_DAYS,
	ESTRUS_ALERT_WINDOW,
	ESTRUS_CYCLE_DAYS,
} from "./constants.js";

const DAY_MS = 86400000;

export function cn(...inputs) {
	return twMerge(clsx(inputs));
}

function toDate(value) {
	return value instanceof Date ? new Date(value.getTime()) : new Date(value);
}

function toValidDate(value) {
	const date = toDate(value);
	return Number.isNaN(date.getTime()) ? null : date;
}

export function getMonthAge(birthDate, now = new Date()) {
	if (!birthDate) return 0;
	const date = toValidDate(birthDate);
	const today = toValidDate(now);
	if (!date || !today) return 0;
	return Math.max(
		1,
		(today.getFullYear() - date.getFullYear()) * 12 +
			today.getMonth() -
			date.getMonth(),
	);
}

export function getNextEstrusDate(lastEstrus, now = new Date()) {
	if (!lastEstrus) return null;
	const today = toValidDate(now);
	const next = toValidDate(lastEstrus);
	if (!today || !next) return null;

	while (next <= today) next.setDate(next.getDate() + ESTRUS_CYCLE_DAYS);

	return next;
}

export function getDaysUntilEstrus(lastEstrus, now = new Date()) {
	const today = toValidDate(now);
	if (!today) return null;
	const next = getNextEstrusDate(lastEstrus, today);
	return next ? Math.ceil((next - today) / DAY_MS) : null;
}

export function isEstrusAlert(lastEstrus, now = new Date()) {
	const days = getDaysUntilEstrus(lastEstrus, now);
	return days !== null && days >= 0 && days <= ESTRUS_ALERT_WINDOW;
}

export function isEstrusToday(lastEstrus, now = new Date()) {
	return getDaysUntilEstrus(lastEstrus, now) === 0;
}

export function getCalvingDate(pregnancyDate) {
	if (!pregnancyDate) return null;
	const date = toValidDate(pregnancyDate);
	return date ? new Date(date.getTime() + CALVING_DAYS * DAY_MS) : null;
}

export function getDaysUntilCalving(pregnancyDate, now = new Date()) {
	const today = toValidDate(now);
	if (!today) return null;
	const calvingDate = getCalvingDate(pregnancyDate);
	return calvingDate ? Math.ceil((calvingDate - today) / DAY_MS) : null;
}

export function isCalvingAlert(pregnancyDate, now = new Date()) {
	const days = getDaysUntilCalving(pregnancyDate, now);
	return days !== null && days >= 0 && days <= CALVING_ALERT_WINDOW;
}

export function formatDate(value) {
	if (!value) return "날짜 미등록";
	const date = toValidDate(value);
	return date ? date.toLocaleDateString("ko-KR") : "날짜 미등록";
}

// Format a date as YYYY-MM-DD using LOCAL calendar components, not UTC.
// Using toISOString() here shifts the day backwards for users east of UTC
// (e.g. KST 00:00–08:59 maps to the previous UTC day), which made "today"
// defaults and calendar cells render one day early for Korean users. Stored
// date-only values (UTC midnight) yield the same string in KST either way.
export function toLocalInputDate(date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
}

export function toInputDate(value) {
	if (!value) return "";
	const date = toValidDate(value);
	return date ? toLocalInputDate(date) : "";
}

export function formatForecastDateLabel(
	value,
	options = { month: "short", day: "numeric" },
) {
	const date = toValidDate(value);
	return date ? date.toLocaleDateString("ko-KR", options) : "날짜 미등록";
}

export function toFiniteNumber(value, fallback = 0) {
	const amount = Number(value);
	return Number.isFinite(amount) ? amount : fallback;
}

export function calcTHI(temp, humidity) {
	return 1.8 * temp + 32 - (0.55 - 0.0055 * humidity) * (1.8 * temp - 26);
}

export function getTHILevel(thi) {
	if (thi < 72) {
		return {
			label: "정상",
			color: "#7f9a76",
			bg: "#e7efe3",
			desc: "한우 활동에 적합한 안정 구간입니다.",
		};
	}

	if (thi < 78) {
		return {
			label: "주의",
			color: "#d39a63",
			bg: "#f7ead9",
			desc: "가벼운 스트레스 구간으로 환기 상태를 확인해 주세요.",
		};
	}

	if (thi < 89) {
		return {
			label: "경고",
			color: "#cf7f76",
			bg: "#f5e1dd",
			desc: "급수량을 확보하고 송풍을 강화해 주세요.",
		};
	}

	return {
		label: "위험",
		color: "#a54f49",
		bg: "#f1d7d3",
		desc: "즉시 냉방과 살수 조치를 진행해 주세요.",
	};
}

export function getWeatherIcon(code) {
	if (code === 0) return "☀️";
	if (code <= 3) return "⛅";
	if (code <= 48) return "🌫️";
	if (code <= 67) return "🌧️";
	if (code <= 77) return "❄️";
	return "⛈️";
}

export function getWeatherDesc(code) {
	if (code === 0) return "맑음";
	if (code <= 2) return "구름 조금";
	if (code === 3) return "흐림";
	if (code <= 48) return "안개";
	if (code <= 55) return "이슬비";
	if (code <= 65) return "비";
	if (code <= 75) return "눈";
	return "폭우";
}

export function formatMoney(value) {
	const amount = toFiniteNumber(value);
	return new Intl.NumberFormat("ko-KR").format(amount);
}

function isLivestockWeatherForecastDay(day) {
	return day && typeof day === "object" && !Array.isArray(day);
}

function normalizeLivestockWeatherForecast(forecast) {
	return Array.isArray(forecast)
		? forecast.filter(isLivestockWeatherForecastDay)
		: [];
}

export function getLivestockWeatherAlerts(forecast = []) {
	const alerts = [];
	const safeForecast = normalizeLivestockWeatherForecast(forecast);

	safeForecast.forEach((day) => {
		const label = formatForecastDateLabel(day.date);

		if (day.tempMax >= 35) {
			alerts.push({
				type: "heat",
				level: "danger",
				msg: `${label} 폭염 경보 (${day.tempMax}°C) - 냉방과 살수 조치를 진행해 주세요.`,
				icon: "🔥",
			});
		} else if (day.tempMax >= 33) {
			alerts.push({
				type: "heat",
				level: "warning",
				msg: `${label} 고온 주의 (${day.tempMax}°C) - 환기와 급수 상태를 강화해 주세요.`,
				icon: "🌡️",
			});
		}

		if (day.tempMin <= -10) {
			alerts.push({
				type: "cold",
				level: "danger",
				msg: `${label} 한파 경보 (${day.tempMin}°C) - 보온 설비를 점검해 주세요.`,
				icon: "🥶",
			});
		} else if (day.tempMin <= -5) {
			alerts.push({
				type: "cold",
				level: "warning",
				msg: `${label} 저온 주의 (${day.tempMin}°C) - 보온 상태를 확인해 주세요.`,
				icon: "🧣",
			});
		}

		if (day.precipProb >= 80) {
			alerts.push({
				type: "rain",
				level: "warning",
				msg: `${label} 강수 확률 ${day.precipProb}% - 축사 누수와 바닥 상태를 점검해 주세요.`,
				icon: "🌧️",
			});
		}
	});

	return alerts;
}
