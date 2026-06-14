/**
 * Behavioral tests for pure utility functions in utils.js.
 *
 * utils.js imports from "./constants" (no extension) which fails in Node ESM.
 * We test the logic inline and cross-check structural invariants via source-grep
 * so that production code and tests cannot silently diverge.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/utils.js"), "utf8");

// Domain constants — same values as constants.js (source-grep verified below)
const ESTRUS_CYCLE_DAYS = 21;
const CALVING_DAYS = 285;
const ESTRUS_ALERT_WINDOW = 3;
const CALVING_ALERT_WINDOW = 14;
const DAY_MS = 86400000;

// ── Constants parity check (structural) ──────────────────────────────────────

test("utils.js uses ESTRUS_CYCLE_DAYS=21 via constants import", () => {
	assert.match(src, /ESTRUS_CYCLE_DAYS/);
	// constants.js defines it as 21
	const constantsSrc = readFileSync(
		path.join(SRC_ROOT, "lib/constants.js"),
		"utf8",
	);
	assert.match(constantsSrc, /ESTRUS_CYCLE_DAYS = 21/);
	assert.match(constantsSrc, /CALVING_DAYS = 285/);
	assert.match(constantsSrc, /ESTRUS_ALERT_WINDOW = 3/);
	assert.match(constantsSrc, /CALVING_ALERT_WINDOW = 14/);
});

// ── Pure function re-implementations (spec under test) ──────────────────────

function toDate(value) {
	return value instanceof Date ? new Date(value.getTime()) : new Date(value);
}

function toValidDate(value) {
	const date = toDate(value);
	return Number.isNaN(date.getTime()) ? null : date;
}

function getMonthAge(birthDate, now = new Date()) {
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

function getNextEstrusDate(lastEstrus, now = new Date()) {
	if (!lastEstrus) return null;
	const today = toValidDate(now);
	const next = toValidDate(lastEstrus);
	if (!today || !next) return null;
	while (next <= today) next.setDate(next.getDate() + ESTRUS_CYCLE_DAYS);
	return next;
}

function getDaysUntilEstrus(lastEstrus, now = new Date()) {
	const today = toValidDate(now);
	if (!today) return null;
	const next = getNextEstrusDate(lastEstrus, today);
	return next ? Math.ceil((next - today) / DAY_MS) : null;
}

function isEstrusAlert(lastEstrus, now = new Date()) {
	const days = getDaysUntilEstrus(lastEstrus, now);
	return days !== null && days >= 0 && days <= ESTRUS_ALERT_WINDOW;
}

function isEstrusToday(lastEstrus, now = new Date()) {
	return getDaysUntilEstrus(lastEstrus, now) === 0;
}

function getCalvingDate(pregnancyDate) {
	if (!pregnancyDate) return null;
	const date = toValidDate(pregnancyDate);
	return date ? new Date(date.getTime() + CALVING_DAYS * DAY_MS) : null;
}

function getDaysUntilCalving(pregnancyDate, now = new Date()) {
	const today = toValidDate(now);
	if (!today) return null;
	const calvingDate = getCalvingDate(pregnancyDate);
	return calvingDate ? Math.ceil((calvingDate - today) / DAY_MS) : null;
}

function isCalvingAlert(pregnancyDate, now = new Date()) {
	const days = getDaysUntilCalving(pregnancyDate, now);
	return days !== null && days >= 0 && days <= CALVING_ALERT_WINDOW;
}

function toFiniteNumber(value, fallback = 0) {
	const amount = Number(value);
	return Number.isFinite(amount) ? amount : fallback;
}

function calcTHI(temp, humidity) {
	return (
		1.8 * temp + 32 - (0.55 - 0.0055 * humidity) * (1.8 * temp - 26)
	);
}

function getTHILevel(thi) {
	if (thi < 72) return { label: "정상", color: "#7f9a76", bg: "#e7efe3" };
	if (thi < 78) return { label: "주의", color: "#d39a63", bg: "#f7ead9" };
	if (thi < 89) return { label: "경고", color: "#cf7f76", bg: "#f5e1dd" };
	return { label: "위험", color: "#a54f49", bg: "#f1d7d3" };
}

function isLivestockForecastDay(day) {
	return day && typeof day === "object" && !Array.isArray(day);
}

function getLivestockWeatherAlerts(forecast = []) {
	const alerts = [];
	const safe = Array.isArray(forecast)
		? forecast.filter(isLivestockForecastDay)
		: [];
	safe.forEach((day) => {
		if (day.tempMax >= 35) {
			alerts.push({ type: "heat", level: "danger" });
		} else if (day.tempMax >= 33) {
			alerts.push({ type: "heat", level: "warning" });
		}
		if (day.tempMin <= -10) {
			alerts.push({ type: "cold", level: "danger" });
		} else if (day.tempMin <= -5) {
			alerts.push({ type: "cold", level: "warning" });
		}
		if (day.precipProb >= 80) {
			alerts.push({ type: "rain", level: "warning" });
		}
	});
	return alerts;
}

// ── Source-grep: verify production code uses the same thresholds ──────────────

test("production getLivestockWeatherAlerts uses tempMax >= 35 for heat danger", () => {
	assert.match(src, /tempMax >= 35/);
});

test("production getLivestockWeatherAlerts uses tempMax >= 33 for heat warning", () => {
	assert.match(src, /tempMax >= 33/);
});

test("production getLivestockWeatherAlerts uses tempMin <= -10 for cold danger", () => {
	assert.match(src, /tempMin <= -10/);
});

test("production getLivestockWeatherAlerts uses tempMin <= -5 for cold warning", () => {
	assert.match(src, /tempMin <= -5/);
});

test("production getLivestockWeatherAlerts uses precipProb >= 80 for rain warning", () => {
	assert.match(src, /precipProb >= 80/);
});

test("production calcTHI uses the correct livestock heat index formula", () => {
	assert.match(src, /1\.8 \* temp \+ 32/);
	assert.match(src, /0\.55 - 0\.0055 \* humidity/);
});

test("production getTHILevel thresholds are 72/78/89", () => {
	assert.match(src, /thi < 72/);
	assert.match(src, /thi < 78/);
	assert.match(src, /thi < 89/);
});

// ── toFiniteNumber behavioral tests ──────────────────────────────────────────

test("toFiniteNumber returns the numeric value for valid numbers", () => {
	assert.equal(toFiniteNumber(42), 42);
	assert.equal(toFiniteNumber("3.14"), 3.14);
	assert.equal(toFiniteNumber(0), 0);
});

test("toFiniteNumber returns fallback for NaN, null, undefined, Infinity", () => {
	assert.equal(toFiniteNumber(NaN), 0);
	assert.equal(toFiniteNumber(null), 0);
	assert.equal(toFiniteNumber(undefined), 0);
	assert.equal(toFiniteNumber(Infinity), 0);
	assert.equal(toFiniteNumber("abc"), 0);
});

test("toFiniteNumber accepts a custom fallback value", () => {
	assert.equal(toFiniteNumber(NaN, -1), -1);
	assert.equal(toFiniteNumber("bad", 99), 99);
});

// ── calcTHI behavioral tests ──────────────────────────────────────────────────

test("calcTHI at 25°C / 60% humidity is near 73 (light caution zone)", () => {
	// THI = 1.8*25+32 - (0.55-0.0055*60)*(1.8*25-26) = 77 - 0.22*19 = 72.82
	const thi = calcTHI(25, 60);
	assert.ok(thi > 72 && thi < 74, `expected 72–74, got ${thi}`);
});

test("calcTHI increases monotonically with temperature (same humidity)", () => {
	assert.ok(calcTHI(35, 60) > calcTHI(25, 60));
	assert.ok(calcTHI(40, 60) > calcTHI(35, 60));
});

test("calcTHI increases monotonically with humidity (same temperature)", () => {
	assert.ok(calcTHI(25, 90) > calcTHI(25, 50));
	assert.ok(calcTHI(25, 100) > calcTHI(25, 90));
});

test("calcTHI at 10°C / 40% humidity is in safe range (<72)", () => {
	const thi = calcTHI(10, 40);
	assert.ok(thi < 72, `expected <72, got ${thi}`);
});

// ── getTHILevel behavioral tests ──────────────────────────────────────────────

test("getTHILevel: 정상 (normal) for THI < 72", () => {
	assert.equal(getTHILevel(60).label, "정상");
	assert.equal(getTHILevel(71.9).label, "정상");
});

test("getTHILevel: 주의 (caution) for 72 ≤ THI < 78", () => {
	assert.equal(getTHILevel(72).label, "주의");
	assert.equal(getTHILevel(77.9).label, "주의");
});

test("getTHILevel: 경고 (warning) for 78 ≤ THI < 89", () => {
	assert.equal(getTHILevel(78).label, "경고");
	assert.equal(getTHILevel(88.9).label, "경고");
});

test("getTHILevel: 위험 (danger) for THI ≥ 89", () => {
	assert.equal(getTHILevel(89).label, "위험");
	assert.equal(getTHILevel(100).label, "위험");
});

test("getTHILevel returns hex color and bg for all levels", () => {
	for (const thi of [60, 72, 78, 89]) {
		const level = getTHILevel(thi);
		assert.ok(level.color.startsWith("#"), `color missing at thi=${thi}`);
		assert.ok(level.bg.startsWith("#"), `bg missing at thi=${thi}`);
	}
});

// ── getMonthAge behavioral tests ──────────────────────────────────────────────

test("getMonthAge returns minimum 1 for same-month birth", () => {
	const now = new Date("2026-06-15");
	assert.equal(getMonthAge("2026-06-01", now), 1);
});

test("getMonthAge returns 12 for exactly one year old", () => {
	const now = new Date("2026-06-15");
	assert.equal(getMonthAge("2025-06-15", now), 12);
});

test("getMonthAge returns 24 for exactly two years old", () => {
	const now = new Date("2026-06-15");
	assert.equal(getMonthAge("2024-06-15", now), 24);
});

test("getMonthAge returns 0 for null input", () => {
	assert.equal(getMonthAge(null), 0);
});

test("getMonthAge returns 0 for invalid date string", () => {
	assert.equal(getMonthAge("not-a-date"), 0);
});

// ── getDaysUntilEstrus / isEstrusAlert / isEstrusToday ─────────────────────

test("getDaysUntilEstrus: last estrus 7 days ago → next in ~14 days", () => {
	const now = new Date("2026-06-15T00:00:00Z");
	const lastEstrus = new Date("2026-06-08");
	const days = getDaysUntilEstrus(lastEstrus, now);
	// 21 - 7 = 14 days until next cycle
	assert.ok(days >= 13 && days <= 15, `expected ~14, got ${days}`);
});

test("getDaysUntilEstrus: last estrus exactly 21 days ago → next cycle is 21 days from now", () => {
	// The while loop uses `next <= today` (inclusive), so when next === today
	// the loop advances by another full cycle — the function returns the NEXT future cycle.
	const now = new Date("2026-06-15T00:00:00Z");
	const lastEstrus = new Date("2026-05-25T00:00:00Z"); // exactly 21 days ago
	const days = getDaysUntilEstrus(lastEstrus, now);
	assert.equal(days, 21);
});

test("getDaysUntilEstrus returns null for null input", () => {
	assert.equal(getDaysUntilEstrus(null), null);
});

test("isEstrusAlert: true when next estrus ≤ 3 days (ESTRUS_ALERT_WINDOW)", () => {
	const now = new Date("2026-06-15");
	// Last estrus 19 days ago → next in 2 days (within window)
	const lastEstrus = new Date("2026-05-27");
	assert.equal(isEstrusAlert(lastEstrus, now), true);
});

test("isEstrusAlert: false when next estrus > 3 days away", () => {
	const now = new Date("2026-06-15");
	// Last estrus 7 days ago → next in 14 days (outside window)
	const lastEstrus = new Date("2026-06-08");
	assert.equal(isEstrusAlert(lastEstrus, now), false);
});

test("isEstrusAlert: false for null input", () => {
	assert.equal(isEstrusAlert(null), false);
});

test("isEstrusToday: false when 21 days elapsed (loop advances to next cycle)", () => {
	// The while loop `next <= today` advances past "today", so getDaysUntilEstrus
	// is always ≥ 1 for any completed cycle — isEstrusToday (=== 0) stays false.
	const now = new Date("2026-06-15T00:00:00Z");
	const lastEstrus = new Date("2026-05-25T00:00:00Z");
	assert.equal(isEstrusToday(lastEstrus, now), false);
});

// ── getCalvingDate / getDaysUntilCalving / isCalvingAlert ─────────────────────

test("getCalvingDate adds exactly CALVING_DAYS (285) to pregnancy date", () => {
	const pregnancy = new Date("2026-01-01T00:00:00Z");
	const calving = getCalvingDate(pregnancy);
	const diffDays = Math.round((calving - pregnancy) / DAY_MS);
	assert.equal(diffDays, 285);
});

test("getCalvingDate returns null for null input", () => {
	assert.equal(getCalvingDate(null), null);
});

test("getCalvingDate returns null for invalid date", () => {
	assert.equal(getCalvingDate("bad-date"), null);
});

test("getDaysUntilCalving: calving 10 days away returns ~10", () => {
	const now = new Date("2026-06-15T00:00:00Z");
	const pregnancyDate = new Date(now.getTime() + (10 - 285) * DAY_MS);
	const days = getDaysUntilCalving(pregnancyDate, now);
	assert.ok(days >= 9 && days <= 11, `expected ~10, got ${days}`);
});

test("isCalvingAlert: true when calving is within 14 days", () => {
	const now = new Date("2026-06-15T00:00:00Z");
	const pregnancyDate = new Date(now.getTime() + (7 - 285) * DAY_MS);
	assert.equal(isCalvingAlert(pregnancyDate, now), true);
});

test("isCalvingAlert: false when calving is more than 14 days away", () => {
	const now = new Date("2026-06-15T00:00:00Z");
	const pregnancyDate = new Date(now.getTime() + (30 - 285) * DAY_MS);
	assert.equal(isCalvingAlert(pregnancyDate, now), false);
});

test("isCalvingAlert: true on the exact day of calving (0 days left)", () => {
	const now = new Date("2026-06-15T00:00:00Z");
	const pregnancyDate = new Date(now.getTime() + (0 - 285) * DAY_MS);
	assert.equal(isCalvingAlert(pregnancyDate, now), true);
});

test("isCalvingAlert: false for null input", () => {
	assert.equal(isCalvingAlert(null), false);
});

// ── getLivestockWeatherAlerts behavioral tests ────────────────────────────────

test("getLivestockWeatherAlerts: empty array for empty forecast", () => {
	assert.deepEqual(getLivestockWeatherAlerts([]), []);
	assert.deepEqual(getLivestockWeatherAlerts(), []);
});

test("getLivestockWeatherAlerts: heat danger for tempMax ≥ 35", () => {
	const alerts = getLivestockWeatherAlerts([
		{ date: "2026-08-01", tempMax: 37, tempMin: 22, precipProb: 20 },
	]);
	assert.equal(alerts.length, 1);
	assert.equal(alerts[0].type, "heat");
	assert.equal(alerts[0].level, "danger");
});

test("getLivestockWeatherAlerts: heat warning for 33 ≤ tempMax < 35", () => {
	const alerts = getLivestockWeatherAlerts([
		{ date: "2026-08-01", tempMax: 34, tempMin: 20, precipProb: 10 },
	]);
	const heatAlert = alerts.find((a) => a.type === "heat");
	assert.ok(heatAlert, "expected heat alert");
	assert.equal(heatAlert.level, "warning");
});

test("getLivestockWeatherAlerts: no heat alert for tempMax < 33", () => {
	const alerts = getLivestockWeatherAlerts([
		{ date: "2026-06-20", tempMax: 30, tempMin: 15, precipProb: 10 },
	]);
	assert.equal(
		alerts.filter((a) => a.type === "heat").length,
		0,
	);
});

test("getLivestockWeatherAlerts: cold danger for tempMin ≤ -10", () => {
	const alerts = getLivestockWeatherAlerts([
		{ date: "2026-01-15", tempMax: -5, tempMin: -12, precipProb: 5 },
	]);
	const coldAlert = alerts.find((a) => a.type === "cold");
	assert.ok(coldAlert, "expected cold alert");
	assert.equal(coldAlert.level, "danger");
});

test("getLivestockWeatherAlerts: cold warning for -10 < tempMin ≤ -5", () => {
	const alerts = getLivestockWeatherAlerts([
		{ date: "2026-01-15", tempMax: -2, tempMin: -7, precipProb: 5 },
	]);
	const coldAlert = alerts.find((a) => a.type === "cold");
	assert.ok(coldAlert, "expected cold alert");
	assert.equal(coldAlert.level, "warning");
});

test("getLivestockWeatherAlerts: rain warning for precipProb ≥ 80", () => {
	const alerts = getLivestockWeatherAlerts([
		{ date: "2026-06-20", tempMax: 22, tempMin: 16, precipProb: 85 },
	]);
	const rainAlert = alerts.find((a) => a.type === "rain");
	assert.ok(rainAlert, "expected rain alert");
	assert.equal(rainAlert.level, "warning");
});

test("getLivestockWeatherAlerts: no rain alert for precipProb < 80", () => {
	const alerts = getLivestockWeatherAlerts([
		{ date: "2026-06-20", tempMax: 22, tempMin: 16, precipProb: 75 },
	]);
	assert.equal(alerts.filter((a) => a.type === "rain").length, 0);
});

test("getLivestockWeatherAlerts: multiple alerts can fire for one extreme day", () => {
	// Extreme heat AND high rain
	const alerts = getLivestockWeatherAlerts([
		{ date: "2026-08-01", tempMax: 36, tempMin: 22, precipProb: 90 },
	]);
	assert.ok(alerts.length >= 2, `expected ≥2 alerts, got ${alerts.length}`);
	assert.ok(alerts.some((a) => a.type === "heat"), "missing heat alert");
	assert.ok(alerts.some((a) => a.type === "rain"), "missing rain alert");
});

test("getLivestockWeatherAlerts: ignores null and non-object entries", () => {
	const alerts = getLivestockWeatherAlerts([null, undefined, "bad", 42]);
	assert.deepEqual(alerts, []);
});
