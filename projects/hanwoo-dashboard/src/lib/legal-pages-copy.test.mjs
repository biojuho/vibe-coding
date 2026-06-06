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

test("legal pages expose stable support channels without personal contact details", () => {
	const privacySource = readSource("app/privacy/page.js");
	const termsSource = readSource("app/terms/page.js");
	const layoutSource = readSource("components/layout/LegalDocumentLayout.js");
	const returnLinkSource = readSource("components/layout/LegalReturnLink.js");
	const combinedSource = `${privacySource}\n${termsSource}`;

	assert.match(termsSource, /eyebrow="서비스 이용약관"/);
	assert.match(privacySource, /eyebrow="개인정보 보호 안내"/);
	assert.doesNotMatch(combinedSource, /Terms of Service|Privacy Policy/);

	assert.match(privacySource, /담당: Joolife 운영팀/);
	assert.match(privacySource, /이메일: joolife@joolife\.io\.kr/);
	assert.match(privacySource, /문의 채널: 서비스 운영 문의/);
	assert.match(termsSource, /문의 이메일: joolife@joolife\.io\.kr/);
	assert.match(termsSource, /웹사이트: joolife\.io\.kr/);
	assert.doesNotMatch(combinedSource, /010-\d{4}-\d{4}/);
	assert.doesNotMatch(combinedSource, /경기도 안양시/);
	assert.doesNotMatch(combinedSource, /공작부영아파트/);
	assert.doesNotMatch(combinedSource, /대표자: 박주호/);
	assert.doesNotMatch(combinedSource, /성명: 박주호/);
	assert.match(
		layoutSource,
		/function normalizeLegalDocumentLayoutOptions\(options\) \{/,
	);
	assert.match(
		layoutSource,
		/return options && typeof options === ["']object["'] && !Array\.isArray\(options\)\s*\?\s*options\s*:\s*\{\s*\}\s*;?/,
	);
	assert.match(
		layoutSource,
		/export default function LegalDocumentLayout\(options = \{\}\) \{/,
	);
	assert.match(
		layoutSource,
		/const \{ eyebrow, title, subtitle, lastUpdated, children \} =\s*normalizeLegalDocumentLayoutOptions\(options\);/,
	);
	assert.doesNotMatch(
		layoutSource,
		/export default function LegalDocumentLayout\(\{\s*eyebrow,/,
	);
	assert.match(layoutSource, /import \{ Suspense \} from ["']react["'];/);
	assert.match(
		layoutSource,
		/import LegalReturnLink, \{\s*LegalReturnLinkFallback,\s*\} from ["']@\/components\/layout\/LegalReturnLink["'];/,
	);
	assert.match(layoutSource, /<Suspense fallback=\{<LegalReturnLinkFallback \/>}/);
	assert.match(layoutSource, /<LegalReturnLink \/>/);
	assert.doesNotMatch(layoutSource, /href="\/"/);
	assert.doesNotMatch(layoutSource, /홈으로 돌아가기/);

	assert.match(returnLinkSource, /"use client";/);
	assert.match(
		returnLinkSource,
		/import \{ getSafeLoginRedirectTarget \} from ["']@\/lib\/login-redirect\.mjs["'];/,
	);
	assert.match(
		returnLinkSource,
		/Dashboard legal return must use document navigation so auth proxy redirect fragments are preserved\./,
	);
	assert.match(returnLinkSource, /import \{ useSearchParams \} from ["']next\/navigation["'];/);
	assert.match(
		returnLinkSource,
		/dashboard:\s*\{\s*href: "\/",[\s\S]*?label: "대시보드로 돌아가기"/,
	);
	assert.match(returnLinkSource, /requiresDocumentNavigation: true/);
	assert.match(
		returnLinkSource,
		/login:\s*\{\s*href: "\/login",\s*label: "로그인 화면으로 돌아가기"/,
	);
	assert.match(
		returnLinkSource,
		/function buildLoginReturnHref\(callbackTarget = ["']["']\) \{/,
	);
	assert.match(
		returnLinkSource,
		/params\.set\(["']callbackUrl["'], callbackTarget\);/,
	);
	assert.match(
		returnLinkSource,
		/return `\$\{LEGAL_RETURN_TARGETS\.login\.href\}\?\$\{params\.toString\(\)\}#login`;/,
	);
	assert.match(
		returnLinkSource,
		/function resolveLegalLoginReturnTarget\(searchParams, locationHref = ["']["']\) \{/,
	);
	assert.match(
		returnLinkSource,
		/const callbackUrl = searchParams\?\.get\(["']callbackUrl["']\);/,
	);
	assert.match(
		returnLinkSource,
		/loginUrl\.searchParams\.set\(["']callbackUrl["'], callbackUrl\);/,
	);
	assert.match(
		returnLinkSource,
		/const redirectTarget = getSafeLoginRedirectTarget\(loginUrl\.href\);/,
	);
	assert.match(returnLinkSource, /href: buildLoginReturnHref\(redirectTarget\),/);
	assert.match(returnLinkSource, /returnTo === "dashboard"/);
	assert.match(
		returnLinkSource,
		/function LegalReturnAnchor\(\{ href, label, requiresDocumentNavigation = false \}\) \{/,
	);
	assert.match(returnLinkSource, /if \(requiresDocumentNavigation\) \{/);
	assert.match(
		returnLinkSource,
		/<a[\s\S]*?href=\{href\}[\s\S]*?aria-label=\{label\}[\s\S]*?title=\{label\}[\s\S]*?className="clay-pressable/,
	);
	assert.match(returnLinkSource, /export function LegalReturnLinkFallback\(\)/);
	assert.match(returnLinkSource, /const searchParams = useSearchParams\(\);/);
	assert.match(
		returnLinkSource,
		/const locationHref = typeof window === ["']undefined["'] \? ["']["'] : window\.location\.href;/,
	);
	assert.match(
		returnLinkSource,
		/resolveLegalReturnTarget\(searchParams, locationHref\)/,
	);
	assert.match(
		returnLinkSource,
		/<ArrowLeft className="h-4 w-4" aria-hidden="true" \/>/,
	);
	assert.doesNotMatch(returnLinkSource, /홈으로 돌아가기/);
});
