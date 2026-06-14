import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const API_ROOT = path.join(PROJECT_ROOT, "src", "app", "api");
const API_SPEC = readFileSync(path.join(PROJECT_ROOT, "API_SPEC.md"), "utf8");

const PUBLIC_ROUTES = new Set([
	"/api/auth/[...nextauth]",
	"/api/auth/register",
	"/api/health",
]);

function escapeRegExp(value) {
	return value.replace(/[\\^$.*+?()[\]{}|]/g, "\\$&");
}

function listRouteFiles(dir = API_ROOT) {
	const entries = readdirSync(dir, { withFileTypes: true });
	return entries.flatMap((entry) => {
		const fullPath = path.join(dir, entry.name);
		if (entry.isDirectory()) {
			return listRouteFiles(fullPath);
		}
		return entry.isFile() && entry.name === "route.js" ? [fullPath] : [];
	});
}

function routePathForFile(filePath) {
	const relative = path
		.relative(API_ROOT, path.dirname(filePath))
		.split(path.sep)
		.filter(Boolean)
		.join("/");
	return `/api/${relative}`;
}

function getSpecEntry(routePath) {
	const bulletLine = API_SPEC.split(/\r?\n/).find(
		(line) => line.trim().startsWith("-") && line.includes(routePath),
	);
	if (bulletLine) {
		return bulletLine;
	}

	const start = API_SPEC.indexOf(routePath);
	assert.notEqual(start, -1, `${routePath} must be documented in API_SPEC.md`);

	const nextHeading = API_SPEC.indexOf("\n## ", start + routePath.length);
	return nextHeading === -1
		? API_SPEC.slice(start)
		: API_SPEC.slice(start, nextHeading);
}

test("API_SPEC documents every App Router API route", () => {
	const routeFiles = listRouteFiles();
	const routePaths = routeFiles.map(routePathForFile).sort();

	assert.deepEqual(routePaths, [
		"/api/ai/chat",
		"/api/ai/insight",
		"/api/auth/[...nextauth]",
		"/api/auth/change-password",
		"/api/auth/register",
		"/api/dashboard/cattle",
		"/api/dashboard/sales",
		"/api/dashboard/summary",
		"/api/health",
		"/api/payments/confirm",
		"/api/payments/prepare",
	]);

	for (const routePath of routePaths) {
		assert.match(
			API_SPEC,
			new RegExp(escapeRegExp(routePath)),
			`${routePath} must be documented in API_SPEC.md`,
		);
	}
});

test("API routes either use the auth guard or are documented public endpoints", () => {
	for (const filePath of listRouteFiles()) {
		const routePath = routePathForFile(filePath);
		const source = readFileSync(filePath, "utf8");
		const hasAuthGuard = source.includes("requireAuthenticatedSession");

		if (PUBLIC_ROUTES.has(routePath)) {
			const specEntry = getSpecEntry(routePath);
			assert.match(specEntry, /public/i);
			continue;
		}

		const specEntry = getSpecEntry(routePath);
		assert.equal(
			hasAuthGuard,
			true,
			`${routePath} must call or inject requireAuthenticatedSession()`,
		);
		assert.match(
			specEntry,
			/authenticated/i,
			`${routePath} must be documented as authenticated`,
		);
	}
});

test("public API endpoints are intentionally reachable without dashboard auth", () => {
	for (const routePath of PUBLIC_ROUTES) {
		assert.match(getSpecEntry(routePath), /public/i);
	}

	const authRoute = path.join(API_ROOT, "auth", "[...nextauth]", "route.js");
	assert.equal(existsSync(authRoute), true);
	assert.match(readFileSync(authRoute, "utf8"), /export const \{ GET, POST \} = handlers;/);
});
