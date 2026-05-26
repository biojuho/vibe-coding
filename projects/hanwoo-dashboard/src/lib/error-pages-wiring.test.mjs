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

test("not-found page is a server component with a route home and title metadata", () => {
	const source = readSource("app/not-found.js");

	assert.match(source, /export default function NotFound/);
	assert.doesNotMatch(source, /["']use client["']/);
	assert.match(source, /export const metadata/);
	assert.match(source, /href="\/"/);
	assert.match(
		source,
		/<Compass size=\{26\} strokeWidth=\{2\.2\} aria-hidden="true" \/>/,
	);
	assert.match(source, /Joolife 한우 운영/);
	assert.match(source, /페이지를 찾을 수 없어요/);
	assert.doesNotMatch(source, /Joolife Operations/);
});

test("route error boundary is a client component exposing retry and home actions", () => {
	const source = readSource("app/error.js");

	assert.match(source, /^["']use client["'];/);
	assert.match(
		source,
		/export default function RouteError\(\{ error, reset \}\)/,
	);
	assert.match(source, /onClick=\{\(\) => reset\(\)\}/);
	assert.match(source, /href="\/"/);
	assert.match(
		source,
		/<TriangleAlert size=\{26\} strokeWidth=\{2\.2\} aria-hidden="true" \/>/,
	);
	assert.match(source, /console\.error/);
	assert.match(source, /Joolife 한우 운영/);
	assert.doesNotMatch(source, /Joolife Operations/);
});

test("global error boundary renders its own html/body and a reset action", () => {
	const source = readSource("app/global-error.js");

	assert.match(source, /^["']use client["'];/);
	assert.match(
		source,
		/export default function GlobalError\(\{ error, reset \}\)/,
	);
	assert.match(source, /<html lang="ko">/);
	assert.match(source, /<body/);
	assert.match(source, /onClick=\{\(\) => reset\(\)\}/);
	assert.match(source, /Joolife 한우 운영/);
	assert.doesNotMatch(source, /Joolife Operations/);
});

test("login page operator eyebrow uses Korean product copy", () => {
	const source = readSource("app/login/page.js");

	assert.match(
		source,
		/<ShieldCheck size=\{26\} strokeWidth=\{2\.2\} aria-hidden="true" \/>/,
	);
	assert.match(source, /<EyeOff size=\{18\} aria-hidden="true" \/>/);
	assert.match(source, /<Eye size=\{18\} aria-hidden="true" \/>/);

	assert.match(source, /Joolife 한우 운영/);
	assert.doesNotMatch(source, /Joolife Operations/);
});

test("login page links authentication errors to both credential fields", () => {
	const source = readSource("app/login/page.js");

	assert.match(source, /const loginErrorId = ["']login-error-message["']/);
	assert.match(source, /aria-invalid=\{Boolean\(error\)\}/);
	assert.match(
		source,
		/aria-describedby=\{error \? loginErrorId : undefined\}/,
	);
	assert.match(
		source,
		/<div id=\{loginErrorId\} className="login-error" role="alert">/,
	);
});

test("login page recovers submit state when sign-in fails unexpectedly", () => {
	const source = readSource("app/login/page.js");

	assert.match(source, /import \{ useRef, useState \} from ["']react["']/);
	assert.match(source, /const submitInFlightRef = useRef\(false\)/);
	assert.match(source, /const loginSubmitLabel = isSubmitting/);
	assert.match(source, /아이디를 입력하면 로그인할 수 있습니다/);
	assert.match(source, /비밀번호를 입력하면 로그인할 수 있습니다/);
	assert.match(source, /한우 대시보드 열기/);
	assert.match(
		source,
		/if \(submitInFlightRef\.current \|\| !canSubmit\) return;/,
	);
	assert.match(source, /submitInFlightRef\.current = true;/);
	assert.match(source, /setIsSubmitting\(true\);/);
	assert.match(source, /try \{\s+const result = await signIn\(["']credentials["']/);
	assert.match(source, /\} catch \{\s+setError\(["']/);
	assert.match(
		source,
		/\} finally \{\s+submitInFlightRef\.current = false;\s+setIsSubmitting\(false\);/,
	);
	assert.match(
		source,
		/disabled=\{!canSubmit\}[\s\S]*?aria-busy=\{isSubmitting\}[\s\S]*?aria-label=\{loginSubmitLabel\}[\s\S]*?title=\{loginSubmitLabel\}/,
	);
});
