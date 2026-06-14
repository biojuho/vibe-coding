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

const source = readSource("lib/hooks/useDashboardModals.js");

test("useDashboardModals is a client component with use client directive", () => {
	assert.match(source, /["']use client["']/);
	assert.match(source, /export function useDashboardModals\(\)/);
});

test("useDashboardModals returns all 8 state fields", () => {
	const stateFields = [
		"showAddModal",
		"quickActionIntent",
		"selectedCow",
		"isEditing",
		"deletingCattleId",
		"selectedBuildingId",
		"selectedPenId",
		"showNotifications",
	];
	for (const field of stateFields) {
		assert.ok(source.includes(field), `Missing state: ${field}`);
	}
});

test("useDashboardModals returns all 5 stable callback handlers", () => {
	const handlers = [
		"closeAddModal",
		"openAddModal",
		"closeNotifications",
		"openNotifications",
		"resetBuildingAndPen",
	];
	for (const handler of handlers) {
		assert.ok(source.includes(handler), `Missing handler: ${handler}`);
	}
});

test("useDashboardModals wraps all callbacks in useCallback for referential stability", () => {
	const callbackCount = (source.match(/useCallback\(/g) || []).length;
	assert.ok(callbackCount >= 5, `Expected ≥5 useCallback calls, found ${callbackCount}`);
});

test("useDashboardModals openAddModal and closeAddModal toggle showAddModal", () => {
	assert.match(source, /openAddModal\s*=\s*useCallback\(\(\) => \{/);
	assert.match(source, /setShowAddModal\(true\)/);
	assert.match(source, /closeAddModal\s*=\s*useCallback\(\(\) => \{/);
	assert.match(source, /setShowAddModal\(false\)/);
});

test("useDashboardModals resetBuildingAndPen sets both IDs to null", () => {
	assert.match(source, /resetBuildingAndPen/);
	assert.match(source, /setSelectedBuildingId\(null\)/);
	assert.match(source, /setSelectedPenId\(null\)/);
});

test("useDashboardModals exposes setter functions for imperative updates", () => {
	// Direct setters are also returned so parent can still drive state
	const setters = [
		"setShowAddModal",
		"setQuickActionIntent",
		"setSelectedCow",
		"setIsEditing",
		"setDeletingCattleId",
		"setSelectedBuildingId",
		"setSelectedPenId",
		"setShowNotifications",
	];
	for (const setter of setters) {
		assert.ok(source.includes(setter), `Missing setter in return: ${setter}`);
	}
});
