import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";


const PORT = process.env.SMOKE_PORT ?? "3101";
const HOST = "127.0.0.1";
const BASE_URL = `http://${HOST}:${PORT}`;
const REDIRECT_STATUSES = new Set([302, 303, 307, 308]);


function createSmokeEnv() {
  return {
    ...process.env,
    PORT,
    AUTH_SECRET: process.env.AUTH_SECRET ?? "smoke-auth-secret",
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET ?? process.env.AUTH_SECRET ?? "smoke-auth-secret",
    AUTH_TRUST_HOST: process.env.AUTH_TRUST_HOST ?? "true",
    AUTH_URL: process.env.AUTH_URL ?? BASE_URL,
    NEXTAUTH_URL: process.env.NEXTAUTH_URL ?? BASE_URL,
    DATABASE_URL:
      process.env.DATABASE_URL ?? "postgresql://smoke:smoke@127.0.0.1:5432/hanwoo_smoke?sslmode=disable",
    TOSS_PAYMENTS_SECRET_KEY: process.env.TOSS_PAYMENTS_SECRET_KEY ?? "smoke-secret",
    NEXT_PUBLIC_TOSS_PAYMENTS_CLIENT_KEY:
      process.env.NEXT_PUBLIC_TOSS_PAYMENTS_CLIENT_KEY ?? "test_ck_smoke_client_key",
  };
}


function startServer() {
  const env = createSmokeEnv();

  const nextBin = path.join(process.cwd(), "node_modules", "next", "dist", "bin", "next");
  const command = process.execPath;
  const args = [nextBin, "start", "--port", PORT, "--hostname", HOST];

  const child = spawn(command, args, {
    cwd: process.cwd(),
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });

  child.stdout?.on("data", (chunk) => process.stdout.write(`[hanwoo-smoke] ${chunk}`));
  child.stderr?.on("data", (chunk) => process.stderr.write(`[hanwoo-smoke] ${chunk}`));
  return child;
}


async function runNextCommand(args, label) {
  const nextBin = path.join(process.cwd(), "node_modules", "next", "dist", "bin", "next");
  const child = spawn(process.execPath, [nextBin, ...args], {
    cwd: process.cwd(),
    env: createSmokeEnv(),
    stdio: ["ignore", "pipe", "pipe"],
  });

  child.stdout?.on("data", (chunk) => process.stdout.write(`[hanwoo-smoke:${label}] ${chunk}`));
  child.stderr?.on("data", (chunk) => process.stderr.write(`[hanwoo-smoke:${label}] ${chunk}`));

  const exitCode = await new Promise((resolve, reject) => {
    child.once("error", reject);
    child.once("exit", resolve);
  });

  if (exitCode !== 0) {
    throw new Error(`${label} failed with exit code ${exitCode}`);
  }
}


async function ensureProductionBuild() {
  const buildIdPath = path.join(process.cwd(), ".next", "BUILD_ID");
  if (existsSync(buildIdPath)) {
    return;
  }

  console.log("[hanwoo-smoke] BUILD_ID missing; creating webpack production build for smoke");
  await runNextCommand(["build", "--webpack"], "build");
}


async function waitForServer(pathname = "/login", timeoutMs = 45000) {
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


async function expectRedirect(pathname) {
  const response = await fetch(`${BASE_URL}${pathname}`, { redirect: "manual" });
  assert(REDIRECT_STATUSES.has(response.status), `${pathname} should redirect, got ${response.status}`);

  const location = response.headers.get("location") ?? "";
  assert(location.includes("/login"), `${pathname} should redirect to /login, got ${location}`);
}


async function expectJson(pathname, options, expectedStatus) {
  const response = await fetch(`${BASE_URL}${pathname}`, options);
  assert.equal(response.status, expectedStatus, `${pathname} should return ${expectedStatus}`);
  return response.json();
}


async function run() {
  await ensureProductionBuild();
  const server = startServer();

  try {
    await waitForServer();

    const loginResponse = await fetch(`${BASE_URL}/login`, { redirect: "manual" });
    assert.equal(loginResponse.status, 200, "/login should load");
    const loginHtml = await loginResponse.text();
    assert(loginHtml.includes('type="password"'), "login page should render a password field");

    await expectRedirect("/");
    await expectRedirect("/subscription");
    await expectRedirect("/admin/diagnostics");

    const prepareBody = {
      amount: 9900,
      customerKey: "user_smoke-user",
      orderName: "Smoke subscription",
      customerName: "Smoke User",
    };
    const prepareJson = await expectJson(
      "/api/payments/prepare",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(prepareBody),
      },
      401,
    );
    assert.equal(prepareJson.success, false, "prepare route should reject unauthenticated callers");

    const confirmJson = await expectJson(
      "/api/payments/confirm",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          paymentKey: "smoke-payment",
          orderId: "sub_user_smoke-user_1234567890",
          amount: 9900,
        }),
      },
      401,
    );
    assert.equal(confirmJson.success, false, "confirm route should reject unauthenticated callers");

    const summaryJson = await expectJson("/api/dashboard/summary", { method: "GET" }, 401);
    assert.equal(summaryJson.success, false, "summary route should reject unauthenticated callers");

    const cattleJson = await expectJson("/api/dashboard/cattle?limit=5", { method: "GET" }, 401);
    assert.equal(cattleJson.success, false, "cattle route should reject unauthenticated callers");

    const salesJson = await expectJson("/api/dashboard/sales?limit=5", { method: "GET" }, 401);
    assert.equal(salesJson.success, false, "sales route should reject unauthenticated callers");
  } finally {
    await stopServer(server);
  }

  console.log("hanwoo-dashboard smoke checks passed");
}


run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
