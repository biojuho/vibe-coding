/**
 * Behavioral tests for private pure helpers in widget components:
 *   buildApiHistory        — src/components/widgets/AIChatWidget.js
 *   getSourcePresentation  — src/components/widgets/MarketPriceWidget.js
 *   formatPerHeadFeedCost  — src/components/widgets/ProfitabilityWidget.js
 *   formatMonthlyGain      — src/components/widgets/ProfitabilityWidget.js
 *
 * All files import React and cannot be loaded in Node ESM.
 * Helpers are re-implemented inline with source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const chatWidgetSrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/AIChatWidget.js"),
	"utf8",
);
const marketPriceSrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/MarketPriceWidget.js"),
	"utf8",
);
const profitabilitySrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/ProfitabilityWidget.js"),
	"utf8",
);

// ── Inline re-implementations ─────────────────────────────────────────────────

// From AIChatWidget.js
function buildApiHistory(messages) {
	const history = [];
	let hasUserTurn = false;

	messages.forEach((message) => {
		if (!message.content) return;
		if (message.role === "user") {
			hasUserTurn = true;
			history.push({ role: "user", content: message.content });
		} else if (hasUserTurn && message.role === "system") {
			history.push({ role: "system", content: message.content });
		}
	});

	return history;
}

// From MarketPriceWidget.js
function getSourcePresentation(prices) {
	switch (prices?.source) {
		case "kape-live":
			return {
				label: "실시간 KAPE",
				style: {
					background: "color-mix(in srgb, var(--chart-clay-5) 18%, white 82%)",
					color: "var(--chart-clay-5)",
					borderColor:
						"color-mix(in srgb, var(--chart-clay-5) 32%, transparent)",
				},
			};
		case "kape-cache":
			return {
				label: "저장된 KAPE",
				style: {
					background: "color-mix(in srgb, var(--chart-clay-3) 18%, white 82%)",
					color: "var(--chart-clay-3)",
					borderColor:
						"color-mix(in srgb, var(--chart-clay-3) 32%, transparent)",
				},
			};
		case "cache-stale":
			return {
				label: "이전 저장값",
				style: {
					background: "color-mix(in srgb, var(--chart-clay-2) 18%, white 82%)",
					color: "var(--chart-clay-2)",
					borderColor:
						"color-mix(in srgb, var(--chart-clay-2) 32%, transparent)",
				},
			};
		default:
			return {
				label: "시세 확인 불가",
				style: {
					background: "color-mix(in srgb, #9aa2ad 18%, white 82%)",
					color: "#637083",
					borderColor: "color-mix(in srgb, #9aa2ad 32%, transparent)",
				},
			};
	}
}

// From ProfitabilityWidget.js
function formatPerHeadFeedCost(value) {
	if (!Number.isFinite(value) || value <= 0) return null;
	return `${Math.round(value / 1000)}천원`;
}

function formatMonthlyGain(value) {
	if (!Number.isFinite(value) || value <= 0) return null;
	const rounded = Math.round(value * 10) / 10;
	return `${rounded}kg`;
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("AIChatWidget.js buildApiHistory gates system messages on hasUserTurn", () => {
	assert.match(chatWidgetSrc, /function buildApiHistory\(messages\)/);
	assert.match(chatWidgetSrc, /let hasUserTurn = false/);
	assert.match(chatWidgetSrc, /hasUserTurn && message\.role === ["']system["']/);
	assert.match(chatWidgetSrc, /if \(!message\.content\) return/);
});

test("MarketPriceWidget.js getSourcePresentation uses switch on prices?.source", () => {
	assert.match(marketPriceSrc, /function getSourcePresentation\(prices\)/);
	assert.match(marketPriceSrc, /switch \(prices\?\.source\)/);
	assert.match(marketPriceSrc, /case ["']kape-live["']/);
	assert.match(marketPriceSrc, /case ["']kape-cache["']/);
	assert.match(marketPriceSrc, /case ["']cache-stale["']/);
	assert.match(marketPriceSrc, /"시세 확인 불가"/);
});

test("ProfitabilityWidget.js formatPerHeadFeedCost guards with isFinite and >0", () => {
	assert.match(profitabilitySrc, /function formatPerHeadFeedCost\(value\)/);
	assert.match(profitabilitySrc, /!Number\.isFinite\(value\) \|\| value <= 0/);
	assert.match(profitabilitySrc, /Math\.round\(value \/ 1000\)/);
	assert.match(profitabilitySrc, /천원/);
});

test("ProfitabilityWidget.js formatMonthlyGain guards with isFinite and >0", () => {
	assert.match(profitabilitySrc, /function formatMonthlyGain\(value\)/);
	assert.match(profitabilitySrc, /!Number\.isFinite\(value\) \|\| value <= 0/);
	assert.match(profitabilitySrc, /Math\.round\(value \* 10\) \/ 10/);
	assert.match(profitabilitySrc, /`\$\{rounded\}kg`/);
});

// ── buildApiHistory behavioral tests ─────────────────────────────────────────

test("buildApiHistory returns empty array for empty messages", () => {
	assert.deepEqual(buildApiHistory([]), []);
});

test("buildApiHistory includes user messages", () => {
	const msgs = [{ role: "user", content: "안녕하세요" }];
	const result = buildApiHistory(msgs);
	assert.equal(result.length, 1);
	assert.equal(result[0].role, "user");
	assert.equal(result[0].content, "안녕하세요");
});

test("buildApiHistory skips messages with falsy content", () => {
	const msgs = [
		{ role: "user", content: "" },
		{ role: "user", content: null },
		{ role: "user", content: undefined },
		{ role: "user", content: "실제 메시지" },
	];
	const result = buildApiHistory(msgs);
	assert.equal(result.length, 1);
	assert.equal(result[0].content, "실제 메시지");
});

test("buildApiHistory excludes system messages before first user turn", () => {
	const msgs = [
		{ role: "system", content: "시스템 초기화" },
		{ role: "user", content: "첫 질문" },
	];
	const result = buildApiHistory(msgs);
	// system before user → skipped; user → included
	assert.equal(result.length, 1);
	assert.equal(result[0].role, "user");
});

test("buildApiHistory includes system messages after a user turn", () => {
	const msgs = [
		{ role: "user", content: "질문" },
		{ role: "system", content: "응답 컨텍스트" },
	];
	const result = buildApiHistory(msgs);
	assert.equal(result.length, 2);
	assert.equal(result[0].role, "user");
	assert.equal(result[1].role, "system");
	assert.equal(result[1].content, "응답 컨텍스트");
});

test("buildApiHistory skips assistant and other roles", () => {
	const msgs = [
		{ role: "user", content: "질문" },
		{ role: "assistant", content: "AI 응답" },
		{ role: "user", content: "후속 질문" },
	];
	const result = buildApiHistory(msgs);
	// only user messages
	assert.equal(result.length, 2);
	assert.ok(result.every((m) => m.role === "user"));
});

test("buildApiHistory interleaves user and system messages correctly", () => {
	const msgs = [
		{ role: "system", content: "무시됨" }, // before first user
		{ role: "user", content: "첫 번째" },
		{ role: "system", content: "포함됨" },
		{ role: "user", content: "두 번째" },
		{ role: "system", content: "포함됨 2" },
	];
	const result = buildApiHistory(msgs);
	assert.equal(result.length, 4);
	assert.equal(result[0].content, "첫 번째");
	assert.equal(result[1].content, "포함됨");
	assert.equal(result[2].content, "두 번째");
	assert.equal(result[3].content, "포함됨 2");
});

// ── getSourcePresentation behavioral tests ────────────────────────────────────

test("getSourcePresentation returns '실시간 KAPE' label for kape-live source", () => {
	const result = getSourcePresentation({ source: "kape-live" });
	assert.equal(result.label, "실시간 KAPE");
	assert.ok(result.style);
});

test("getSourcePresentation returns '저장된 KAPE' label for kape-cache source", () => {
	const result = getSourcePresentation({ source: "kape-cache" });
	assert.equal(result.label, "저장된 KAPE");
});

test("getSourcePresentation returns '이전 저장값' label for cache-stale source", () => {
	const result = getSourcePresentation({ source: "cache-stale" });
	assert.equal(result.label, "이전 저장값");
});

test("getSourcePresentation returns '시세 확인 불가' for unknown source", () => {
	const result = getSourcePresentation({ source: "unknown-source" });
	assert.equal(result.label, "시세 확인 불가");
});

test("getSourcePresentation returns '시세 확인 불가' for null prices", () => {
	const result = getSourcePresentation(null);
	assert.equal(result.label, "시세 확인 불가");
});

test("getSourcePresentation returns '시세 확인 불가' for undefined prices", () => {
	const result = getSourcePresentation(undefined);
	assert.equal(result.label, "시세 확인 불가");
});

test("getSourcePresentation returns '시세 확인 불가' for prices without source field", () => {
	const result = getSourcePresentation({});
	assert.equal(result.label, "시세 확인 불가");
});

test("getSourcePresentation always includes label and style properties", () => {
	const sources = ["kape-live", "kape-cache", "cache-stale", null, undefined, {}];
	for (const s of sources) {
		const input = typeof s === "string" ? { source: s } : s;
		const result = getSourcePresentation(input);
		assert.ok("label" in result, `label missing for source: ${JSON.stringify(s)}`);
		assert.ok("style" in result, `style missing for source: ${JSON.stringify(s)}`);
	}
});

// ── formatPerHeadFeedCost behavioral tests ────────────────────────────────────

test("formatPerHeadFeedCost returns null for zero", () => {
	assert.equal(formatPerHeadFeedCost(0), null);
});

test("formatPerHeadFeedCost returns null for negative values", () => {
	assert.equal(formatPerHeadFeedCost(-1), null);
	assert.equal(formatPerHeadFeedCost(-500000), null);
});

test("formatPerHeadFeedCost returns null for non-finite values", () => {
	assert.equal(formatPerHeadFeedCost(NaN), null);
	assert.equal(formatPerHeadFeedCost(Infinity), null);
	assert.equal(formatPerHeadFeedCost(-Infinity), null);
	assert.equal(formatPerHeadFeedCost(null), null);
	assert.equal(formatPerHeadFeedCost(undefined), null);
});

test("formatPerHeadFeedCost converts 1000 to '1천원'", () => {
	assert.equal(formatPerHeadFeedCost(1000), "1천원");
});

test("formatPerHeadFeedCost rounds to nearest thousand", () => {
	assert.equal(formatPerHeadFeedCost(1500), "2천원");
	assert.equal(formatPerHeadFeedCost(1499), "1천원");
	assert.equal(formatPerHeadFeedCost(500000), "500천원");
});

test("formatPerHeadFeedCost formats 1 (minimal positive) as '0천원' (rounds to 0)", () => {
	// Math.round(1/1000) = 0 → "0천원"
	assert.equal(formatPerHeadFeedCost(1), "0천원");
});

// ── formatMonthlyGain behavioral tests ────────────────────────────────────────

test("formatMonthlyGain returns null for zero", () => {
	assert.equal(formatMonthlyGain(0), null);
});

test("formatMonthlyGain returns null for negative values", () => {
	assert.equal(formatMonthlyGain(-1), null);
	assert.equal(formatMonthlyGain(-100), null);
});

test("formatMonthlyGain returns null for non-finite values", () => {
	assert.equal(formatMonthlyGain(NaN), null);
	assert.equal(formatMonthlyGain(Infinity), null);
	assert.equal(formatMonthlyGain(null), null);
	assert.equal(formatMonthlyGain(undefined), null);
});

test("formatMonthlyGain returns '1kg' for value 1", () => {
	assert.equal(formatMonthlyGain(1), "1kg");
});

test("formatMonthlyGain rounds to one decimal place", () => {
	assert.equal(formatMonthlyGain(1.05), "1.1kg");
	assert.equal(formatMonthlyGain(1.04), "1kg");
	assert.equal(formatMonthlyGain(2.75), "2.8kg");
});

test("formatMonthlyGain returns '0.5kg' for 0.5 (positive but < 1)", () => {
	assert.equal(formatMonthlyGain(0.5), "0.5kg");
});

test("formatMonthlyGain formats large gains correctly", () => {
	assert.equal(formatMonthlyGain(100), "100kg");
	assert.equal(formatMonthlyGain(37.55), "37.6kg");
});
