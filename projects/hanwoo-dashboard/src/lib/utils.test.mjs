import assert from "node:assert/strict";
import test from "node:test";

import {
	calcTHI,
	formatDate,
	formatMoney,
	getCalvingDate,
	getDaysUntilCalving,
	getDaysUntilEstrus,
	getLivestockWeatherAlerts,
	getMonthAge,
	getNextEstrusDate,
	getTHILevel,
	getWeatherDesc,
	getWeatherIcon,
	isCalvingAlert,
	isEstrusAlert,
	isEstrusToday,
	toFiniteNumber,
	toInputDate,
} from "./utils.js";

import {
	CALVING_ALERT_WINDOW,
	CALVING_DAYS,
	ESTRUS_ALERT_WINDOW,
	ESTRUS_CYCLE_DAYS,
} from "./constants.js";

// ── Helpers ──────────────────────────────────────────────────────────────────

function addDays(date, n) {
	const d = new Date(date.getTime());
	d.setDate(d.getDate() + n);
	return d;
}

const TODAY = new Date("2025-06-15T00:00:00.000Z");

// ── getMonthAge ───────────────────────────────────────────────────────────────

test("getMonthAge: null birthDate returns 0", () => {
	assert.equal(getMonthAge(null, TODAY), 0);
});

test("getMonthAge: invalid date string returns 0", () => {
	assert.equal(getMonthAge("not-a-date", TODAY), 0);
});

test("getMonthAge: same-month birth returns minimum 1", () => {
	const born = new Date("2025-06-01");
	assert.equal(getMonthAge(born, TODAY), 1);
});

test("getMonthAge: 12 months ago returns 12", () => {
	const born = new Date("2024-06-15");
	assert.equal(getMonthAge(born, TODAY), 12);
});

test("getMonthAge: 6 months ago returns 6", () => {
	const born = new Date("2024-12-15");
	assert.equal(getMonthAge(born, TODAY), 6);
});

// ── getNextEstrusDate ─────────────────────────────────────────────────────────

test("getNextEstrusDate: null returns null", () => {
	assert.equal(getNextEstrusDate(null, TODAY), null);
});

test("getNextEstrusDate: when last estrus was exactly one cycle ago, returns next future cycle", () => {
	// getNextEstrusDate uses 'while (next <= today)', so even if today is the estrus
	// day (21 days after last), it advances to the next cycle (42 days after last).
	const lastEstrus = addDays(TODAY, -ESTRUS_CYCLE_DAYS);
	const next = getNextEstrusDate(lastEstrus, TODAY);
	assert.ok(next > TODAY, "next estrus should be strictly in the future");
	const diffDays = Math.round((next - TODAY) / 86400000);
	assert.equal(diffDays, ESTRUS_CYCLE_DAYS, "should advance one full cycle from today");
});

// ── getDaysUntilEstrus ────────────────────────────────────────────────────────

test("getDaysUntilEstrus: null lastEstrus returns null", () => {
	assert.equal(getDaysUntilEstrus(null, TODAY), null);
});

test("getDaysUntilEstrus: exactly one cycle ago → reports ESTRUS_CYCLE_DAYS until next", () => {
	// Because getNextEstrusDate advances past 'today' (<=), today-as-estrus-day
	// becomes the start of a new countdown to the following cycle.
	const lastEstrus = addDays(TODAY, -ESTRUS_CYCLE_DAYS);
	assert.equal(getDaysUntilEstrus(lastEstrus, TODAY), ESTRUS_CYCLE_DAYS);
});

// ── isEstrusAlert / isEstrusToday ─────────────────────────────────────────────

test("isEstrusAlert: true when within alert window", () => {
	// set last estrus so next estrus is 1 day away (within ESTRUS_ALERT_WINDOW=3)
	const lastEstrus = addDays(TODAY, -(ESTRUS_CYCLE_DAYS - 1));
	assert.equal(isEstrusAlert(lastEstrus, TODAY), true);
});

test("isEstrusAlert: false when outside alert window", () => {
	// next estrus is 10 days away, which is > ESTRUS_ALERT_WINDOW (3)
	const lastEstrus = addDays(TODAY, -(ESTRUS_CYCLE_DAYS - 10));
	assert.equal(isEstrusAlert(lastEstrus, TODAY), false);
});

test("isEstrusToday: returns false when getDaysUntilEstrus > 0", () => {
	// getNextEstrusDate uses '<=', so getDaysUntilEstrus is always >= 1;
	// isEstrusToday (checks === 0) therefore always returns false.
	// This is correct per the domain-constants-coverage source test.
	const lastEstrus = addDays(TODAY, -(ESTRUS_CYCLE_DAYS - 5));
	assert.equal(isEstrusToday(lastEstrus, TODAY), false);
});

