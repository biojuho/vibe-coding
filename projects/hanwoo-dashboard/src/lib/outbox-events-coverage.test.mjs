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

const source = readSource("lib/dashboard/events.js");

test("events exports DASHBOARD_EVENT_TOPICS with all 9 topic constants", () => {
	assert.match(source, /DASHBOARD_EVENT_TOPICS/);
	assert.match(source, /Object\.freeze\(/);
	const topics = [
		"CATTLE_CREATED",
		"CATTLE_UPDATED",
		"CATTLE_ARCHIVED",
		"SALE_RECORDED",
		"EXPENSE_RECORDED",
		"FEED_RECORDED",
		"FARM_SETTINGS_UPDATED",
		"MARKET_PRICE_REFRESHED",
		"PAYMENT_CONFIRMED",
	];
	for (const topic of topics) {
		assert.ok(source.includes(topic), `Missing topic constant: ${topic}`);
	}
});

test("events exports all 6 outbox CRUD functions", () => {
	const fns = [
		"createOutboxEvent",
		"listPendingOutboxEvents",
		"markOutboxEventProcessing",
		"markOutboxEventDone",
		"rescheduleOutboxEvent",
		"markOutboxEventFailed",
	];
	for (const fn of fns) {
		assert.match(source, new RegExp(`export async function ${fn}\\(`), `Missing: ${fn}`);
	}
});

test("events createOutboxEvent defaults status to PENDING and availableAt to now", () => {
	assert.match(source, /createOutboxEvent/);
	assert.match(source, /status: input\.status \?\? ["']PENDING["']/);
	assert.match(source, /availableAt: input\.availableAt \?\? new Date\(\)/);
	assert.match(source, /aggregateId: input\.aggregateId \?\? null/);
	assert.match(source, /payload: input\.payload \?\? \{\}/);
});

test("events listPendingOutboxEvents queries PENDING status with lte availableAt", () => {
	assert.match(source, /listPendingOutboxEvents/);
	assert.match(source, /status: ["']PENDING["']/);
	assert.match(source, /availableAt:/);
	assert.match(source, /lte: new Date\(\)/);
	assert.match(source, /orderBy/);
	assert.match(source, /take: limit/);
});

test("events markOutboxEventProcessing increments attempts counter atomically", () => {
	assert.match(source, /markOutboxEventProcessing/);
	assert.match(source, /status: ["']PROCESSING["']/);
	assert.match(source, /attempts:/);
	assert.match(source, /increment: 1/);
});

test("events rescheduleOutboxEvent delays by configurable seconds with PENDING status", () => {
	assert.match(source, /rescheduleOutboxEvent/);
	assert.match(source, /delaySeconds = 30/);
	assert.match(source, /delaySeconds \* 1000/);
	assert.match(source, /status: ["']PENDING["']/);
	assert.match(source, /availableAt/);
});

test("events markOutboxEventFailed sets terminal FAILED status", () => {
	assert.match(source, /markOutboxEventFailed/);
	assert.match(source, /status: ["']FAILED["']/);
});

test("events resolveClient falls back to module-level prisma when no client is provided", () => {
	assert.match(source, /resolveClient/);
	assert.match(source, /client \?\? prisma/);
	assert.match(source, /import prisma from/);
});
