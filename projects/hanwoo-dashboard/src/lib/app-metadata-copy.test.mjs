import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");

function readProjectFile(relativePath) {
	return readFileSync(path.join(PROJECT_ROOT, relativePath), "utf8");
}

test("app metadata and PWA manifest use product-ready Korean copy", () => {
	const layoutSource = readProjectFile("src/app/layout.js");
	const manifest = JSON.parse(readProjectFile("public/manifest.json"));

	assert.match(layoutSource, /Joolife 한우 농장 관리/);
	assert.match(
		layoutSource,
		/한우 농장의 개체, 번식, 출하, 재고, 일정을 한곳에서 관리하는 운영 대시보드/,
	);
	assert.match(layoutSource, /Joolife 한우/);
	assert.doesNotMatch(layoutSource, /Joolife Dashboard/);
	assert.doesNotMatch(layoutSource, /Premium Hanwoo Farm Management System/);
	assert.match(layoutSource, /function normalizeRootLayoutOptions\(options\) \{/);
	assert.match(
		layoutSource,
		/return options && typeof options === ["']object["'] && !Array\.isArray\(options\)\s*\?\s*options\s*:\s*\{\s*\}\s*;?/,
	);
	assert.match(
		layoutSource,
		/export default function RootLayout\(options = \{\}\) \{/,
	);
	assert.match(
		layoutSource,
		/const \{ children \} = normalizeRootLayoutOptions\(options\);/,
	);
	assert.match(layoutSource, /data-scroll-behavior=["']smooth["']/);
	assert.doesNotMatch(
		layoutSource,
		/export default function RootLayout\(\{ children \}\)/,
	);

	assert.equal(manifest.name, "Joolife 한우 농장 관리");
	assert.equal(manifest.short_name, "Joolife 한우");
	assert.equal(
		manifest.description,
		"한우 농장의 개체, 번식, 출하, 재고, 일정을 한곳에서 관리하는 운영 대시보드",
	);
	assert.equal(manifest.id, "/");
	assert.equal(manifest.scope, "/");
	assert.equal(manifest.lang, "ko-KR");
});

test("proxy leaves public health and PWA assets outside auth redirects", () => {
	const proxySource = readProjectFile("src/proxy.js");

	assert.match(proxySource, /api\/health/);
	assert.match(proxySource, /manifest\.json/);
	assert.match(proxySource, /api\/auth/);
	assert.match(proxySource, /subscription\/fail/);
});

test("public-facing pages have distinct Korean page titles for SEO", () => {
	const loginLayout = readProjectFile("src/app/login/layout.js");
	const registerLayout = readProjectFile("src/app/register/layout.js");
	const termsSource = readProjectFile("src/app/terms/page.js");
	const privacySource = readProjectFile("src/app/privacy/page.js");

	assert.match(loginLayout, /로그인 · Joolife 한우/);
	assert.match(registerLayout, /회원가입 · Joolife 한우/);
	assert.match(registerLayout, /14일 무료/);
	assert.match(termsSource, /이용약관 · Joolife 한우/);
	assert.match(privacySource, /개인정보처리방침 · Joolife 한우/);

	// Layout files must pass children through so they don't break rendering
	assert.match(loginLayout, /export default function LoginLayout/);
	assert.match(registerLayout, /export default function RegisterLayout/);
});

test("root layout includes skip-to-main-content link for keyboard accessibility", () => {
	const layoutSource = readProjectFile("src/app/layout.js");
	const cssSource = readProjectFile("src/app/globals.css");

	// Skip link targets main-content ID
	assert.match(layoutSource, /href="#main-content"/);
	assert.match(layoutSource, /className="skip-to-main"/);
	assert.match(layoutSource, /본문으로 건너뛰기/);

	// CSS hides and reveals on focus (WCAG 2.4.1)
	assert.match(cssSource, /\.skip-to-main\s*\{/);
	assert.match(cssSource, /\.skip-to-main:focus\s*\{/);
	assert.match(cssSource, /top:\s*0/);

	// Login page exposes id="main-content" for the skip link target
	const loginSource = readProjectFile("src/app/login/page.js");
	assert.match(loginSource, /id="main-content"/);
});

test("committed service worker fallback stays build-agnostic", () => {
	const serviceWorkerSource = readProjectFile("public/sw.js");

	assert.match(serviceWorkerSource, /NEXT_ENABLE_PWA=1/);
	assert.match(serviceWorkerSource, /self\.skipWaiting\(\)/);
	assert.match(serviceWorkerSource, /self\.clients\.claim\(\)/);
	assert.match(serviceWorkerSource, /CACHE_PREFIXES = \["serwist-", "workbox-"\]/);
	assert.doesNotMatch(serviceWorkerSource, /\/_next\/static\//);
	assert.doesNotMatch(serviceWorkerSource, /precacheAndRoute/);
	assert.doesNotMatch(serviceWorkerSource, /__SW_MANIFEST|__WB_MANIFEST/);
	assert.doesNotMatch(serviceWorkerSource, /revision:\s*["'][a-f0-9]{16,}["']/);
});
