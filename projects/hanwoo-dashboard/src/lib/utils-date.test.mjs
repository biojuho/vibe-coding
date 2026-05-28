import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

test("date utility calculations use a fresh or injected current date", () => {
	const utilsSource = readSource("lib/utils.js");
	const constantsSource = readSource("lib/constants.js");

	assert.match(utilsSource, /const DAY_MS = 86400000;/);
	assert.match(utilsSource, /function toDate\(value\)/);
	assert.match(utilsSource, /function toValidDate\(value\)/);
	assert.match(
		utilsSource,
		/Number\.isNaN\(date\.getTime\(\)\) \? null : date/,
	);
	assert.match(
		utilsSource,
		/export function getMonthAge\(birthDate, now = new Date\(\)\)/,
	);
	assert.match(utilsSource, /if \(!date \|\| !today\) return 0;/);
	assert.match(
		utilsSource,
		/export function getNextEstrusDate\(lastEstrus, now = new Date\(\)\)/,
	);
	assert.match(utilsSource, /if \(!today \|\| !next\) return null;/);
	assert.match(
		utilsSource,
		/export function getDaysUntilEstrus\(lastEstrus, now = new Date\(\)\)/,
	);
	assert.match(utilsSource, /if \(!today\) return null;/);
	assert.match(
		utilsSource,
		/const next = getNextEstrusDate\(lastEstrus, today\);/,
	);
	assert.match(
		utilsSource,
		/export function isEstrusAlert\(lastEstrus, now = new Date\(\)\)/,
	);
	assert.match(utilsSource, /getDaysUntilEstrus\(lastEstrus, now\)/);
	assert.match(utilsSource, /const date = toValidDate\(pregnancyDate\);/);
	assert.match(
		utilsSource,
		/return date \? new Date\(date\.getTime\(\) \+ CALVING_DAYS \* DAY_MS\) : null;/,
	);
	assert.match(
		utilsSource,
		/export function getDaysUntilCalving\(pregnancyDate, now = new Date\(\)\)/,
	);
	assert.match(utilsSource, /Math\.ceil\(\(calvingDate - today\) \/ DAY_MS\)/);
	assert.match(
		utilsSource,
		/export function isCalvingAlert\(pregnancyDate, now = new Date\(\)\)/,
	);
	assert.match(utilsSource, /getDaysUntilCalving\(pregnancyDate, now\)/);
	assert.match(
		utilsSource,
		/return date \? date\.toLocaleDateString\(['"]ko-KR['"]\) : ['"]날짜 미등록['"];/,
	);
	assert.doesNotMatch(utilsSource, /return date \? date\.toLocaleDateString\(['"]ko-KR['"]\) : ['"]-['"];/);
	assert.match(
		utilsSource,
		/return date \? date\.toISOString\(\)\.split\(['"]T['"]\)\[0\] : ['"]['"];/,
	);
	assert.match(
		utilsSource,
		/export function formatForecastDateLabel\(\s*value,\s*options = \{ month: ['"]short['"], day: ['"]numeric['"] \},?\s*\) \{/,
	);
	assert.match(
		utilsSource,
		/return date \? date\.toLocaleDateString\(['"]ko-KR['"], options\) : ['"]날짜 미등록['"];/,
	);
	assert.match(
		utilsSource,
		/const label = formatForecastDateLabel\(day\.date\);/,
	);
	assert.match(
		utilsSource,
		/function isLivestockWeatherForecastDay\(day\) \{/,
	);
	assert.match(
		utilsSource,
		/day && typeof day === ["']object["'] && !Array\.isArray\(day\)/,
	);
	assert.match(
		utilsSource,
		/function normalizeLivestockWeatherForecast\(forecast\) \{/,
	);
	assert.match(
		utilsSource,
		/forecast\.filter\(isLivestockWeatherForecastDay\)/,
	);
	assert.match(
		utilsSource,
		/const safeForecast = normalizeLivestockWeatherForecast\(forecast\);/,
	);
	assert.match(utilsSource, /safeForecast\.forEach\(\(day\) => \{/);
	assert.doesNotMatch(utilsSource, /forecast\.forEach\(\(day\) => \{/);
	assert.match(
		utilsSource,
		/export function toFiniteNumber\(value, fallback = 0\) \{/,
	);
	assert.match(utilsSource, /const amount = Number\(value\);/);
	assert.match(
		utilsSource,
		/return Number\.isFinite\(amount\) \? amount : fallback;/,
	);
	assert.match(utilsSource, /const amount = toFiniteNumber\(value\);/);
	assert.match(
		utilsSource,
		/return new Intl\.NumberFormat\(['"]ko-KR['"]\)\.format\(amount\);/,
	);
	assert.doesNotMatch(utilsSource, /toLocaleDateString\(['"]ko-KR['"]\);\s*\}/);
	assert.doesNotMatch(utilsSource, /new Date\(pregnancyDate\)\.getTime\(\)/);
	assert.doesNotMatch(
		utilsSource,
		/Intl\.NumberFormat\(['"]ko-KR['"]\)\.format\(value\)/,
	);
	assert.doesNotMatch(
		utilsSource,
		/new Date\(day\.date\)\.toLocaleDateString\(['"]ko-KR['"]/,
	);
	assert.doesNotMatch(utilsSource, /TODAY/);
	assert.doesNotMatch(constantsSource, /TODAY = new Date\(\)/);
});
