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

test("root layout has openGraph and twitter social share images", () => {
	const layoutSource = readProjectFile("src/app/layout.js");

	// Social share images make link previews usable (Kakao, Twitter, etc.)
	assert.match(layoutSource, /openGraph:[\s\S]{0,200}images:/);
	assert.match(layoutSource, /icon-512x512\.png/);
	assert.match(layoutSource, /twitter:[\s\S]{0,200}images:/);
});

test("root layout has metadataBase so OG image URLs resolve to absolute paths", () => {
	const layoutSource = readProjectFile("src/app/layout.js");

	// Without metadataBase, OG image paths like /icon-512x512.png stay relative
	// and Kakao/Twitter crawlers reject them — they require absolute URLs
	assert.match(layoutSource, /metadataBase:/);
	assert.match(layoutSource, /new URL\(/);
	assert.match(layoutSource, /hanwoo\.joolife\.com/);
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

test("home page and admin diagnostics layout have metadata", () => {
	const homeSource = readProjectFile("src/app/page.js");
	const adminLayoutSource = readProjectFile("src/app/admin/diagnostics/layout.js");

	assert.match(homeSource, /export const metadata = \{/);
	assert.match(homeSource, /대시보드 · Joolife 한우/);
	assert.match(adminLayoutSource, /export const metadata = \{/);
	assert.match(adminLayoutSource, /시스템 진단 · Joolife 한우/);
	// Admin routes must be excluded from search engine indexing
	assert.match(adminLayoutSource, /robots:.*noindex/);
});

test("Providers wires SessionProvider and FeedbackProvider around children", () => {
	const source = readProjectFile("src/components/Providers.js");

	assert.match(source, /"use client";/);
	assert.match(source, /import \{ SessionProvider \} from ["']next-auth\/react["']/);
	assert.match(source, /import \{ FeedbackProvider \}/);
	assert.match(source, /<SessionProvider>/);
	assert.match(source, /<FeedbackProvider>/);
	assert.match(source, /\{children\}/);
	assert.match(source, /export default function Providers/);
});

test("AIChatWidget non-premium close button has aria-label for screen readers", () => {
	const source = readProjectFile("src/components/widgets/AIChatWidget.js");

	// The upsell panel's "닫기" button must have a label distinguishing it from the subscription CTA
	assert.match(source, /aria-label="AI 농장 비서 닫기"/);
	// Main header close button also has label (verify at least one title)
	assert.match(source, /title="AI 농장 비서 닫기"/);
});

test("root layout has noscript fallback for users with JavaScript disabled", () => {
	const layoutSource = readProjectFile("src/app/layout.js");

	assert.match(layoutSource, /<noscript>/);
	assert.match(layoutSource, /JavaScript가 필요합니다/);
	assert.match(layoutSource, /<\/noscript>/);
});

test("NotificationModal has Tab focus trap matching other dialog components", () => {
	const source = readProjectFile("src/components/ui/NotificationModal.js");

	assert.match(source, /event\.key === ["']Tab["']/);
	assert.match(source, /querySelectorAll[\s\S]{0,200}button:not\(\[disabled\]\)/);
	assert.match(source, /document\.activeElement === first/);
	assert.match(source, /document\.activeElement === last/);
	assert.match(source, /event\.shiftKey/);
});

test("globals.css respects prefers-reduced-motion for accessibility", () => {
	const cssSource = readProjectFile("src/app/globals.css");

	assert.match(cssSource, /@media \(prefers-reduced-motion: reduce\)/);
	assert.match(cssSource, /animation-duration: 0\.01ms !important/);
	assert.match(cssSource, /transition-duration: 0\.01ms !important/);
	assert.match(cssSource, /scroll-behavior: auto !important/);
});

test("security headers allow geolocation for weather widget but block microphone", () => {
	const configSource = readProjectFile("next.config.mjs");

	// camera=(self) allows ear-tag scanner; geolocation=(self) allows weather auto-detect
	assert.match(configSource, /camera=\(self\)/);
	assert.match(configSource, /geolocation=\(self\)/);
	// microphone must stay blocked — no feature uses it
	assert.match(configSource, /microphone=\(\)/);
	// geolocation=() (blocked) must not appear — would break weather widget
	assert.doesNotMatch(configSource, /geolocation=\(\)/);
});

test("next.config security headers include clickjacking, MIME-sniff, HSTS, and referrer guards", () => {
	const configSource = readProjectFile("next.config.mjs");

	// Deny all framing — app handles payments and must not be embedded
	assert.match(configSource, /X-Frame-Options.*DENY|DENY.*X-Frame-Options/);
	// Prevent MIME-type sniffing attacks
	assert.match(configSource, /X-Content-Type-Options.*nosniff|nosniff.*X-Content-Type-Options/);
	// Enforce HTTPS for 2 years including subdomains
	assert.match(configSource, /Strict-Transport-Security/);
	assert.match(configSource, /max-age=63072000/);
	assert.match(configSource, /includeSubDomains/);
	// Limit referrer data sent to external origins
	assert.match(configSource, /Referrer-Policy.*strict-origin-when-cross-origin/);
	// All headers must apply to every route
	assert.match(configSource, /source.*\(.*\.\*\).*headers.*SECURITY_HEADERS/s);
});

test("globals.css has print styles that hide chrome and preserve content", () => {
	const cssSource = readProjectFile("src/app/globals.css");

	// Navigation and interactive chrome must not print
	assert.match(cssSource, /@media print/);
	assert.match(cssSource, /\.tab-bar[\s\S]{0,100}display: none !important/);
	assert.match(cssSource, /\.skip-to-main[\s\S]{0,100}display: none !important/);
	assert.match(cssSource, /\.quick-action-panel[\s\S]{0,100}display: none !important/);

	// Content surfaces reset to white for print
	assert.match(cssSource, /body\s*\{[\s\S]{0,100}background: white !important/);
	assert.match(cssSource, /break-inside: avoid/);
});

test("root layout includes JSON-LD SoftwareApplication schema for SEO rich results", () => {
	const layoutSource = readProjectFile("src/app/layout.js");

	// JSON-LD structured data enables Google rich results for SaaS apps
	assert.match(layoutSource, /application\/ld\+json/);
	assert.match(layoutSource, /SoftwareApplication/);
	assert.match(layoutSource, /BusinessApplication/);
	assert.match(layoutSource, /hanwoo\.joolife\.com/);
	assert.match(layoutSource, /dangerouslySetInnerHTML/);
	assert.match(layoutSource, /SCHEMA_ORG_APP/);
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

test("private pages set robots=noindex to prevent search engine indexing", () => {
	// Authentication-required pages must be noindex to avoid leaking URLs or descriptions
	const privatePages = [
		{ path: "src/app/page.js", label: "dashboard" },
		{ path: "src/app/login/layout.js", label: "login" },
		{ path: "src/app/register/layout.js", label: "register" },
		{ path: "src/app/subscription/page.js", label: "subscription" },
		{ path: "src/app/subscription/success/layout.js", label: "payment-success" },
		{ path: "src/app/subscription/fail/layout.js", label: "payment-fail" },
	];
	for (const { path: p, label } of privatePages) {
		const source = readProjectFile(p);
		assert.match(source, /robots: \{ index: false/, `${label} page missing robots:noindex`);
	}
});

test("sitemap only includes publicly indexable pages (not login/register/dashboard)", () => {
	const source = readProjectFile("src/app/sitemap.js");
	assert.match(source, /\/terms/);
	assert.match(source, /\/privacy/);
	assert.doesNotMatch(source, /\/login/);
	assert.doesNotMatch(source, /\/register/);
	assert.doesNotMatch(source, /\/subscription/);
});

test("dynamic robots.js is the single source of truth for crawl policy", () => {
	const source = readProjectFile("src/app/robots.js");
	assert.match(source, /\/api\//);
	assert.match(source, /\/admin\//);
	assert.match(source, /sitemap\.xml/);
	// robots.js must define the rules and sitemap pointer
	assert.match(source, /userAgent/);
	assert.match(source, /disallow/i);
});
