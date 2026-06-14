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

test("auth guard normalizes malformed options before destructuring", () => {
	const source = readSource("lib/auth-guard.js");

	assert.match(
		source,
		/function normalizeObject\(value\) \{\s+return value && typeof value === "object" && !Array\.isArray\(value\)\s+\? value\s+:\s+\{\};\s+\}/,
	);
	assert.match(
		source,
		/const \{ redirectToLogin = false \} = normalizeObject\(options\);/,
	);
	assert.doesNotMatch(
		source,
		/const \{ redirectToLogin = false \} = options;/,
	);
});

test("auth guard exports AdminAuthorizationError with Korean default message", () => {
	const source = readSource("lib/auth-guard.js");

	assert.match(source, /export class AdminAuthorizationError extends Error \{/);
	assert.match(source, /관리자 권한이 필요합니다\./);
	assert.match(source, /this\.name = ["']AdminAuthorizationError["'];/);
});

test("auth guard normalizeAdminOptions rejects arrays and primitives", () => {
	const source = readSource("lib/auth-guard.js");

	assert.match(source, /function normalizeAdminOptions\(value\) \{/);
	assert.match(
		source,
		/value && typeof value === ["']object["'] && !Array\.isArray\(value\) \? value : \{\}/,
	);
});

test("auth guard requireAdminSession uses ADMIN_USERNAMES env var in production", () => {
	const source = readSource("lib/auth-guard.js");

	assert.match(source, /export async function requireAdminSession\(options = \{\}\) \{/);
	assert.match(source, /const isDev = process\.env\.NODE_ENV === ["']development["'];/);
	assert.match(source, /process\.env\.ADMIN_USERNAMES/);
	assert.match(source, /\.split\(","\)[\s\S]*?\.map[\s\S]*?\.filter\(Boolean\)/);
	assert.match(source, /if \(!adminUsernames\.includes\(username\)\) \{/);
	assert.match(source, /throw new AdminAuthorizationError\(\);/);
	assert.match(source, /\{ redirectToLogin = false, redirectToHome = false \}/);
});

test("admin routes use requireAdminSession not requireAuthenticatedSession", () => {
	const diagnosticsSource = readSource("app/admin/diagnostics/page.js");
	const systemActionsSource = readSource("lib/actions/system.js");

	assert.match(diagnosticsSource, /requireAdminSession/);
	assert.doesNotMatch(diagnosticsSource, /requireAuthenticatedSession\(/);
	assert.match(systemActionsSource, /requireAdminSession/);
	assert.match(systemActionsSource, /requireAuthenticatedSession/);
});