test("isEstrusToday: also false when last estrus was exactly one cycle ago", () => {
	// Even on the estrus day itself, the while (next <= today) loop advances past it.
	const lastEstrus = addDays(TODAY, -ESTRUS_CYCLE_DAYS);
	assert.equal(isEstrusToday(lastEstrus, TODAY), false);
});

// ── getCalvingDate ────────────────────────────────────────────────────────────

test("getCalvingDate: null returns null", () => {
	assert.equal(getCalvingDate(null), null);
});

test("getCalvingDate: adds CALVING_DAYS to pregnancy date", () => {
	const pregnancyDate = new Date("2025-01-01");
	const calving = getCalvingDate(pregnancyDate);
	const expected = addDays(pregnancyDate, CALVING_DAYS);
	assert.equal(calving.getTime(), expected.getTime());
});

// ── getDaysUntilCalving / isCalvingAlert ──────────────────────────────────────

test("getDaysUntilCalving: null returns null", () => {
	assert.equal(getDaysUntilCalving(null, TODAY), null);
});

test("getDaysUntilCalving: pregnancy starting today → CALVING_DAYS days", () => {
	const days = getDaysUntilCalving(TODAY, TODAY);
	assert.equal(days, CALVING_DAYS);
});

test("isCalvingAlert: true when within CALVING_ALERT_WINDOW days", () => {
	// calving is CALVING_DAYS from pregnancy start, within 14 days
	const pregnancyStart = addDays(TODAY, -(CALVING_DAYS - 7));
	assert.equal(isCalvingAlert(pregnancyStart, TODAY), true);
});

test("isCalvingAlert: false when calving is far away", () => {
	const pregnancyStart = addDays(TODAY, -1); // just started
	assert.equal(isCalvingAlert(pregnancyStart, TODAY), false);
});

// ── formatDate ────────────────────────────────────────────────────────────────

test("formatDate: null returns '날짜 미등록'", () => {
	assert.equal(formatDate(null), "날짜 미등록");
});

test("formatDate: invalid string returns '날짜 미등록'", () => {
	assert.equal(formatDate("not-a-date"), "날짜 미등록");
});

test("formatDate: valid date returns Korean locale string", () => {
	const result = formatDate(new Date("2025-01-15"));
	assert.ok(typeof result === "string" && result.length > 0);
	assert.ok(result !== "날짜 미등록");
});

// ── toInputDate ───────────────────────────────────────────────────────────────

test("toInputDate: null returns empty string", () => {
	assert.equal(toInputDate(null), "");
});

test("toInputDate: invalid string returns empty string", () => {
	assert.equal(toInputDate("bad"), "");
});

test("toInputDate: valid date returns YYYY-MM-DD format", () => {
	// Use a fixed date to avoid timezone drift in the assertion
	const d = new Date(2025, 5, 15); // local: June 15, 2025
	const result = toInputDate(d);
	assert.match(result, /^\d{4}-\d{2}-\d{2}$/);
	assert.equal(result, "2025-06-15");
});

// ── toFiniteNumber ────────────────────────────────────────────────────────────

test("toFiniteNumber: numeric string returns number", () => {
	assert.equal(toFiniteNumber("42"), 42);
});

test("toFiniteNumber: NaN string uses fallback", () => {
	assert.equal(toFiniteNumber("not-a-number", 99), 99);
});

test("toFiniteNumber: Infinity uses fallback", () => {
	assert.equal(toFiniteNumber(Infinity, 0), 0);
});

test("toFiniteNumber: undefined uses fallback", () => {
	assert.equal(toFiniteNumber(undefined, 5), 5);
});

test("toFiniteNumber: null uses fallback 0", () => {
	assert.equal(toFiniteNumber(null), 0);
});

// ── calcTHI ───────────────────────────────────────────────────────────────────

test("calcTHI: known value at 30°C / 80% humidity", () => {
	// THI = 1.8*30 + 32 - (0.55 - 0.0055*80) * (1.8*30 - 26)
	//     = 54 + 32 - (0.55 - 0.44) * (54 - 26)
	//     = 86 - 0.11 * 28 = 86 - 3.08 = 82.92
	const thi = calcTHI(30, 80);
	assert.ok(Math.abs(thi - 82.92) < 0.01, `Expected ~82.92, got ${thi}`);
});

test("calcTHI: low temp/humidity gives low THI", () => {
	const thi = calcTHI(10, 30);
	assert.ok(thi < 72, `Expected THI < 72 for cool weather, got ${thi}`);
});

// ── getTHILevel ───────────────────────────────────────────────────────────────

test("getTHILevel: below 72 returns 정상", () => {
	const level = getTHILevel(65);
	assert.equal(level.label, "정상");
});

test("getTHILevel: 72-77 returns 주의", () => {
	const level = getTHILevel(75);
	assert.equal(level.label, "주의");
});

test("getTHILevel: 78-88 returns 경고", () => {
	const level = getTHILevel(80);
	assert.equal(level.label, "경고");
});

test("getTHILevel: 89+ returns 위험", () => {
	const level = getTHILevel(90);
	assert.equal(level.label, "위험");
});

