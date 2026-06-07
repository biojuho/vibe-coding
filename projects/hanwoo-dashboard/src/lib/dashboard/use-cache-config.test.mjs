import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

// Resolve project root from this file's location:
// src/lib/dashboard/use-cache-config.test.mjs -> project root (3 levels up)
const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "../../..");

// ============================================================
// A-3: use cache configuration & integration smoke tests
//
// These are static analysis tests that verify wiring by reading
// source files — they do NOT require the Next.js runtime.
// ============================================================

describe("use cache — configuration", () => {
	it("next.config.mjs enables cacheComponents: true", () => {
		const configContent = readFileSync(
			resolve(ROOT, "next.config.mjs"),
			"utf-8",
		);
		assert.ok(
			configContent.includes("cacheComponents: true"),
			"cacheComponents must be enabled in next.config.mjs",
		);
	});

	it("next.config.mjs allows 127.0.0.1 dev browser QA origin", () => {
		const configContent = readFileSync(
			resolve(ROOT, "next.config.mjs"),
			"utf-8",
		);
		assert.match(
			configContent,
			/allowedDevOrigins:\s*\[\s*["']127\.0\.0\.1["']\s*\]/,
			"Next dev server should accept Playwright QA sessions opened through 127.0.0.1",
		);
	});

	it("next.config.mjs keeps the dev indicator away from mobile tab controls", () => {
		const configContent = readFileSync(
			resolve(ROOT, "next.config.mjs"),
			"utf-8",
		);
		assert.match(
			configContent,
			/devIndicators:\s*\{\s*position:\s*["']top-right["']\s*,?\s*\}/,
			"Next dev indicator should not sit on top of the fixed mobile tab bar during browser QA",
		);
	});
});

describe("use cache — cached-queries module", () => {
	it('cached-queries.js declares "use cache" directive', () => {
		const content = readFileSync(
			resolve(ROOT, "src/lib/dashboard/cached-queries.js"),
			"utf-8",
		);
		assert.ok(
			/^['"]use cache['"]/.test(content.trimStart()),
			'cached-queries.js must start with "use cache" directive',
		);
	});

	it("declares getCachedDashboardSummary function", () => {
		const content = readFileSync(
			resolve(ROOT, "src/lib/dashboard/cached-queries.js"),
			"utf-8",
		);
		assert.ok(
			content.includes("async function getCachedDashboardSummary"),
			"must export getCachedDashboardSummary",
		);
	});

	it("declares getCachedCattleList function", () => {
		const content = readFileSync(
			resolve(ROOT, "src/lib/dashboard/cached-queries.js"),
			"utf-8",
		);
		assert.ok(
			content.includes("async function getCachedCattleList"),
			"must export getCachedCattleList",
		);
	});

	it("declares getCachedSalesList function", () => {
		const content = readFileSync(
			resolve(ROOT, "src/lib/dashboard/cached-queries.js"),
			"utf-8",
		);
		assert.ok(
			content.includes("async function getCachedSalesList"),
			"must export getCachedSalesList",
		);
	});

	it("uses cacheTag for invalidation targeting", () => {
		const content = readFileSync(
			resolve(ROOT, "src/lib/dashboard/cached-queries.js"),
			"utf-8",
		);
		assert.ok(
			/cacheTag\(\s*['"]dashboard-summary['"]\s*\)/.test(content),
			"must tag dashboard-summary",
		);
		assert.ok(
			/cacheTag\(\s*['"]cattle-list['"]\s*\)/.test(content),
			"must tag cattle-list",
		);
		assert.ok(
			/cacheTag\(\s*['"]sales-list['"]\s*\)/.test(content),
			"must tag sales-list",
		);
	});
});

describe("use cache — revalidateTag integration", () => {
	it("_helpers.js imports revalidateTag from next/cache", () => {
		const content = readFileSync(
			resolve(ROOT, "src/lib/actions/_helpers.js"),
			"utf-8",
		);
		assert.ok(
			content.includes("revalidateTag") && content.includes("next/cache"),
			"_helpers.js must import revalidateTag from next/cache",
		);
	});

	it("invalidates dashboard-summary tag", () => {
		const content = readFileSync(
			resolve(ROOT, "src/lib/actions/_helpers.js"),
			"utf-8",
		);
		assert.ok(
			/revalidateTag\(\s*['"]dashboard-summary['"]\s*\)/.test(content),
			"_helpers.js must call revalidateTag for dashboard-summary",
		);
	});

	it("invalidates cattle-list tag on cattleListPages mutation", () => {
		const content = readFileSync(
			resolve(ROOT, "src/lib/actions/_helpers.js"),
			"utf-8",
		);
		assert.ok(
			/revalidateTag\(\s*['"]cattle-list['"]\s*\)/.test(content),
			"_helpers.js must call revalidateTag for cattle-list",
		);
	});

	it("invalidates sales-list tag on salesListPages mutation", () => {
		const content = readFileSync(
			resolve(ROOT, "src/lib/actions/_helpers.js"),
			"utf-8",
		);
		assert.ok(
			/revalidateTag\(\s*['"]sales-list['"]\s*\)/.test(content),
			"_helpers.js must call revalidateTag for sales-list",
		);
	});
});

describe("use cache — page.js migration", () => {
	it("page.js does NOT use force-dynamic", () => {
		const content = readFileSync(resolve(ROOT, "src/app/page.js"), "utf-8");
		assert.ok(
			!content.includes("force-dynamic"),
			"page.js must NOT contain force-dynamic after migration",
		);
	});

	it("page.js imports cached query wrappers", () => {
		const content = readFileSync(resolve(ROOT, "src/app/page.js"), "utf-8");
		assert.ok(
			content.includes("getCachedDashboardSummary"),
			"page.js must use getCachedDashboardSummary",
		);
		assert.ok(
			content.includes("getCachedCattleList"),
			"page.js must use getCachedCattleList",
		);
		assert.ok(
			content.includes("getCachedSalesList"),
			"page.js must use getCachedSalesList",
		);
	});

	it("page.js does NOT directly import prisma", () => {
		const content = readFileSync(resolve(ROOT, "src/app/page.js"), "utf-8");
		assert.ok(
			!content.includes("from '@/lib/db'"),
			"page.js should not directly import prisma client",
		);
	});
});
