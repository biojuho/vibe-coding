import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const PORT = process.env.SMOKE_PORT ?? "3102";
const HOST = "127.0.0.1";
const BASE_URL = `http://${HOST}:${PORT}`;
const API_KEY = process.env.DASHBOARD_API_KEY ?? "smoke-dashboard-key";
const DATA_DIR = path.join(process.cwd(), "data");

// Fixtures shaped to satisfy the hardened payload guards in src/lib/dashboard-payload.ts.
const FIXTURES = {
	"dashboard_data.json": {
		last_updated: "2026-04-02T00:00:00.000Z",
		github: [],
		notebooklm: [],
		sessions: [],
	},
	"qaqc_result.json": {
		timestamp: "2026-04-02T00:00:00.000Z",
		verdict: "APPROVED",
		elapsed_sec: 1,
		projects: {},
		total: { passed: 1, failed: 0 },
		ast_check: { total: 1, ok: 1, failures: [] },
		security_scan: { status: "CLEAR", issues: [] },
		infrastructure: {
			docker: true,
			ollama: true,
			scheduler: { ready: 1, total: 1 },
			disk_gb_free: 100,
		},
		trend: [
			{ date: "2026-04-01", passed: 1, failed: 0 },
			{ date: "2026-04-02", passed: 1, failed: 0 },
		],
	},
	"product_readiness.json": {
		generated_at: "2026-04-02T00:00:00.000Z",
		overall: {
			score: 90,
			state: "ready",
			project_count: 1,
			blocked_count: 0,
			workspace_blocker_count: 0,
		},
		projects: [],
		workspace_blockers: [],
		next_actions: [],
	},
	"skill_lint.json": {
		generated_at: "2026-04-02T00:00:00.000Z",
		summary: {
			status: "pass",
			score: 100,
			skill_count: 1,
			healthy_count: 1,
			warning_count: 0,
			error_count: 0,
			issue_count: 0,
		},
		top_issues: [],
		issues: [],
	},
};

// Back up any real data files, write deterministic fixtures, and restore on exit
// so the smoke run never depends on (or destroys) locally synced data.
async function withFixtures(run) {
	await mkdir(DATA_DIR, { recursive: true });
	const backups = new Map();

	for (const name of Object.keys(FIXTURES)) {
		const file = path.join(DATA_DIR, name);
		try {
			backups.set(name, await readFile(file, "utf8"));
		} catch {
			backups.set(name, null); // did not exist
		}
		await writeFile(file, JSON.stringify(FIXTURES[name], null, 2), "utf8");
	}

	try {
		return await run();
	} finally {
		for (const [name, original] of backups) {
			const file = path.join(DATA_DIR, name);
			if (original === null) {
				await rm(file, { force: true });
			} else {
				await writeFile(file, original, "utf8");
			}
		}
	}
}

function startServer() {
	const env = { ...process.env, PORT, DASHBOARD_API_KEY: API_KEY };
	const nextBin = path.join(
		process.cwd(),
		"node_modules",
		"next",
		"dist",
		"bin",
		"next",
	);
	const child = spawn(
		process.execPath,
		[nextBin, "start", "--port", PORT, "--hostname", HOST],
		{ cwd: process.cwd(), env, stdio: ["ignore", "pipe", "pipe"] },
	);
	child.stdout?.on("data", (chunk) =>
		process.stdout.write(`[knowledge-smoke] ${chunk}`),
	);
	child.stderr?.on("data", (chunk) =>
		process.stderr.write(`[knowledge-smoke] ${chunk}`),
	);
	return child;
}

async function waitForServer(pathname = "/", timeoutMs = 45000) {
	const startedAt = Date.now();
	while (Date.now() - startedAt < timeoutMs) {
		try {
			const response = await fetch(`${BASE_URL}${pathname}`, {
				redirect: "manual",
			});
			if (response.status < 500) return;
		} catch {
			// Server still booting.
		}
		await delay(500);
	}
	throw new Error(`Timed out waiting for ${pathname} on ${BASE_URL}`);
}

async function stopServer(child) {
	if (child.exitCode !== null) return;
	child.kill("SIGTERM");
	await Promise.race([
		new Promise((resolve) => child.once("exit", resolve)),
		delay(5000),
	]);
	if (child.exitCode === null) {
		child.kill("SIGKILL");
		await new Promise((resolve) => child.once("exit", resolve));
	}
}

