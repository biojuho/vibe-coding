import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";


const PORT = process.env.SMOKE_PORT ?? "3102";
const HOST = "127.0.0.1";
const BASE_URL = `http://${HOST}:${PORT}`;
const API_KEY = process.env.DASHBOARD_API_KEY ?? "smoke-dashboard-key";
const DATA_DIR = path.join(process.cwd(), "data");
const DASHBOARD_FILE = path.join(DATA_DIR, "dashboard_data.json");
const QAQC_FILE = path.join(DATA_DIR, "qaqc_result.json");

const dashboardFixture = {
  last_updated: "2026-04-02T00:00:00.000Z",
  github: [],
  notebooklm: [],
  sessions: [],
};

const qaqcFixture = {
  timestamp: "2026-04-02T00:00:00.000Z",
  verdict: "APPROVED",
  elapsed_sec: 1,
  projects: {},
  total: { passed: 1, failed: 0 },
  ast_check: { total: 1, ok: 1, failures: [] },
  security_scan: { status: "CLEAR", issues: [] },
  infrastructure: { docker: true, ollama: true, scheduler: { ready: 1, total: 1 }, disk_gb_free: 100 },
};


async function ensureFixture(filePath, data) {
  await mkdir(path.dirname(filePath), { recursive: true });

  try {
    await readFile(filePath, "utf8");
  } catch {
    await writeFile(filePath, JSON.stringify(data, null, 2), "utf8");
  }
}


function startServer() {
  const env = {
    ...process.env,
    PORT,
    DASHBOARD_API_KEY: API_KEY,
  };

  const nextBin = path.join(process.cwd(), "node_modules", "next", "dist", "bin", "next");
  const command = process.execPath;
  const args = [nextBin, "start", "--port", PORT, "--hostname", HOST];

  const child = spawn(command, args, {
    cwd: process.cwd(),
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });

  child.stdout?.on("data", (chunk) => process.stdout.write(`[knowledge-smoke] ${chunk}`));
  child.stderr?.on("data", (chunk) => process.stderr.write(`[knowledge-smoke] ${chunk}`));
  return child;
}


async function waitForServer(pathname = "/", timeoutMs = 45000) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(`${BASE_URL}${pathname}`, { redirect: "manual" });
      if (response.status < 500) {
        return;
      }
    } catch {
      // Server is still booting.
    }

    await delay(500);
  }

  throw new Error(`Timed out waiting for ${pathname} on ${BASE_URL}`);
}


async function stopServer(child) {
  if (child.exitCode !== null) {
    return;
  }

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


async function run() {
  await ensureFixture(DASHBOARD_FILE, dashboardFixture);
  await ensureFixture(QAQC_FILE, qaqcFixture);

  const server = startServer();

  try {
    await waitForServer();

    const pageResponse = await fetch(`${BASE_URL}/`, { redirect: "manual" });
    assert.equal(pageResponse.status, 200, "dashboard root should load");
    const pageHtml = await pageResponse.text();
    assert(pageHtml.includes("DASHBOARD_API_KEY"), "root page should render the API key gate");

    const unauthorizedDashboard = await fetch(`${BASE_URL}/api/data/dashboard`, { redirect: "manual" });
    assert.equal(unauthorizedDashboard.status, 401, "dashboard API should reject missing auth");

    const unauthorizedQaQc = await fetch(`${BASE_URL}/api/data/qaqc`, { redirect: "manual" });
    assert.equal(unauthorizedQaQc.status, 401, "qaqc API should reject missing auth");

    const sessionResponse = await fetch(`${BASE_URL}/api/auth/session`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ apiKey: API_KEY }),
      redirect: "manual",
    });
    assert.equal(sessionResponse.status, 200, "session login should accept a valid API key");
    const sessionCookieHeader = sessionResponse.headers.get("set-cookie");
    assert(sessionCookieHeader?.includes("knowledge_dashboard_session="), "session login should set an auth cookie");
    const sessionCookie = sessionCookieHeader.split(";", 1)[0];

    const dashboardResponse = await fetch(`${BASE_URL}/api/data/dashboard`, {
      headers: { cookie: sessionCookie },
      redirect: "manual",
    });
    assert.equal(dashboardResponse.status, 200, "dashboard API should accept a valid session cookie");
    const dashboardJson = await dashboardResponse.json();
    assert(Array.isArray(dashboardJson.github), "dashboard payload should include github data");
    assert(Array.isArray(dashboardJson.notebooklm), "dashboard payload should include notebook data");

    const qaqcResponse = await fetch(`${BASE_URL}/api/data/qaqc`, {
      headers: { cookie: sessionCookie },
      redirect: "manual",
    });
    assert.equal(qaqcResponse.status, 200, "qaqc API should accept a valid session cookie");
    const qaqcJson = await qaqcResponse.json();
    assert.equal(qaqcJson.verdict, "APPROVED", "qaqc payload should expose the smoke fixture verdict");
    assert.equal(qaqcJson.total.passed, 1, "qaqc payload should expose fixture totals");
  } finally {
    await stopServer(server);
  }

  console.log("knowledge-dashboard smoke checks passed");
}


run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
