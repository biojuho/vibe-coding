import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import {
	DATA_DIR_ENV,
	dashboardDataFile,
	getDashboardDataDir,
	readJsonFileResult,
} from "./dashboard-data.ts";

test("readJsonFileResult returns 200 with parsed data for valid JSON", async () => {
	const dir = await mkdtemp(path.join(tmpdir(), "kd-data-"));
	try {
		const file = path.join(dir, "ok.json");
		await writeFile(file, JSON.stringify({ a: 1, nested: { b: 2 } }), "utf8");

		const result = await readJsonFileResult(file, "not found");
		assert.equal(result.status, 200);
		assert.deepEqual(
			result.status === 200 ? result.data : null,
			{ a: 1, nested: { b: 2 } },
		);
	} finally {
		await rm(dir, { recursive: true, force: true });
	}
});

test("readJsonFileResult returns 404 with the supplied message when absent", async () => {
	const result = await readJsonFileResult(
		path.join(tmpdir(), "kd-does-not-exist-xyz.json"),
		"custom not found",
	);
	assert.equal(result.status, 404);
	assert.equal(result.status === 404 ? result.error : "", "custom not found");
});

test("readJsonFileResult returns 500 on malformed JSON and does NOT leak file contents", async () => {
	const dir = await mkdtemp(path.join(tmpdir(), "kd-data-"));
	try {
		const secret = "SECRET_TOKEN_should_not_leak {";
		const file = path.join(dir, "bad.json");
		await writeFile(file, secret, "utf8");

		const result = await readJsonFileResult(file, "not found");
		assert.equal(result.status, 500);
		const body = result.status === 500 ? result.error : "";
		assert.equal(body, "Internal Server Error");
		assert.ok(
			!body.includes("SECRET_TOKEN"),
			"raw file contents must never appear in the error body",
		);
	} finally {
		await rm(dir, { recursive: true, force: true });
	}
});

test("dashboardDataFile uses the configured runtime data directory", async () => {
	const previous = process.env[DATA_DIR_ENV];
	const dir = await mkdtemp(path.join(tmpdir(), "kd-runtime-data-"));
	try {
		process.env[DATA_DIR_ENV] = dir;
		assert.equal(getDashboardDataDir(), path.resolve(dir));
		assert.equal(
			dashboardDataFile("skill_lint.json"),
			path.join(dir, "skill_lint.json"),
		);
	} finally {
		if (previous === undefined) {
			delete process.env[DATA_DIR_ENV];
		} else {
			process.env[DATA_DIR_ENV] = previous;
		}
		await rm(dir, { recursive: true, force: true });
	}
});
