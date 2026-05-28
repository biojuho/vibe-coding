import assert from "node:assert/strict";
import test from "node:test";

import {
	buildNotificationTiming,
	formatNotificationTime,
	getNotificationTargetDate,
} from "./notification-timing.mjs";

test("getNotificationTargetDate advances estrus alerts to the next expected cycle", () => {
	const result = getNotificationTargetDate(
		"estrus",
		"2026-03-01T00:00:00.000Z",
		{
			now: "2026-04-07T00:00:00.000Z",
		},
	);

	assert.equal(result?.toISOString(), "2026-04-12T00:00:00.000Z");
});

test("getNotificationTargetDate converts pregnancy dates into calving dates", () => {
	const result = getNotificationTargetDate(
		"calving",
		"2026-01-01T00:00:00.000Z",
	);

	assert.equal(result?.toISOString(), "2026-10-13T00:00:00.000Z");
});

test("getNotificationTargetDate ignores malformed options input", () => {
	const result = getNotificationTargetDate(
		"calving",
		"2026-01-01T00:00:00.000Z",
		null,
	);

	assert.equal(result?.toISOString(), "2026-10-13T00:00:00.000Z");
});

test("getNotificationTargetDate ignores array option fields", () => {
	const options = [];
	options.now = "2026-04-07T00:00:00.000Z";

	const before = new Date();
	const result = getNotificationTargetDate(
		"estrus",
		"2026-03-01T00:00:00.000Z",
		options,
	);

	assert.ok(result instanceof Date);
	assert.ok(result > before);
	assert.notEqual(result.toISOString(), "2026-04-12T00:00:00.000Z");
});

test("getNotificationTargetDate falls back to the current time when estrus options are malformed", () => {
	const before = new Date();
	const result = getNotificationTargetDate(
		"estrus",
		"2026-03-01T00:00:00.000Z",
		null,
	);

	assert.ok(result instanceof Date);
	assert.ok(result > before);
});

test("buildNotificationTiming returns stable iso timestamps for estrus notifications", () => {
	const result = buildNotificationTiming("estrus", "2026-03-01T00:00:00.000Z", {
		now: "2026-04-07T00:00:00.000Z",
	});

	assert.equal(result.date, "2026-04-12T00:00:00.000Z");
	assert.equal(result.targetDate, "2026-04-12T00:00:00.000Z");
	assert.equal(result.time, formatNotificationTime("2026-04-12T00:00:00.000Z"));
});

test("buildNotificationTiming returns an empty shape for invalid dates", () => {
	const result = buildNotificationTiming("calving", "not-a-date");

	assert.deepEqual(result, {
		date: null,
		time: "알림 시간 확인 불가",
		targetDate: null,
	});
});

test("buildNotificationTiming rejects impossible calendar dates", () => {
	const result = buildNotificationTiming("calving", "2026-02-31T00:00:00.000Z");

	assert.deepEqual(result, {
		date: null,
		time: "알림 시간 확인 불가",
		targetDate: null,
	});
});

test("formatNotificationTime uses explicit Korean copy for invalid dates", () => {
	assert.equal(formatNotificationTime("not-a-date"), "알림 시간 확인 불가");
});
