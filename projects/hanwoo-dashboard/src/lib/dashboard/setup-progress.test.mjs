import assert from "node:assert/strict";
import test from "node:test";

import { buildSetupProgressItems } from "./setup-progress.mjs";

test("buildSetupProgressItems identifies the next incomplete onboarding step", () => {
	const progress = buildSetupProgressItems({
		farmSettings: { name: "주호목장", location: "전북 남원" },
		buildings: [{ id: "b1", name: "1동" }],
		cattleList: [],
		inventoryList: [],
		scheduleEvents: [],
	});

	assert.equal(progress.completed, 2);
	assert.equal(progress.total, 5);
	assert.equal(progress.percent, 40);
	assert.equal(progress.nextItem.id, "cattle");
	assert.equal(progress.nextItem.actionId, "add-cattle");
});

test("buildSetupProgressItems routes missing buildings to the add-building flow", () => {
	const progress = buildSetupProgressItems({
		farmSettings: { name: "주호목장", location: "전북 남원" },
		buildings: [],
	});

	assert.equal(progress.nextItem.id, "buildings");
	assert.equal(progress.nextItem.targetTab, "settings");
	assert.equal(progress.nextItem.actionId, "add-building");
});

test("buildSetupProgressItems routes missing inventory and schedule to add forms", () => {
	const progress = buildSetupProgressItems({
		farmSettings: { name: "주호목장", location: "전북 남원" },
		buildings: [{ id: "b1", name: "1동" }],
		cattleList: [{ id: "c1", earTag: "001" }],
		inventoryList: [],
		scheduleEvents: [],
	});

	const inventoryItem = progress.items.find((item) => item.id === "inventory");
	const scheduleItem = progress.items.find((item) => item.id === "schedule");

	assert.equal(progress.nextItem.id, "inventory");
	assert.equal(inventoryItem.targetTab, "inventory");
	assert.equal(inventoryItem.actionId, "add-inventory");
	assert.equal(scheduleItem.targetTab, "schedule");
	assert.equal(scheduleItem.actionId, "add-schedule");
});

test("buildSetupProgressItems ignores malformed collection rows", () => {
	const progress = buildSetupProgressItems({
		farmSettings: { name: "Farm", location: "Namwon" },
		buildings: ["b1", null, ["array-building"]],
		cattleList: [undefined, "c1", ["array-cattle"]],
		inventoryList: [false, ["array-inventory"]],
		scheduleEvents: ["s1", ["array-schedule"]],
	});

	assert.equal(progress.completed, 1);
	assert.equal(progress.percent, 20);
	assert.equal(progress.nextItem.id, "buildings");
	assert.deepEqual(
		progress.items.map((item) => item.done),
		[true, false, false, false, false],
	);
});

test("buildSetupProgressItems ignores malformed top-level options", () => {
	for (const value of [null, [], "bad-options"]) {
		const progress = buildSetupProgressItems(value);

		assert.equal(progress.completed, 0);
		assert.equal(progress.total, 5);
		assert.equal(progress.percent, 0);
		assert.equal(progress.nextItem.id, "farm-profile");
		assert.deepEqual(
			progress.items.map((item) => item.done),
			[false, false, false, false, false],
		);
	}
});

test("buildSetupProgressItems marks setup complete when all required operating data exists", () => {
	const progress = buildSetupProgressItems({
		farmSettings: { name: "주호목장", location: "전북 남원" },
		buildings: [{ id: "b1" }],
		cattleList: [{ id: "c1" }],
		inventoryList: [{ id: "i1" }],
		scheduleEvents: [{ id: "s1" }],
	});

	assert.equal(progress.completed, 5);
	assert.equal(progress.percent, 100);
	assert.equal(progress.nextItem, null);
	assert.deepEqual(
		progress.items.map((item) => item.done),
		[true, true, true, true, true],
	);
});