const DATA_ROUTES = [
	"/api/data/dashboard",
	"/api/data/qaqc",
	"/api/data/readiness",
	"/api/data/skills",
];

async function run() {
	const server = startServer();
	try {
		await waitForServer();

		// 1) Page shell renders.
		const pageResponse = await fetch(`${BASE_URL}/`, { redirect: "manual" });
		assert.equal(pageResponse.status, 200, "dashboard root should load");
		assert(
			(await pageResponse.text()).toLowerCase().includes("<html"),
			"root page should render the app shell",
		);

		// 2) Security headers are applied.
		assert.equal(
			pageResponse.headers.get("x-frame-options"),
			"DENY",
			"X-Frame-Options should be set",
		);
		assert(
			pageResponse.headers.get("content-security-policy"),
			"CSP header should be present",
		);

		// 3) Health endpoint is unauthenticated and healthy (key is configured).
		const health = await fetch(`${BASE_URL}/api/health`, { redirect: "manual" });
		assert.equal(health.status, 200, "health should be 200 with a key set");
		const healthJson = await health.json();
		assert.equal(healthJson.checks.apiKeyConfigured, true);

		// 4) All data routes reject missing auth.
		for (const route of DATA_ROUTES) {
			const res = await fetch(`${BASE_URL}${route}`, { redirect: "manual" });
			assert.equal(res.status, 401, `${route} should reject missing auth`);
		}

		// 5) Login: wrong key and malformed body -> 401.
		const wrongKey = await fetch(`${BASE_URL}/api/auth/session`, {
			method: "POST",
			headers: { "content-type": "application/json" },
			body: JSON.stringify({ apiKey: "definitely-wrong" }),
			redirect: "manual",
		});
		assert.equal(wrongKey.status, 401, "wrong key should be rejected");

		const malformed = await fetch(`${BASE_URL}/api/auth/session`, {
			method: "POST",
			headers: { "content-type": "application/json" },
			body: "not-json",
			redirect: "manual",
		});
		assert.equal(malformed.status, 401, "malformed body should be rejected");

		// 6) Login with the valid key sets a session cookie.
		const sessionResponse = await fetch(`${BASE_URL}/api/auth/session`, {
			method: "POST",
			headers: { "content-type": "application/json" },
			body: JSON.stringify({ apiKey: API_KEY }),
			redirect: "manual",
		});
		assert.equal(sessionResponse.status, 200, "valid key should log in");
		const setCookie = sessionResponse.headers.get("set-cookie");
		assert(
			setCookie?.includes("knowledge_dashboard_session="),
			"login should set the auth cookie",
		);
		const sessionCookie = setCookie.split(";", 1)[0];
		const authed = { cookie: sessionCookie };

		// 7) All four data routes return 200 with the cookie + expected keys.
		const expectations = {
			"/api/data/dashboard": (json) => Array.isArray(json.github),
			"/api/data/qaqc": (json) => json.verdict === "APPROVED",
			"/api/data/readiness": (json) => typeof json.overall?.score === "number",
			"/api/data/skills": (json) => typeof json.summary?.status === "string",
		};
		for (const route of DATA_ROUTES) {
			const res = await fetch(`${BASE_URL}${route}`, {
				headers: authed,
				redirect: "manual",
			});
			assert.equal(res.status, 200, `${route} should accept a session cookie`);
			assert(
				expectations[route](await res.json()),
				`${route} payload should match its expected shape`,
			);
		}

		// 8) Missing data file -> 404 (authenticated).
		const skillFile = path.join(DATA_DIR, "skill_lint.json");
		await rm(skillFile, { force: true });
		const missing = await fetch(`${BASE_URL}/api/data/skills`, {
			headers: authed,
			redirect: "manual",
		});
		assert.equal(missing.status, 404, "absent data file should 404");
		await writeFile(
			skillFile,
			JSON.stringify(FIXTURES["skill_lint.json"], null, 2),
			"utf8",
		);

		// 9) DELETE clears the cookie.
		const deleted = await fetch(`${BASE_URL}/api/auth/session`, {
			method: "DELETE",
			redirect: "manual",
		});
		assert.equal(deleted.status, 200, "logout should succeed");
		assert(
			deleted.headers.get("set-cookie")?.includes("Max-Age=0"),
			"logout should expire the cookie",
		);
	} finally {
		await stopServer(server);
	}

	console.log("knowledge-dashboard smoke checks passed");
}

withFixtures(run).catch((error) => {
	console.error(error);
	process.exitCode = 1;
});
