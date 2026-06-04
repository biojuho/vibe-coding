import assert from "node:assert/strict";
import test from "node:test";

import { buildInfraEntries, resolveVerdict } from "./qaqc-view.ts";

test("resolveVerdict passes known verdicts and falls back to REJECTED", () => {
	assert.equal(resolveVerdict("APPROVED"), "APPROVED");
	assert.equal(resolveVerdict("CONDITIONALLY_APPROVED"), "CONDITIONALLY_APPROVED");
	assert.equal(resolveVerdict("REJECTED"), "REJECTED");
	assert.equal(resolveVerdict("WAT"), "REJECTED");
	assert.equal(resolveVerdict(""), "REJECTED");
});

test("buildInfraEntries applies boundary thresholds (disk >10, scheduler ready>0)", () => {
	const entries = buildInfraEntries({
		docker: true,
		ollama: false,
		scheduler: { ready: 0, total: 3 },
		disk_gb_free: 10,
	});
	const byKey = Object.fromEntries(entries.map((e) => [e.key, e]));

	assert.equal(byKey.docker.ok, true);
	assert.equal(byKey.ollama.ok, false);
	assert.equal(byKey.scheduler.ok, false, "ready=0 is not ok");
	assert.equal(byKey.scheduler.label, "Scheduler 0/3");
	assert.equal(byKey.disk.ok, false, "exactly 10GB is not above the floor");
	assert.equal(byKey.disk.label, "10 GB Free");

	const ok = buildInfraEntries({
		scheduler: { ready: 1, total: 1 },
		disk_gb_free: 11,
	});
	const okByKey = Object.fromEntries(ok.map((e) => [e.key, e]));
	assert.equal(okByKey.scheduler.ok, true);
	assert.equal(okByKey.disk.ok, true);
});

test("buildInfraEntries tolerates missing fields", () => {
	const entries = buildInfraEntries({});
	const disk = entries.find((e) => e.key === "disk");
	assert.equal(disk?.label, "? GB Free");
	assert.equal(disk?.ok, false);
});
