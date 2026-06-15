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

test("LoginPage buildLoginLegalDocumentHref rejects non-path inputs with /login fallback", () => {
	const source = readSource("app/login/page.js");
	assert.match(
		source,
		/function buildLoginLegalDocumentHref\(pathname, redirectTarget = ""\) \{/,
	);
	assert.match(source, /!pathname\.startsWith\("\/"\)/);
	assert.match(source, /pathname\.startsWith\("\/\/"\)/);
	assert.match(source, /return "\/login";/);
});

test("LoginPage buildLoginLegalDocumentHref appends returnTo+callbackUrl when redirectTarget is non-empty", () => {
	const source = readSource("app/login/page.js");
	assert.match(source, /params\.set\("returnTo", "login"\)/);
	assert.match(source, /params\.set\("callbackUrl", redirectTarget\)/);
	assert.match(source, /return `\$\{pathname\}\?\$\{params\.toString\(\)\}`/);
});

test("LoginPage canSubmit gate requires both username and password with no in-flight", () => {
	const source = readSource("app/login/page.js");
	assert.match(
		source,
		/username\.trim\(\)\.length > 0 && password\.length > 0 && !isSubmitting/,
	);
	assert.match(source, /disabled=\{!canSubmit\}/);
});

test("LoginPage loginSubmitLabel provides context-aware accessibility label", () => {
	const source = readSource("app/login/page.js");
	assert.match(source, /로그인 확인 중/);
	assert.match(source, /아이디를 입력하면 로그인할 수 있습니다/);
	assert.match(source, /비밀번호를 입력하면 로그인할 수 있습니다/);
	assert.match(source, /한우 대시보드 열기/);
	assert.match(source, /aria-label=\{loginSubmitLabel\}/);
	assert.match(source, /title=\{loginSubmitLabel\}/);
});

test("LoginPage handleSubmit prevents double-submit via submitInFlightRef guard", () => {
	const source = readSource("app/login/page.js");
	assert.match(source, /submitInFlightRef\.current = true;/);
	assert.match(source, /submitInFlightRef\.current = false;/);
	assert.match(
		source,
		/if \(submitInFlightRef\.current \|\| !canSubmit\) return;/,
	);
});

test("LoginPage password toggle button has accessible labels", () => {
	const source = readSource("app/login/page.js");
	assert.match(source, /비밀번호 숨기기/);
	assert.match(source, /비밀번호 보기/);
	assert.match(source, /passwordToggleLabel/);
	assert.match(source, /aria-label=\{passwordToggleLabel\}/);
	assert.match(source, /title=\{passwordToggleLabel\}/);
});

test("LoginPage error message uses aria-live=polite for screen reader accessibility", () => {
	const source = readSource("app/login/page.js");
	assert.match(source, /loginErrorId/);
	assert.match(source, /role="alert"/);
	assert.match(source, /아이디 또는 비밀번호를 다시 확인해 주세요\./);
});

test("LoginPage shows registration success message on ?registered=1 param", () => {
	const source = readSource("app/login/page.js");
	assert.match(source, /params\.get\("registered"\) === "1"/);
	assert.match(source, /registrationSuccess/);
	assert.match(source, /setRegistrationSuccess\(true\)/);
});

test("LoginPage logs sign-in error to console.error before showing user message", () => {
	const source = readSource("app/login/page.js");
	assert.match(
		source,
		/console\.error\(["']LoginPage: sign-in failed["'], err\)/,
	);
	assert.match(source, /catch \(err\)/);
});
