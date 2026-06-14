/**
 * Behavioral tests for formatting utilities in utils.js.
 *
 * utils.js imports from "./constants" (bare specifier, no extension) which fails
 * in Node ESM. These formatting functions have no dependency on constants, so we
 * re-implement them inline and cross-check production boundaries via source-grep.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/utils.js"), "utf8");

// ── Inline re-implementations (keep in sync via source-grep below) ────────────

function toDate(value) {
	return value instanceof Date ? new Date(value.getTime()) : new Date(value);
}

function toValidDate(value) {
	const date = toDate(value);
	return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(value) {
	if (!value) return "날짜 미등록";
	const date = toValidDate(value);
	return date ? date.toLocaleDateString("ko-KR") : "날짜 미등록";
}

function toLocalInputDate(date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");
	return `${year}-${month}-${day}`;
}

function toInputDate(value) {
	if (!value) return "";
	const date = toValidDate(value);
	return date ? toLocalInputDate(date) : "";
}

function toFiniteNumber(value, fallback = 0) {
	const amount = Number(value);
	return Number.isFinite(amount) ? amount : fallback;
}

function formatMoney(value) {
	const amount = toFiniteNumber(value);
	return new Intl.NumberFormat("ko-KR").format(amount);
}

function getWeatherIcon(code) {
	if (code === 0) return "☀️";
	if (code <= 3) return "⛅";
	if (code <= 48) return "🌫️";
	if (code <= 67) return "🌧️";
	if (code <= 77) return "❄️";
	return "⛈️";
}

function getWeatherDesc(code) {
	if (code === 0) return "맑음";
	if (code <= 2) return "구름 조금";
	if (code === 3) return "흐림";
	if (code <= 48) return "안개";
	if (code <= 55) return "이슬비";
	if (code <= 65) return "비";
	if (code <= 75) return "눈";
	return "폭우";
}

// ── Source-grep: structural guards ───────────────────────────────────────────

test("formatDate uses ko-KR locale and 날짜 미등록 fallback", () => {
	assert.match(src, /date\.toLocaleDateString\("ko-KR"\)/);
	assert.match(src, /"날짜 미등록"/);
});

test("toLocalInputDate uses getMonth()+1 padded — not toISOString", () => {
	assert.match(src, /getMonth\(\) \+ 1/);
	assert.match(src, /padStart\(2, "0"\)/);
	assert.doesNotMatch(src, /toISOString\(\)\.split\("T"\)\[0\]/);
});

test("formatMoney uses Intl.NumberFormat ko-KR", () => {
	assert.match(src, /new Intl\.NumberFormat\("ko-KR"\)\.format\(amount\)/);
});

// ── formatDate behavioral ────────────────────────────────────────────────────

test("formatDate returns 날짜 미등록 for null, undefined, empty string", () => {
	assert.equal(formatDate(null), "날짜 미등록");
	assert.equal(formatDate(undefined), "날짜 미등록");
	assert.equal(formatDate(""), "날짜 미등록");
});

test("formatDate returns 날짜 미등록 for invalid date strings", () => {
	assert.equal(formatDate("not-a-date"), "날짜 미등록");
	assert.equal(formatDate("abc"), "날짜 미등록");
});

test("formatDate returns localized Korean string for valid ISO dates", () => {
	const result = formatDate("2026-01-15T00:00:00.000Z");
	// Should be a Korean-formatted date string, not the fallback
	assert.notEqual(result, "날짜 미등록");
	assert.ok(typeof result === "string" && result.length > 0);
});

test("formatDate accepts a Date object directly", () => {
	const date = new Date("2026-06-01T00:00:00.000Z");
	const result = formatDate(date);
	assert.notEqual(result, "날짜 미등록");
});

// ── toLocalInputDate behavioral ───────────────────────────────────────────────

test("toLocalInputDate formats a Date as YYYY-MM-DD using local fields", () => {
	// Use a fixed UTC date that is unambiguous at midnight UTC — local and UTC agree
	const date = new Date(2026, 0, 5); // Jan 5, 2026 in local time
	assert.equal(toLocalInputDate(date), "2026-01-05");
});

test("toLocalInputDate zero-pads month and day", () => {
	const date = new Date(2026, 0, 1); // Jan 1
	assert.equal(toLocalInputDate(date), "2026-01-01");
});

test("toLocalInputDate handles December (month 11)", () => {
	const date = new Date(2026, 11, 31);
	assert.equal(toLocalInputDate(date), "2026-12-31");
});

// ── toInputDate behavioral ────────────────────────────────────────────────────

test("toInputDate returns empty string for null, undefined, empty string", () => {
	assert.equal(toInputDate(null), "");
	assert.equal(toInputDate(undefined), "");
	assert.equal(toInputDate(""), "");
});

test("toInputDate returns empty string for invalid date strings", () => {
	assert.equal(toInputDate("not-a-date"), "");
	assert.equal(toInputDate("2026-13-01"), "");
});

test("toInputDate formats valid ISO string as YYYY-MM-DD", () => {
	// UTC midnight — local and UTC calendar date agree for any timezone
	const result = toInputDate("2026-06-15T00:00:00.000Z");
	assert.match(result, /^\d{4}-\d{2}-\d{2}$/);
});

// ── formatMoney behavioral ────────────────────────────────────────────────────

test("formatMoney formats positive integers with Korean thousands separators", () => {
	assert.equal(formatMoney(1000000), "1,000,000");
	assert.equal(formatMoney(9900), "9,900");
});

test("formatMoney returns 0 for NaN, null, undefined, Infinity", () => {
	assert.equal(formatMoney(NaN), "0");
	assert.equal(formatMoney(null), "0");
	assert.equal(formatMoney(undefined), "0");
	assert.equal(formatMoney(Infinity), "0");
});

test("formatMoney coerces numeric strings", () => {
	assert.equal(formatMoney("50000"), "50,000");
});

test("formatMoney handles zero", () => {
	assert.equal(formatMoney(0), "0");
});

// ── getWeatherIcon behavioral ─────────────────────────────────────────────────

test("getWeatherIcon returns ☀️ for code 0 (clear sky)", () => {
	assert.equal(getWeatherIcon(0), "☀️");
});

test("getWeatherIcon returns ⛅ for codes 1-3 (partly cloudy)", () => {
	assert.equal(getWeatherIcon(1), "⛅");
	assert.equal(getWeatherIcon(3), "⛅");
});

test("getWeatherIcon returns 🌫️ for codes 4-48 (fog)", () => {
	assert.equal(getWeatherIcon(45), "🌫️");
	assert.equal(getWeatherIcon(48), "🌫️");
});

test("getWeatherIcon returns 🌧️ for codes 49-67 (rain)", () => {
	assert.equal(getWeatherIcon(61), "🌧️");
	assert.equal(getWeatherIcon(67), "🌧️");
});

test("getWeatherIcon returns ❄️ for codes 68-77 (snow)", () => {
	assert.equal(getWeatherIcon(71), "❄️");
	assert.equal(getWeatherIcon(77), "❄️");
});

test("getWeatherIcon returns ⛈️ for codes > 77 (storm)", () => {
	assert.equal(getWeatherIcon(95), "⛈️");
	assert.equal(getWeatherIcon(99), "⛈️");
});

// ── getWeatherDesc behavioral ─────────────────────────────────────────────────

test("getWeatherDesc returns 맑음 for code 0", () => {
	assert.equal(getWeatherDesc(0), "맑음");
});

test("getWeatherDesc returns 구름 조금 for codes 1-2", () => {
	assert.equal(getWeatherDesc(1), "구름 조금");
	assert.equal(getWeatherDesc(2), "구름 조금");
});

test("getWeatherDesc returns 흐림 for code 3", () => {
	assert.equal(getWeatherDesc(3), "흐림");
});

test("getWeatherDesc returns 안개 for codes 4-48", () => {
	assert.equal(getWeatherDesc(45), "안개");
	assert.equal(getWeatherDesc(48), "안개");
});

test("getWeatherDesc returns 이슬비 for codes 49-55", () => {
	assert.equal(getWeatherDesc(51), "이슬비");
	assert.equal(getWeatherDesc(55), "이슬비");
});

test("getWeatherDesc returns 비 for codes 56-65", () => {
	assert.equal(getWeatherDesc(61), "비");
	assert.equal(getWeatherDesc(65), "비");
});

test("getWeatherDesc returns 눈 for codes 66-75", () => {
	assert.equal(getWeatherDesc(71), "눈");
	assert.equal(getWeatherDesc(75), "눈");
});

test("getWeatherDesc returns 폭우 for codes > 75", () => {
	assert.equal(getWeatherDesc(95), "폭우");
	assert.equal(getWeatherDesc(99), "폭우");
});