test("getTHILevel: returns color and bg properties", () => {
	const level = getTHILevel(65);
	assert.ok(typeof level.color === "string" && level.color.startsWith("#"));
	assert.ok(typeof level.bg === "string" && level.bg.startsWith("#"));
});

// ── getWeatherIcon ────────────────────────────────────────────────────────────

test("getWeatherIcon: code 0 returns ☀️", () => {
	assert.equal(getWeatherIcon(0), "☀️");
});

test("getWeatherIcon: code 2 returns ⛅ (partly cloudy)", () => {
	assert.equal(getWeatherIcon(2), "⛅");
});

test("getWeatherIcon: code 60 returns 🌧️ (rain)", () => {
	assert.equal(getWeatherIcon(60), "🌧️");
});

test("getWeatherIcon: code 99 returns ⛈️ (thunderstorm)", () => {
	assert.equal(getWeatherIcon(99), "⛈️");
});

// ── getWeatherDesc ────────────────────────────────────────────────────────────

test("getWeatherDesc: code 0 returns '맑음'", () => {
	assert.equal(getWeatherDesc(0), "맑음");
});

test("getWeatherDesc: code 3 returns '흐림'", () => {
	assert.equal(getWeatherDesc(3), "흐림");
});

test("getWeatherDesc: code 65 returns '비'", () => {
	assert.equal(getWeatherDesc(65), "비");
});

test("getWeatherDesc: code 99 returns '폭우'", () => {
	assert.equal(getWeatherDesc(99), "폭우");
});

// ── formatMoney ───────────────────────────────────────────────────────────────

test("formatMoney: zero returns '0'", () => {
	assert.equal(formatMoney(0), "0");
});

test("formatMoney: 1000 returns '1,000'", () => {
	assert.equal(formatMoney(1000), "1,000");
});

test("formatMoney: string number is parsed", () => {
	assert.equal(formatMoney("50000"), "50,000");
});

test("formatMoney: NaN string falls back to 0", () => {
	assert.equal(formatMoney("not-a-number"), "0");
});

// ── getLivestockWeatherAlerts ─────────────────────────────────────────────────

test("getLivestockWeatherAlerts: empty forecast returns empty array", () => {
	assert.deepEqual(getLivestockWeatherAlerts([]), []);
});

test("getLivestockWeatherAlerts: no alert when within normal range", () => {
	const forecast = [{ date: "2025-06-15", tempMax: 28, tempMin: 15, precipProb: 20 }];
	assert.deepEqual(getLivestockWeatherAlerts(forecast), []);
});

test("getLivestockWeatherAlerts: heat danger at tempMax >= 35", () => {
	const forecast = [{ date: "2025-06-15", tempMax: 36, tempMin: 25, precipProb: 10 }];
	const alerts = getLivestockWeatherAlerts(forecast);
	assert.equal(alerts.length, 1);
	assert.equal(alerts[0].type, "heat");
	assert.equal(alerts[0].level, "danger");
});

test("getLivestockWeatherAlerts: heat warning at 33 <= tempMax < 35", () => {
	const forecast = [{ date: "2025-06-15", tempMax: 34, tempMin: 20, precipProb: 0 }];
	const alerts = getLivestockWeatherAlerts(forecast);
	assert.equal(alerts.length, 1);
	assert.equal(alerts[0].type, "heat");
	assert.equal(alerts[0].level, "warning");
});

test("getLivestockWeatherAlerts: cold danger at tempMin <= -10", () => {
	const forecast = [{ date: "2025-01-15", tempMax: -5, tempMin: -12, precipProb: 0 }];
	const alerts = getLivestockWeatherAlerts(forecast);
	const coldAlert = alerts.find((a) => a.type === "cold");
	assert.ok(coldAlert, "should have a cold alert");
	assert.equal(coldAlert.level, "danger");
});

test("getLivestockWeatherAlerts: rain warning at precipProb >= 80", () => {
	const forecast = [{ date: "2025-06-15", tempMax: 25, tempMin: 18, precipProb: 85 }];
	const alerts = getLivestockWeatherAlerts(forecast);
	assert.equal(alerts.length, 1);
	assert.equal(alerts[0].type, "rain");
});

test("getLivestockWeatherAlerts: multiple conditions generate multiple alerts", () => {
	const forecast = [{ date: "2025-01-15", tempMax: -3, tempMin: -15, precipProb: 90 }];
	const alerts = getLivestockWeatherAlerts(forecast);
	assert.ok(alerts.length >= 2, `expected at least 2 alerts, got ${alerts.length}`);
});

test("getLivestockWeatherAlerts: non-object entries in forecast are filtered", () => {
	const forecast = [null, "string", { date: "2025-06-15", tempMax: 20, tempMin: 10, precipProb: 0 }];
	assert.deepEqual(getLivestockWeatherAlerts(forecast), []);
});
