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

	assert.match(
		source,
		/<span aria-hidden="true" style=\{\{ fontSize: '18px' \}\} className="animate-bounce">/,
	);
});

test("alert banner D-day labels normalize malformed notification values", () => {
	const source = readSource("components/widgets/AlertBanners.js");

	assert.match(
		source,
		/import \{ formatDate, toFiniteNumber \} from '@\/lib\/utils';/,
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
	assert.doesNotMatch(source, /notification\.daysLeft \?\? 0/);
	assert.doesNotMatch(source, /notification\.daysLeft === 0/);
});

test("alert banners normalize malformed notification and building payloads before rendering", () => {
	const source = readSource("components/widgets/AlertBanners.js");

	assert.match(
		source,
		/function normalizeAlertNotifications\(notifications, type\)/,
	);
	assert.match(source, /if \(!Array\.isArray\(notifications\)\) return \[\]/);
	assert.match(
		source,
		/notification && typeof notification === 'object' && notification\.type === type/,
	);
	assert.match(source, /function normalizeBuildings\(buildings\)/);
	assert.match(source, /Array\.isArray\(buildings\)/);
	assert.match(
		source,
		/const safeBuildings = normalizeBuildings\(buildings\);/,
	);
	assert.match(
		source,
		/normalizeAlertNotifications\(notifications, 'estrus'\)/,
	);
	assert.match(
		source,
		/normalizeAlertNotifications\(notifications, 'calving'\)/,
	);
	assert.match(
		source,
		/safeBuildings\.find\(\(item\) => item\.id === notification\.buildingId\)/,
	);
	assert.match(source, /id: notification\.id \?\? `\$\{type\}-\$\{index\}`/);
	assert.match(source, /'이름 미등록'/);
	assert.doesNotMatch(
		source,
		/notifications\.filter\(\(notification\) => notification\.type/,
	);
	assert.doesNotMatch(
		source,
		/buildings\.find\(\(item\) => item\.id === notification\.buildingId\)/,
	);
});
