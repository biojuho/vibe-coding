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
	assert.match(
		source,
		/<Link[\s\S]*?href="\/"[\s\S]*?aria-label="대시보드로 돌아가기"[\s\S]*?title="대시보드로 돌아가기"[\s\S]*?className="login-submit status-submit-link"/,
	);
	assert.match(
		source,
		/<Compass size=\{26\} strokeWidth=\{2\.2\} aria-hidden="true" \/>/,
	);
	assert.match(source, /Joolife 한우 운영/);
	assert.match(source, /페이지를 찾을 수 없습니다/);
	assert.match(source, /주소가 바뀌었거나 삭제된 화면일 수 있습니다/);
	assert.match(source, /사육, 재고, 출하 업무를 이어서 관리해 주세요/);
	assert.doesNotMatch(source, /페이지를 찾을 수 없어요/);
	assert.doesNotMatch(source, /화면일 수 있어요/);
	assert.doesNotMatch(source, /사육, 재고, 출하 업무를 이어서 관리하세요/);
	assert.doesNotMatch(source, /Joolife Operations/);
});

test("route error boundary is a client component exposing retry and home actions", () => {
	const source = readSource("app/error.js");

	assert.match(source, /^["']use client["'];/);
	assert.match(
		source,
		/export default function RouteError\(\{ error, reset \}\)/,
	);
	assert.match(source, /const resetButtonLabel = ["']화면 다시 불러오기["']/);
	assert.match(
		source,
		/onClick=\{\(\) => reset\(\)\}[\s\S]*?aria-label=\{resetButtonLabel\}[\s\S]*?title=\{resetButtonLabel\}/,
	);
	assert.match(
		source,
		/<Link[\s\S]*?href="\/"[\s\S]*?aria-label="대시보드로 돌아가기"[\s\S]*?title="대시보드로 돌아가기"[\s\S]*?className="status-link"/,
	);
	assert.match(
		source,
		/<TriangleAlert size=\{26\} strokeWidth=\{2\.2\} aria-hidden="true" \/>/,
	);
	assert.match(source, /console\.error/);
	assert.match(source, /Joolife 한우 운영/);
	assert.match(source, /잠시 문제가 발생했습니다/);
	assert.match(source, /화면을 불러오는 중 오류가 발생했습니다/);
	assert.match(source, /대시보드로 돌아가 주세요/);
	assert.doesNotMatch(source, /잠시 문제가 생겼어요/);
	assert.doesNotMatch(source, /오류가 발생했어요/);
	assert.doesNotMatch(source, /대시보드로 돌아가세요/);
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
	assert.match(source, /const resetButtonLabel = ["']앱 다시 불러오기["']/);
	assert.match(
		source,
		/onClick=\{\(\) => reset\(\)\}[\s\S]*?aria-label=\{resetButtonLabel\}[\s\S]*?title=\{resetButtonLabel\}/,
	);
	assert.match(source, /Joolife 한우 운영/);
	assert.doesNotMatch(source, /Joolife Operations/);
});

test("dashboard page wraps client runtime failures with the premium error boundary", () => {
	const source = readSource("app/page.js");

	assert.match(
		source,
		/import ErrorBoundary from ["']@\/components\/ErrorBoundary["'];/,
	);
	assert.match(
		source,
		/<ErrorBoundary>\s*<DashboardClient[\s\S]*?\/>\s*<\/ErrorBoundary>/,
	);
});

test("dashboard error boundary exposes a labeled non-submit recovery action", () => {
	const source = readSource("components/ErrorBoundary.js");

	assert.match(
		source,
		/const resetButtonLabel = ["']대시보드 새로고침 및 복구 시도["']/,
	);
	assert.match(source, /화면 표시 중 일시적인 오류가 발생했습니다/);
	assert.match(source, /화면 표시 정보가 올바르지 않거나 처리 중/);
	assert.doesNotMatch(source, /화면 렌더링에 일시적인 에러가 발생했습니다/);
	assert.doesNotMatch(source, /데이터 형식이 올바르지 않거나 렌더링 도중/);
	assert.match(
		source,
		/<AlertTriangle[\s\S]*?aria-hidden="true"[\s\S]*?\/>/,
	);
	assert.match(
		source,
		/<PremiumButton[\s\S]*?type="button"[\s\S]*?onClick=\{this\.handleReset\}[\s\S]*?aria-label=\{resetButtonLabel\}[\s\S]*?title=\{resetButtonLabel\}/,
	);
	assert.match(source, /try \{\s+window\.location\.reload\(\);/);
	assert.match(
		source,
		/catch \(resetError\) \{\s+console\.error\(["']\[ErrorBoundary\] Failed to reload:/,
	);
	assert.match(
		source,
		/this\.setState\(\{ hasError: true, error: resetError \}\);/,
	);
	assert.match(source, /\{resetButtonLabel\}/);
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
	assert.match(source, /오늘의 사육, 재고, 출하 업무를 이어서 관리해 주세요/);
	assert.doesNotMatch(source, /오늘의 사육, 재고, 출하 업무를 이어서 관리하세요/);
	assert.match(source, /데모 로그인 정보/);
	assert.match(source, /<span aria-hidden="true">💡<\/span>/);
	assert.match(source, /아이디: <code/);
	assert.match(source, /비밀번호: <code/);
	assert.doesNotMatch(source, /Joolife Operations/);
	assert.doesNotMatch(source, /Demo Accounts/);
	assert.doesNotMatch(source, />ID:/);
	assert.doesNotMatch(source, />PW:/);
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

test("login password visibility toggle exposes matching accessible and title copy", () => {
	const source = readSource("app/login/page.js");

	assert.match(
		source,
		/const passwordToggleLabel = showPassword \? "비밀번호 숨기기" : "비밀번호 보기"/,
	);
	assert.match(
		source,
		/<button[\s\S]*?className="login-password-toggle"[\s\S]*?aria-label=\{passwordToggleLabel\}[\s\S]*?title=\{passwordToggleLabel\}/,
	);
	assert.match(source, /<EyeOff size=\{18\} aria-hidden="true" \/>/);
	assert.match(source, /<Eye size=\{18\} aria-hidden="true" \/>/);
});

test("login page recovers submit state when sign-in fails unexpectedly", () => {
	const source = readSource("app/login/page.js");

	assert.match(source, /import \{ useRef, useState \} from ["']react["']/);
	assert.match(
		source,
		/const LOGIN_NAVIGATION_ERROR_MESSAGE =\s+["']로그인은 완료됐지만 대시보드로 이동하지 못했습니다\. 새로고침 후 다시 시도해 주세요\.["'];/,
	);
	assert.match(source, /const submitInFlightRef = useRef\(false\)/);
	assert.match(source, /const loginSubmitLabel = isSubmitting/);
	assert.match(source, /아이디를 입력하면 로그인할 수 있습니다/);
	assert.match(source, /비밀번호를 입력하면 로그인할 수 있습니다/);
	assert.match(source, /한우 대시보드 열기/);
	assert.match(source, /\{isSubmitting \? "로그인 확인 중\.\.\." : "대시보드 열기"\}/);
	assert.doesNotMatch(source, /\{isSubmitting \? "확인 중\.\.\." : "대시보드 열기"\}/);
	assert.match(
		source,
		/if \(submitInFlightRef\.current \|\| !canSubmit\) return;/,
	);
	assert.match(source, /submitInFlightRef\.current = true;/);
	assert.match(source, /setIsSubmitting\(true\);/);
	assert.match(source, /try \{\s+const result = await signIn\(["']credentials["']/);
	assert.match(
		source,
		/try \{\s+router\.push\(["']\/["']\);\s+router\.refresh\(\);\s+\} catch \(navigationError\) \{/,
	);
	assert.match(
		source,
		/console\.error\(["']Login dashboard navigation failed:/,
	);
	assert.match(source, /setError\(LOGIN_NAVIGATION_ERROR_MESSAGE\);/);
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
