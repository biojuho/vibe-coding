/**
 * Behavioral tests for private pure helpers in:
 *   AIChatWidget.js       — buildOfflineReply, shouldUseFallbackGuide, buildApiHistory
 *   AIInsightWidget.js    — formatCacheAgeLabel
 *   EarTagScannerModal.js — formatScannerBirthDate, normalizeScannerCattleList
 *
 * All files import React; cannot be loaded in Node ESM.
 * Helpers are re-implemented inline with source-grep guards.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

const chatSrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/AIChatWidget.js"),
	"utf8",
);
const insightSrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/AIInsightWidget.js"),
	"utf8",
);
const scannerSrc = readFileSync(
	path.join(SRC_ROOT, "components/widgets/EarTagScannerModal.js"),
	"utf8",
);

// ── AIChatWidget inline re-implementations ────────────────────────────────────

const FALLBACK_GUIDE_PREFIX =
	"AI 연결이 불안정해 기본 운영 가이드로 먼저 안내합니다. 최신 농장 정보 기반 답변은 잠시 후 다시 시도해 주세요.";

function buildOfflineReply(question) {
	const q = question.toLowerCase();
	if (q.includes("발정")) {
		return "전제: 실시간 농장 정보가 연결되지 않아 일반적인 발정 확인 기준으로 안내합니다.\n오늘 확인할 것:\n- 승가 허용, 꼬리 들기, 외음부 점액, 활동량 증가를 같은 시간대에 2회 이상 확인하세요.\n- 이력번호와 마지막 관찰 시각을 기록하고, 12~18시간 내 수정 적기 여부를 점검하세요.\n- 발열, 식욕 저하, 통증처럼 질병 징후가 겹치면 수의사 상담을 우선하세요.\n다음에 확인할 정보: 개체 이력번호, 마지막 발정일, 분만/수정 이력";
	}
	if (q.includes("급여") || q.includes("사료")) {
		return "전제: 실시간 사료 재고와 개체 체중을 확인하지 못해 일반 기준으로 안내합니다.\n바로 할 일:\n- 송아지는 초기 사료와 건초 섭취량을 함께 기록하세요.\n- 번식우는 과비를 피하도록 체형 점수와 섭취량을 같이 확인하세요.\n- 비육우는 후기 사료 비중을 급격히 바꾸지 말고 단계적으로 조정하세요.\n다음에 확인할 정보: 개체군, 평균 체중, 현재 급여량, 남은 사료 재고";
	}
	if (q.includes("안녕")) {
		return "안녕하세요. 오늘 농장 운영에서 궁금한 부분을 질문해 주세요.";
	}
	return "전제: 실시간 농장 정보가 연결되지 않아 일반 운영 기준으로 안내합니다.\n바로 할 일:\n- 질문에 관련된 개체 이력번호, 날짜, 증상, 기록값을 먼저 정리하세요.\n- 발정, 급여, 건강관리, 출하, 재고처럼 한 가지 주제로 좁혀 다시 질문하면 더 정확합니다.\n- 응급 질병이나 통증 징후가 있으면 기록보다 수의사 상담을 우선하세요.\n다음에 확인할 정보: 주제, 개체 이력번호, 관찰 시각, 최근 변경 사항";
}

function shouldUseFallbackGuide(errorMsg) {
	const message = typeof errorMsg === "string" ? errorMsg : "";
	const nonRecoverableErrors = [
		"로그인이 필요",
		"질문은",
		"대화 이력",
		"요청 본문",
	];
	return !nonRecoverableErrors.some((token) => message.includes(token));
}

function buildFallbackGuide(question) {
	return `${FALLBACK_GUIDE_PREFIX}\n\n${buildOfflineReply(question)}`;
}

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

// ── AIInsightWidget inline re-implementations ────────────────────────────────

function formatCacheAgeLabel(ageSeconds) {
	const seconds = Number(ageSeconds);
	if (!Number.isFinite(seconds) || seconds < 0) return null;
	if (seconds < 60) return "방금 분석";
	const minutes = Math.floor(seconds / 60);
	if (minutes < 60) return `${minutes}분 전 캐시`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}시간 전 캐시`;
	return "오늘 분석 결과";
}

// ── EarTagScannerModal inline re-implementations ──────────────────────────────

function formatScannerBirthDate(value) {
	if (!value) {
		return "생년월일 미등록";
	}
	const date = new Date(value);
	return Number.isNaN(date.getTime())
		? "생년월일 미등록"
		: date.toLocaleDateString("ko-KR");
}

function normalizeScannerCattleList(cattleList) {
	return Array.isArray(cattleList)
		? cattleList.filter(
				(cow) => cow && typeof cow === "object" && !Array.isArray(cow),
			)
		: [];
}

// ── Source-grep guards: AIChatWidget ─────────────────────────────────────────

test("AIChatWidget.js shouldUseFallbackGuide: non-recoverable error list", () => {
	assert.match(chatSrc, /function shouldUseFallbackGuide\(errorMsg\)/);
	assert.match(chatSrc, /["']로그인이 필요["']/);
	assert.match(chatSrc, /["']질문은["']/);
	assert.match(chatSrc, /["']대화 이력["']/);
	assert.match(chatSrc, /["']요청 본문["']/);
	assert.match(chatSrc, /nonRecoverableErrors\.some\(\(token\) => message\.includes\(token\)\)/);
});

test("AIChatWidget.js buildApiHistory skips system messages before first user turn", () => {
	assert.match(chatSrc, /function buildApiHistory\(messages\)/);
	assert.match(chatSrc, /let hasUserTurn = false/);
	assert.match(chatSrc, /hasUserTurn && message\.role === ["']system["']/);
});

test("AIChatWidget.js buildOfflineReply routes by 발정/급여|사료/안녕 keywords", () => {
	assert.match(chatSrc, /function buildOfflineReply\(question\)/);
	assert.match(chatSrc, /q\.includes\(["']발정["']\)/);
	assert.match(chatSrc, /q\.includes\(["']급여["']\) \|\| q\.includes\(["']사료["']\)/);
	assert.match(chatSrc, /q\.includes\(["']안녕["']\)/);
});

// ── Source-grep guards: AIInsightWidget ──────────────────────────────────────

test("AIInsightWidget.js formatCacheAgeLabel: thresholds 60s, 3600s, 86400s", () => {
	assert.match(insightSrc, /function formatCacheAgeLabel\(ageSeconds\)/);
	assert.match(insightSrc, /seconds < 60/);
	assert.match(insightSrc, /minutes < 60/);
	assert.match(insightSrc, /hours < 24/);
});

// ── Source-grep guards: EarTagScannerModal ────────────────────────────────────

test("EarTagScannerModal.js formatScannerBirthDate: falsy → 생년월일 미등록", () => {
	assert.match(scannerSrc, /function formatScannerBirthDate\(value\)/);
	assert.match(scannerSrc, /["']생년월일 미등록["']/);
	assert.match(scannerSrc, /toLocaleDateString\(["']ko-KR["']\)/);
});

test("EarTagScannerModal.js normalizeScannerCattleList filters plain objects", () => {
	assert.match(scannerSrc, /function normalizeScannerCattleList\(cattleList\)/);
	assert.match(scannerSrc, /!Array\.isArray\(cow\)/);
});

// ── buildOfflineReply behavioral tests ───────────────────────────────────────

test("buildOfflineReply returns estrus guide for questions containing '발정'", () => {
	const result = buildOfflineReply("발정 확인 방법이 뭔가요?");
	assert.ok(result.includes("발정"));
	assert.ok(result.includes("승가 허용"));
});

test("buildOfflineReply is case-insensitive via lowercase()", () => {
	// '발정' is Korean and not affected by toLowerCase but the function does toLowerCase
	// Test that uppercase ASCII in mixed question doesn't break routing
	const result = buildOfflineReply("발정 체크 방법 HELP");
	assert.ok(result.includes("발정"));
});

test("buildOfflineReply returns feed guide for questions containing '급여'", () => {
	const result = buildOfflineReply("급여 시간 알려줘");
	assert.ok(result.includes("사료"));
});

test("buildOfflineReply returns feed guide for questions containing '사료'", () => {
	const result = buildOfflineReply("사료 배합 비율은?");
	assert.ok(result.includes("사료"));
});

test("buildOfflineReply returns greeting for questions containing '안녕'", () => {
	const result = buildOfflineReply("안녕하세요");
	assert.equal(result, "안녕하세요. 오늘 농장 운영에서 궁금한 부분을 질문해 주세요.");
});

test("buildOfflineReply returns generic fallback for unmatched questions", () => {
	const result = buildOfflineReply("출하 일정 언제야?");
	assert.ok(result.includes("일반 운영 기준"));
	assert.ok(result.includes("개체 이력번호"));
});

test("buildFallbackGuide prepends FALLBACK_GUIDE_PREFIX", () => {
	const result = buildFallbackGuide("발정 질문");
	assert.ok(result.startsWith(FALLBACK_GUIDE_PREFIX));
	assert.ok(result.includes("승가 허용")); // offline reply part
});

// ── shouldUseFallbackGuide behavioral tests ───────────────────────────────────

test("shouldUseFallbackGuide returns true for generic connection error", () => {
	assert.equal(shouldUseFallbackGuide("AI 비서 연결이 불안정합니다"), true);
	assert.equal(shouldUseFallbackGuide("서버 오류 (500)"), true);
});

test("shouldUseFallbackGuide returns false for '로그인이 필요' errors", () => {
	assert.equal(shouldUseFallbackGuide("로그인이 필요합니다"), false);
});

test("shouldUseFallbackGuide returns false for '질문은' errors", () => {
	assert.equal(shouldUseFallbackGuide("질문은 10자 이상 입력해 주세요"), false);
});

test("shouldUseFallbackGuide returns false for '대화 이력' errors", () => {
	assert.equal(shouldUseFallbackGuide("대화 이력이 너무 깁니다"), false);
});

test("shouldUseFallbackGuide returns false for '요청 본문' errors", () => {
	assert.equal(shouldUseFallbackGuide("요청 본문 파싱 오류"), false);
});

test("shouldUseFallbackGuide returns true for non-string errorMsg (coerces to empty string)", () => {
	// null, undefined, number → empty string → no tokens match → returns true
	assert.equal(shouldUseFallbackGuide(null), true);
	assert.equal(shouldUseFallbackGuide(undefined), true);
	assert.equal(shouldUseFallbackGuide(42), true);
});

// ── buildApiHistory behavioral tests ─────────────────────────────────────────

test("buildApiHistory returns empty array for empty messages", () => {
	assert.deepEqual(buildApiHistory([]), []);
});

test("buildApiHistory skips messages with no content", () => {
	const messages = [
		{ role: "user", content: "" },
		{ role: "user", content: null },
		{ role: "user", content: "유효한 질문" },
	];
	const result = buildApiHistory(messages);
	assert.equal(result.length, 1);
	assert.equal(result[0].content, "유효한 질문");
});

test("buildApiHistory skips system messages that appear BEFORE first user message", () => {
	const messages = [
		{ role: "system", content: "초기 시스템 메시지" },
		{ role: "user", content: "첫 번째 질문" },
		{ role: "system", content: "AI 응답" },
	];
	const result = buildApiHistory(messages);
	// Initial system message skipped; user + post-user system kept
	assert.equal(result.length, 2);
	assert.equal(result[0].role, "user");
	assert.equal(result[1].role, "system");
	assert.equal(result[1].content, "AI 응답");
});

test("buildApiHistory includes system messages AFTER first user turn", () => {
	const messages = [
		{ role: "user", content: "질문1" },
		{ role: "system", content: "응답1" },
		{ role: "user", content: "질문2" },
		{ role: "system", content: "응답2" },
	];
	const result = buildApiHistory(messages);
	assert.equal(result.length, 4);
	assert.deepEqual(result[0], { role: "user", content: "질문1" });
	assert.deepEqual(result[1], { role: "system", content: "응답1" });
	assert.deepEqual(result[2], { role: "user", content: "질문2" });
	assert.deepEqual(result[3], { role: "system", content: "응답2" });
});

test("buildApiHistory ignores messages with neither 'user' nor 'system' role", () => {
	const messages = [
		{ role: "user", content: "질문" },
		{ role: "assistant", content: "비서 응답" }, // not added
		{ role: "system", content: "정상 응답" },
	];
	const result = buildApiHistory(messages);
	assert.equal(result.length, 2);
	assert.ok(result.every((m) => m.role !== "assistant"));
});

test("buildApiHistory preserves message content exactly", () => {
	const messages = [
		{ role: "user", content: "  한국어 질문  " },
	];
	const result = buildApiHistory(messages);
	assert.equal(result[0].content, "  한국어 질문  ");
});

// ── formatCacheAgeLabel behavioral tests ─────────────────────────────────────

test("formatCacheAgeLabel returns null for non-finite values", () => {
	assert.equal(formatCacheAgeLabel(NaN), null);
	assert.equal(formatCacheAgeLabel(Infinity), null);
	assert.equal(formatCacheAgeLabel(-Infinity), null);
	// Number(undefined) = NaN → null; Number(null) = 0 → "방금 분석" (not null)
	assert.equal(formatCacheAgeLabel(undefined), null);
});

test("formatCacheAgeLabel returns null for negative values", () => {
	assert.equal(formatCacheAgeLabel(-1), null);
	assert.equal(formatCacheAgeLabel(-0.001), null);
});

test("formatCacheAgeLabel returns '방금 분석' for 0 seconds (and for null, since Number(null)=0)", () => {
	assert.equal(formatCacheAgeLabel(0), "방금 분석");
	// Number(null) = 0 → finite, non-negative → "방금 분석"
	assert.equal(formatCacheAgeLabel(null), "방금 분석");
});

test("formatCacheAgeLabel returns '방금 분석' for < 60 seconds", () => {
	assert.equal(formatCacheAgeLabel(59), "방금 분석");
	assert.equal(formatCacheAgeLabel(1), "방금 분석");
	assert.equal(formatCacheAgeLabel(30), "방금 분석");
});

test("formatCacheAgeLabel returns '{n}분 전 캐시' for 60s to < 3600s", () => {
	assert.equal(formatCacheAgeLabel(60), "1분 전 캐시");
	assert.equal(formatCacheAgeLabel(120), "2분 전 캐시");
	assert.equal(formatCacheAgeLabel(3599), "59분 전 캐시");
});

test("formatCacheAgeLabel returns '{n}시간 전 캐시' for 3600s to < 86400s", () => {
	assert.equal(formatCacheAgeLabel(3600), "1시간 전 캐시");
	assert.equal(formatCacheAgeLabel(7200), "2시간 전 캐시");
	assert.equal(formatCacheAgeLabel(86399), "23시간 전 캐시");
});

test("formatCacheAgeLabel returns '오늘 분석 결과' for >= 86400s", () => {
	assert.equal(formatCacheAgeLabel(86400), "오늘 분석 결과");
	assert.equal(formatCacheAgeLabel(172800), "오늘 분석 결과");
});

test("formatCacheAgeLabel accepts numeric strings (Number() conversion)", () => {
	assert.equal(formatCacheAgeLabel("30"), "방금 분석");
	assert.equal(formatCacheAgeLabel("120"), "2분 전 캐시");
});

// ── formatScannerBirthDate behavioral tests ───────────────────────────────────

test("formatScannerBirthDate returns '생년월일 미등록' for falsy values", () => {
	assert.equal(formatScannerBirthDate(null), "생년월일 미등록");
	assert.equal(formatScannerBirthDate(undefined), "생년월일 미등록");
	assert.equal(formatScannerBirthDate(""), "생년월일 미등록");
	assert.equal(formatScannerBirthDate(0), "생년월일 미등록");
	assert.equal(formatScannerBirthDate(false), "생년월일 미등록");
});

test("formatScannerBirthDate returns '생년월일 미등록' for invalid date string", () => {
	assert.equal(formatScannerBirthDate("not-a-date"), "생년월일 미등록");
	assert.equal(formatScannerBirthDate("abc"), "생년월일 미등록");
});

test("formatScannerBirthDate returns a locale string for valid date string", () => {
	// toLocaleDateString("ko-KR") output is locale-dependent — just check it's a string
	const result = formatScannerBirthDate("2026-06-15");
	assert.ok(typeof result === "string" && result !== "생년월일 미등록");
});

test("formatScannerBirthDate returns a locale string for valid Date instance", () => {
	const d = new Date(2026, 5, 15); // June 15 in local time
	const result = formatScannerBirthDate(d);
	assert.ok(typeof result === "string" && result !== "생년월일 미등록");
});

// ── normalizeScannerCattleList behavioral tests ───────────────────────────────

test("normalizeScannerCattleList returns empty array for non-array input", () => {
	assert.deepEqual(normalizeScannerCattleList(null), []);
	assert.deepEqual(normalizeScannerCattleList(undefined), []);
	assert.deepEqual(normalizeScannerCattleList({}), []);
});

test("normalizeScannerCattleList filters null, primitives, and arrays", () => {
	const cattle = [null, "string", 42, [], { id: "c1" }];
	assert.equal(normalizeScannerCattleList(cattle).length, 1);
});

test("normalizeScannerCattleList keeps plain objects regardless of id", () => {
	const cattle = [{ earTag: "001" }, { earTag: "002" }];
	assert.equal(normalizeScannerCattleList(cattle).length, 2);
});
