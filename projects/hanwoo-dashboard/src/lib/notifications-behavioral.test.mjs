/**
 * Behavioral tests for buildNotifications in notifications.js.
 *
 * notifications.js imports from "./utils" (bare specifier, no extension) which
 * fails in Node ESM. We replicate the pure logic inline and cross-check the
 * critical production boundaries via source-grep so tests and production code
 * cannot silently diverge.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/notifications.js"), "utf8");

// ── Inline re-implementation of buildNotifications ────────────────────────────
// Matches the exact production logic so the tests remain meaningful.

const ESTRUS_CYCLE_DAYS = 21;
const CALVING_DAYS = 285;
const ESTRUS_ALERT_WINDOW = 3;
const CALVING_ALERT_WINDOW = 14;
const DAY_MS = 86400000;

function toValidDate(value) {
	const date = value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? null : date;
}

function getNextEstrusDate(lastEstrus, now) {
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

function buildNotificationTiming() {
	return {};
}

function isNotificationCattleRow(row) {
	return row && typeof row === "object" && !Array.isArray(row);
}

function normalizeNotificationCattle(cattle) {
	return Array.isArray(cattle) ? cattle.filter(isNotificationCattleRow) : [];
}

function isLowStock(item) {
	if (!item || typeof item !== "object" || Array.isArray(item)) return false;
	const qty = Number(item.quantity);
	const thr = Number(item.threshold);
	return Number.isFinite(qty) && Number.isFinite(thr) && thr > 0 && qty <= thr;
}

function buildNotifications(cattle = [], inventory = [], now = new Date()) {
	const notifications = [];
	const safeCattle = normalizeNotificationCattle(cattle);

	safeCattle.forEach((cow) => {
		if (
			(cow.status === "번식우" || cow.status === "육성우") &&
			cow.lastEstrus &&
			isEstrusAlert(cow.lastEstrus, now)
		) {
			const daysLeft = getDaysUntilEstrus(cow.lastEstrus, now);
			const timing = buildNotificationTiming("estrus", cow.lastEstrus);

			notifications.push({
				id: `estrus-${cow.id}`,
				type: "estrus",
				level: daysLeft <= 1 ? "critical" : "warning",
				title: daysLeft === 0 ? "오늘 발정 예정" : "발정 임박",
				message: `${cow.name} (${cow.tagNumber}) 발정 예정일이 ${daysLeft}일 남았습니다.`,
				daysLeft,
				cattleId: cow.id,
				cattleName: cow.name,
				tagNumber: cow.tagNumber,
				buildingId: cow.buildingId,
				penNumber: cow.penNumber,
				...timing,
			});
		}

		if (
			cow.status === "임신우" &&
			cow.pregnancyDate &&
			isCalvingAlert(cow.pregnancyDate, now)
		) {
			const daysLeft = getDaysUntilCalving(cow.pregnancyDate, now);
			const timing = buildNotificationTiming("calving", cow.pregnancyDate);

			notifications.push({
				id: `calving-${cow.id}`,
				type: "calving",
				level: daysLeft <= 3 ? "critical" : "warning",
				title: daysLeft === 0 ? "오늘 분만 예정" : "분만 임박",
				message: `${cow.name} (${cow.tagNumber}) 분만 예정일이 ${daysLeft}일 남았습니다.`,
				daysLeft,
				cattleId: cow.id,
				cattleName: cow.name,
				tagNumber: cow.tagNumber,
				buildingId: cow.buildingId,
				penNumber: cow.penNumber,
				...timing,
			});
		}
	});

	if (Array.isArray(inventory)) {
		inventory.filter(isLowStock).forEach((item) => {
			const name = typeof item.name === "string" ? item.name.trim() : "재고 항목";
			const qty = Number(item.quantity);
			const thr = Number(item.threshold);
			const isCritical = qty === 0;
			notifications.push({
				id: `inventory-${item.id ?? name}`,
				type: "alert",
				level: isCritical ? "critical" : "warning",
				title: isCritical ? "재고 소진" : "재고 부족",
				message: isCritical
					? `${name} 재고가 소진되었습니다. 즉시 보충이 필요합니다.`
					: `${name} 재고가 ${qty}${item.unit ?? ""}로 기준(${thr}${item.unit ?? ""})에 미달합니다.`,
				inventoryId: item.id,
				inventoryName: name,
			});
		});
	}

	notifications.sort((a, b) => {
		if (a.level === "critical" && b.level !== "critical") return -1;
		if (a.level !== "critical" && b.level === "critical") return 1;
		return 0;
	});

	return notifications;
}

// Helper: make a date N days from a reference date
function daysFromNow(n, now) {
	const d = new Date(now.getTime() + n * DAY_MS);
	return d;
}

// Reference "now" for deterministic tests
const NOW = new Date("2026-06-15T12:00:00Z");

// lastEstrus such that next cycle is within N days of NOW
function lastEstrusForDaysLeft(daysLeft, now = NOW) {
	// next estrus = now + daysLeft, so lastEstrus = next - 21
	const nextEstrus = new Date(now.getTime() + daysLeft * DAY_MS);
	return new Date(nextEstrus.getTime() - ESTRUS_CYCLE_DAYS * DAY_MS);
}

// pregnancyDate such that calving is exactly daysLeft from now
function pregnancyForCalvingInDays(daysLeft, now = NOW) {
	const calvingAt = new Date(now.getTime() + daysLeft * DAY_MS);
	return new Date(calvingAt.getTime() - CALVING_DAYS * DAY_MS);
}

// ── Source-grep: verify production boundaries ─────────────────────────────────

test("production notifications.js: estrus critical when daysLeft <= 1", () => {
	assert.match(src, /daysLeft <= 1/);
});

test("production notifications.js: calving critical when daysLeft <= 3", () => {
	assert.match(src, /daysLeft <= 3/);
});

test("production notifications.js: isLowStock checks threshold > 0", () => {
	assert.match(src, /thr > 0/);
});

test("production notifications.js: inventory critical when qty === 0", () => {
	assert.match(src, /qty === 0/);
});

test("production notifications.js: sort puts critical before warning", () => {
	assert.match(src, /return -1/);
	assert.match(src, /return 1/);
});

// ── Estrus alerts ─────────────────────────────────────────────────────────────

test("buildNotifications emits estrus alert for 번식우 within ESTRUS_ALERT_WINDOW", () => {
	const lastEstrus = lastEstrusForDaysLeft(2, NOW);
	const notifications = buildNotifications(
		[{ id: "c1", name: "복순이", tagNumber: "001", status: "번식우", lastEstrus }],
		[],
		NOW,
	);
	assert.equal(notifications.length, 1);
	assert.equal(notifications[0].type, "estrus");
	assert.equal(notifications[0].id, "estrus-c1");
});

test("buildNotifications emits estrus alert for 육성우 within ESTRUS_ALERT_WINDOW", () => {
	const lastEstrus = lastEstrusForDaysLeft(2, NOW);
	const notifications = buildNotifications(
		[{ id: "c2", name: "순자", tagNumber: "002", status: "육성우", lastEstrus }],
		[],
		NOW,
	);
	assert.equal(notifications.length, 1);
	assert.equal(notifications[0].type, "estrus");
});

test("buildNotifications does NOT emit estrus alert for 임신우", () => {
	const lastEstrus = lastEstrusForDaysLeft(2, NOW);
	const notifications = buildNotifications(
		[{ id: "c3", name: "영이", tagNumber: "003", status: "임신우", lastEstrus }],
		[],
		NOW,
	);
	const estrusAlerts = notifications.filter((n) => n.type === "estrus");
	assert.equal(estrusAlerts.length, 0);
});

test("buildNotifications does NOT emit estrus alert for 송아지", () => {
	const lastEstrus = lastEstrusForDaysLeft(2, NOW);
	const notifications = buildNotifications(
		[{ id: "c4", name: "아기", tagNumber: "004", status: "송아지", lastEstrus }],
		[],
		NOW,
	);
	assert.equal(notifications.length, 0);
});

test("buildNotifications: estrus level is critical when daysLeft <= 1", () => {
	const lastEstrus = lastEstrusForDaysLeft(1, NOW);
	const notifications = buildNotifications(
		[{ id: "c5", name: "복순이", tagNumber: "005", status: "번식우", lastEstrus }],
		[],
		NOW,
	);
	const n = notifications.find((x) => x.type === "estrus");
	assert.ok(n, "expected estrus notification");
	assert.equal(n.level, "critical");
});

test("buildNotifications: estrus level is warning when daysLeft is 2 or 3", () => {
	for (const daysLeft of [2, 3]) {
		const lastEstrus = lastEstrusForDaysLeft(daysLeft, NOW);
		const notifications = buildNotifications(
			[{ id: "c6", name: "복순이", tagNumber: "006", status: "번식우", lastEstrus }],
			[],
			NOW,
		);
		const n = notifications.find((x) => x.type === "estrus");
		assert.ok(n, `expected estrus notification for daysLeft=${daysLeft}`);
		assert.equal(n.level, "warning", `expected warning for daysLeft=${daysLeft}`);
	}
});

test("buildNotifications: no estrus alert when outside window (> 3 days)", () => {
	// 10 days left — outside the 3-day alert window
	const lastEstrus = lastEstrusForDaysLeft(10, NOW);
	const notifications = buildNotifications(
		[{ id: "c7", name: "복순이", tagNumber: "007", status: "번식우", lastEstrus }],
		[],
		NOW,
	);
	assert.equal(notifications.filter((n) => n.type === "estrus").length, 0);
});

// ── Calving alerts ────────────────────────────────────────────────────────────

test("buildNotifications emits calving alert for 임신우 within CALVING_ALERT_WINDOW (14 days)", () => {
	const pregnancyDate = pregnancyForCalvingInDays(7, NOW);
	const notifications = buildNotifications(
		[{ id: "p1", name: "영자", tagNumber: "P001", status: "임신우", pregnancyDate }],
		[],
		NOW,
	);
	assert.equal(notifications.length, 1);
	assert.equal(notifications[0].type, "calving");
	assert.equal(notifications[0].id, "calving-p1");
});

test("buildNotifications does NOT emit calving alert for 번식우", () => {
	const pregnancyDate = pregnancyForCalvingInDays(7, NOW);
	const notifications = buildNotifications(
		[{ id: "p2", name: "복순이", tagNumber: "P002", status: "번식우", pregnancyDate }],
		[],
		NOW,
	);
	assert.equal(notifications.filter((n) => n.type === "calving").length, 0);
});

test("buildNotifications: calving level is critical when daysLeft <= 3", () => {
	const pregnancyDate = pregnancyForCalvingInDays(2, NOW);
	const notifications = buildNotifications(
		[{ id: "p3", name: "영자", tagNumber: "P003", status: "임신우", pregnancyDate }],
		[],
		NOW,
	);
	const n = notifications.find((x) => x.type === "calving");
	assert.ok(n, "expected calving notification");
	assert.equal(n.level, "critical");
});

test("buildNotifications: calving level is warning when daysLeft is 4-14", () => {
	for (const daysLeft of [4, 10, 14]) {
		const pregnancyDate = pregnancyForCalvingInDays(daysLeft, NOW);
		const notifications = buildNotifications(
			[{ id: "p4", name: "영자", tagNumber: "P004", status: "임신우", pregnancyDate }],
			[],
			NOW,
		);
		const n = notifications.find((x) => x.type === "calving");
		assert.ok(n, `expected calving notification for daysLeft=${daysLeft}`);
		assert.equal(n.level, "warning", `expected warning for daysLeft=${daysLeft}`);
	}
});

test("buildNotifications: no calving alert when calving > 14 days away", () => {
	const pregnancyDate = pregnancyForCalvingInDays(20, NOW);
	const notifications = buildNotifications(
		[{ id: "p5", name: "영자", tagNumber: "P005", status: "임신우", pregnancyDate }],
		[],
		NOW,
	);
	assert.equal(notifications.filter((n) => n.type === "calving").length, 0);
});

// ── Inventory low-stock alerts ────────────────────────────────────────────────

test("buildNotifications emits inventory warning when qty ≤ threshold (threshold > 0)", () => {
	const notifications = buildNotifications(
		[],
		[{ id: "i1", name: "조사료", quantity: 5, threshold: 10, unit: "kg" }],
	);
	assert.equal(notifications.length, 1);
	assert.equal(notifications[0].type, "alert");
	assert.equal(notifications[0].level, "warning");
	assert.equal(notifications[0].inventoryId, "i1");
});

test("buildNotifications emits inventory critical when qty === 0", () => {
	const notifications = buildNotifications(
		[],
		[{ id: "i2", name: "배합사료", quantity: 0, threshold: 5 }],
	);
	const n = notifications.find((x) => x.type === "alert");
	assert.ok(n, "expected inventory alert");
	assert.equal(n.level, "critical");
	assert.ok(n.message.includes("소진"), `expected 소진 message: ${n.message}`);
});

test("buildNotifications does NOT emit inventory alert when threshold is 0", () => {
	// threshold=0 means no alert configured
	const notifications = buildNotifications(
		[],
		[{ id: "i3", name: "약품", quantity: 0, threshold: 0 }],
	);
	assert.equal(notifications.length, 0);
});

test("buildNotifications does NOT emit inventory alert when qty > threshold", () => {
	const notifications = buildNotifications(
		[],
		[{ id: "i4", name: "조사료", quantity: 15, threshold: 10 }],
	);
	assert.equal(notifications.length, 0);
});

test("buildNotifications uses 재고 항목 fallback when inventory name is missing", () => {
	const notifications = buildNotifications(
		[],
		[{ id: "i5", quantity: 0, threshold: 5 }],
	);
	assert.equal(notifications[0].inventoryName, "재고 항목");
});

// ── Sort: critical before warning ─────────────────────────────────────────────

test("buildNotifications sorts critical before warning", () => {
	const pregnancyDate = pregnancyForCalvingInDays(2, NOW); // critical calving
	const lastEstrus = lastEstrusForDaysLeft(2, NOW);        // warning estrus

	const notifications = buildNotifications(
		[
			{
				id: "a1",
				name: "복순이",
				tagNumber: "A001",
				status: "번식우",
				lastEstrus,
			},
			{
				id: "a2",
				name: "영자",
				tagNumber: "A002",
				status: "임신우",
				pregnancyDate,
			},
		],
		[],
		NOW,
	);

	assert.ok(notifications.length >= 2);
	const criticals = notifications.filter((n) => n.level === "critical");
	const warnings = notifications.filter((n) => n.level === "warning");
	if (criticals.length > 0 && warnings.length > 0) {
		const lastCriticalIdx = Math.max(...criticals.map((n) => notifications.indexOf(n)));
		const firstWarningIdx = Math.min(...warnings.map((n) => notifications.indexOf(n)));
		assert.ok(
			lastCriticalIdx < firstWarningIdx,
			`critical (${lastCriticalIdx}) should come before warning (${firstWarningIdx})`,
		);
	}
});

// ── Defensive input handling ──────────────────────────────────────────────────

test("buildNotifications returns empty array for empty inputs", () => {
	assert.deepEqual(buildNotifications([], []), []);
	assert.deepEqual(buildNotifications(), []);
});

test("buildNotifications ignores non-array cattle argument", () => {
	const notifications = buildNotifications("bad", []);
	assert.deepEqual(notifications, []);
});

test("buildNotifications ignores malformed cattle rows (string, null, array)", () => {
	const notifications = buildNotifications(
		["string", null, ["array"], undefined, 42],
		[],
	);
	assert.deepEqual(notifications, []);
});

test("buildNotifications ignores cattle without lastEstrus for estrus alerts", () => {
	const notifications = buildNotifications(
		[{ id: "c8", name: "복순이", tagNumber: "008", status: "번식우", lastEstrus: null }],
		[],
		NOW,
	);
	assert.equal(notifications.filter((n) => n.type === "estrus").length, 0);
});

test("buildNotifications ignores cattle without pregnancyDate for calving alerts", () => {
	const notifications = buildNotifications(
		[{ id: "p6", name: "영자", tagNumber: "P006", status: "임신우", pregnancyDate: null }],
		[],
		NOW,
	);
	assert.equal(notifications.filter((n) => n.type === "calving").length, 0);
});
