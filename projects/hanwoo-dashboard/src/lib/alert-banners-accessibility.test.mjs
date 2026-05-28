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

test("alert banner decorative calving icon is hidden from assistive tech", () => {
	const source = readSource("components/widgets/AlertBanners.js");
	const commonSource = readSource("components/ui/common.js");

	assert.match(
		source,
		/<span[\s\S]*?aria-hidden="true"[\s\S]*?style=\{\{\s*fontSize:\s*["']18px["']\s*\}\}[\s\S]*?className="animate-bounce"/,
	);
	assert.match(source, /<span className="alert-icon" aria-hidden="true">/);
	assert.match(
		commonSource,
		/export const HeartIcon = \(\) => \(\s*<svg\s+aria-hidden="true"\s+focusable="false"/,
	);
});

test("alert banner remaining-day labels normalize malformed notification values", () => {
	const source = readSource("components/widgets/AlertBanners.js");

	assert.match(
		source,
		/import \{ formatDate, toFiniteNumber \} from ["']@\/lib\/utils["'];/,
	);
	assert.match(source, /function normalizeDaysLeft\(value\) \{/);
	assert.match(
		source,
		/return Math\.max\(0, Math\.floor\(toFiniteNumber\(value\)\)\);/,
	);
	assert.match(source, /normalizeDaysLeft\(notification\.daysLeft\) === 0/);
	assert.match(
		source,
		/const daysLeft = normalizeDaysLeft\(notification\.daysLeft\);/,
	);
	assert.match(source, /daysLeft === 0 \? "오늘" : `\$\{daysLeft\}일 남음`/);
	assert.doesNotMatch(source, /D-\{daysLeft\}/);
	assert.doesNotMatch(source, /`D-\$\{daysLeft\}`/);
	assert.doesNotMatch(source, /notification\.daysLeft \?\? 0/);
	assert.doesNotMatch(source, /notification\.daysLeft === 0/);
});

test("alert banners normalize malformed notification and building payloads before rendering", () => {
	const source = readSource("components/widgets/AlertBanners.js");

	assert.match(
		source,
		/function normalizeAlertBannerOptions\(options\) \{/,
	);
	assert.match(
		source,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export function EstrusAlertBanner\(options = \{\}\)/);
	assert.match(source, /export function CalvingAlertBanner\(options = \{\}\)/);
	assert.match(
		source,
		/const \{ notifications = \[\], buildings = \[\] \} =\s+normalizeAlertBannerOptions\(options\);/,
	);
	assert.match(
		source,
		/function normalizeAlertNotifications\(notifications, type\)/,
	);
	assert.match(source, /if \(!Array\.isArray\(notifications\)\) return \[\]/);
	assert.match(
		source,
		/notification\s*&&\s*typeof\s*notification\s*===\s*["']object["']\s*&&\s*!Array\.isArray\(notification\)\s*&&\s*notification\.\s*type\s*===\s*type/,
	);
	assert.match(source, /function normalizeBuildings\(buildings\)/);
	assert.match(source, /Array\.isArray\(buildings\)/);
	assert.match(
		source,
		/building\s*&&\s*typeof\s*building\s*===\s*["']object["']\s*&&\s*!Array\.isArray\(building\)/,
	);
	assert.match(
		source,
		/const safeBuildings = normalizeBuildings\(buildings\);/,
	);
	assert.match(
		source,
		/normalizeAlertNotifications\(\s*notifications[\s\S]*?["']estrus["']\s*,?\s*\)/,
	);
	assert.match(
		source,
		/normalizeAlertNotifications\(\s*notifications[\s\S]*?["']calving["']\s*,?\s*\)/,
	);
	assert.match(
		source,
		/safeBuildings\s*\.\s*find\(\s*\(\s*item\s*\)\s*=>\s*item\s*\.\s*id\s*===\s*notification\s*\.\s*buildingId\s*,?\s*\)/,
	);
	assert.match(source, /id: notification\.id \?\? `\$\{type\}-\$\{index\}`/);
	assert.match(source, /["']개체명 미등록["']/);
	assert.match(source, /penNumber: notification\.penNumber \?\? ["']칸 미지정["']/);
	assert.match(source, /building\?\.name \|\| ["']축사 미지정["']/);
	assert.match(
		source,
		/notification\.targetDate\s*\?\s*formatDate\(notification\.targetDate\)\s*:\s*["']분만 예정일 미등록["']/,
	);
	assert.doesNotMatch(source, /["']이름 미등록["']/);
	assert.doesNotMatch(source, /penNumber: notification\.penNumber \?\? ["']-["']/);
	assert.doesNotMatch(source, /building\?\.name \|\| ["']미지정["']/);
	assert.doesNotMatch(
		source,
		/notification\.targetDate\s*\?\s*formatDate\(notification\.targetDate\)\s*:\s*["']-["']/,
	);
	assert.doesNotMatch(
		source,
		/notifications\.filter\(\(notification\) => notification\.type/,
	);
	assert.doesNotMatch(
		source,
		/buildings\.find\(\(item\) => item\.id === notification\.buildingId\)/,
	);
	assert.doesNotMatch(
		source,
		/export function EstrusAlertBanner\(\{ notifications = \[\], buildings = \[\] \}\)/,
	);
	assert.doesNotMatch(
		source,
		/export function CalvingAlertBanner\(\{ notifications = \[\], buildings = \[\] \}\)/,
	);
});
