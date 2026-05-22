import assert from "node:assert/strict";
import test from "node:test";

import { buildTodayFocusItems } from "./today-focus.mjs";

test("buildTodayFocusItems prioritizes offline, critical alerts, schedules, and low stock", () => {
	const items = buildTodayFocusItems({
		isOnline: false,
		now: new Date("2026-05-18T10:00:00+09:00"),
		notifications: [
			{ id: "n1", level: "critical", message: "critical calving alert" },
			{ id: "n2", level: "warning", message: "warning alert" },
		],
		scheduleEvents: [
			{
				id: "s2",
				title: "barn cleanup",
				date: "2026-05-20",
				isCompleted: false,
			},
			{
				id: "s1",
				title: "vaccination",
				date: "2026-05-19",
				isCompleted: false,
			},
		],
		inventoryList: [
			{ id: "i1", name: "feed mix", quantity: 4, threshold: 5, unit: "kg" },
			{ id: "i2", name: "straw", quantity: 20, threshold: 5, unit: "kg" },
		],
		monthlySalesCount: 3,
	});

	assert.deepEqual(
		items.map((item) => item.id),
		["offline", "critical-alerts", "next-schedule", "low-stock"],
	);
	assert.equal(items[2].title, "vaccination");
	assert.match(items[3].detail, /^feed mix: 4kg/);
});

test("buildTodayFocusItems ignores malformed inventory quantities for low stock", () => {
	const items = buildTodayFocusItems({
		now: new Date("2026-05-18T10:00:00+09:00"),
		inventoryList: [
			{
				id: "bad-quantity",
				name: "bad quantity",
				quantity: "not-a-number",
				threshold: 10,
				unit: "kg",
			},
			{
				id: "empty-quantity",
				name: "empty quantity",
				quantity: "",
				threshold: 10,
				unit: "kg",
			},
			{
				id: "bad-threshold",
				name: "bad threshold",
				quantity: 1,
				threshold: "not-a-number",
				unit: "kg",
			},
			{
				id: "ok",
				name: "normal stock",
				quantity: "4",
				threshold: "5",
				unit: "kg",
			},
		],
		monthlySalesCount: 0,
	});

	const lowStockItem = items.find((item) => item.id === "low-stock");
	assert.equal(lowStockItem?.title.startsWith("1"), true);
	assert.match(lowStockItem?.detail ?? "", /^normal stock: 4kg/);
	assert.equal(
		items.some((item) => item.title === "bad quantity"),
		false,
	);
});

test("buildTodayFocusItems keeps a useful sales prompt when no urgent work exists", () => {
	const items = buildTodayFocusItems({
		now: new Date("2026-05-18T10:00:00+09:00"),
		monthlySalesCount: 0,
	});

	assert.deepEqual(
		items.map((item) => item.id),
		["monthly-sales"],
	);
	assert.equal(items[0].type, "sales");
	assert.equal(items[0].targetTab, "sales");
	assert.equal(items[0].tone, "neutral");
});

test("buildTodayFocusItems skips malformed schedule dates", () => {
	const items = buildTodayFocusItems({
		now: new Date("2026-05-18T10:00:00+09:00"),
		scheduleEvents: [
			{
				id: "bad",
				title: "bad schedule",
				date: "not-a-date",
				isCompleted: false,
			},
			{
				id: "past",
				title: "past schedule",
				date: "2026-05-17",
				isCompleted: false,
			},
			{
				id: "done",
				title: "done schedule",
				date: "2026-05-18",
				isCompleted: true,
			},
			{
				id: "next",
				title: "valid schedule",
				date: "2026-05-19",
				isCompleted: false,
			},
		],
		monthlySalesCount: 0,
	});

	const scheduleItem = items.find((item) => item.id === "next-schedule");
	assert.equal(scheduleItem?.title, "valid schedule");
	assert.equal(
		items.some((item) => item.title === "bad schedule"),
		false,
	);
});
