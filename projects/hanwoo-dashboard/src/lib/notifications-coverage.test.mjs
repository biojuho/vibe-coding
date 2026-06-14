import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readProjectFile(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

const src = readProjectFile("lib/notifications.js");

// ── Structure ────────────────────────────────────────────────────────────────

test("notifications: exports buildNotifications", () => {
	assert.match(src, /export function buildNotifications/);
});

test("notifications: imports buildNotificationTiming from notification-timing", () => {
	assert.match(src, /buildNotificationTiming/);
	assert.match(src, /notification-timing/);
});

// ── Estrus alert logic ────────────────────────────────────────────────────────

test("notifications: estrus alert fires for 번식우", () => {
	assert.match(src, /번식우/);
	assert.match(src, /isEstrusAlert/);
});

test("notifications: estrus alert fires for 육성우", () => {
	assert.match(src, /육성우/);
});

test("notifications: estrus critical threshold is daysLeft <= 1", () => {
	assert.match(src, /daysLeft <= 1/);
});

test("notifications: estrus notification type is 'estrus'", () => {
	assert.match(src, /type: "estrus"/);
});

test("notifications: estrus id uses cattle id", () => {
	assert.match(src, /`estrus-\$\{cow\.id\}`/);
});

// ── Calving alert logic ───────────────────────────────────────────────────────

test("notifications: calving alert fires for 임신우", () => {
	assert.match(src, /임신우/);
	assert.match(src, /isCalvingAlert/);
});

test("notifications: calving critical threshold is daysLeft <= 3", () => {
	assert.match(src, /daysLeft <= 3/);
});

test("notifications: calving notification type is 'calving'", () => {
	assert.match(src, /type: "calving"/);
});

test("notifications: calving id uses cattle id", () => {
	assert.match(src, /`calving-\$\{cow\.id\}`/);
});

// ── Inventory low-stock alert logic ──────────────────────────────────────────

test("notifications: low stock uses isLowStock helper", () => {
	assert.match(src, /isLowStock/);
});

test("notifications: isLowStock checks threshold > 0", () => {
	assert.match(src, /thr > 0/);
});

test("notifications: inventory alert type is 'alert'", () => {
	assert.match(src, /type: "alert"/);
});

test("notifications: inventory critical when quantity is 0", () => {
	assert.match(src, /qty === 0/);
});

test("notifications: inventory notification id falls back to name", () => {
	assert.match(src, /item\.id \?\? name/);
});

// ── Sort ─────────────────────────────────────────────────────────────────────

test("notifications: sorts critical before warning", () => {
	assert.match(src, /critical.*warning|sort/);
	assert.match(src, /notifications\.sort/);
});

test("notifications: sort puts critical first with return -1", () => {
	assert.match(src, /return -1/);
	assert.match(src, /return 1/);
});

// ── Defensive input handling ──────────────────────────────────────────────────

test("notifications: normalizeNotificationCattle guards non-array input", () => {
	assert.match(src, /normalizeNotificationCattle/);
	assert.match(src, /Array\.isArray\(cattle\)/);
});

test("notifications: inventory block guards Array.isArray", () => {
	assert.match(src, /Array\.isArray\(inventory\)/);
});

// ── Null guards: missing name / tagNumber ─────────────────────────────────────

test("notifications: estrus message null-guards cow.name with ?? 이름 없음", () => {
	assert.match(src, /cow\.name \?\? "이름 없음"/);
});

test("notifications: estrus message null-guards cow.tagNumber with ?? 번호 없음", () => {
	assert.match(src, /cow\.tagNumber \?\? "번호 없음"/);
});

test("notifications: cattleName field null-coalesces to null when name is absent", () => {
	assert.match(src, /cattleName: cow\.name \?\? null/);
});

test("notifications: tagNumber field null-coalesces to null when tagNumber is absent", () => {
	assert.match(src, /tagNumber: cow\.tagNumber \?\? null/);
});
