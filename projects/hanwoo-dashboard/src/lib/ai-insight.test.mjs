import assert from "node:assert/strict";
import test from "node:test";

import {
	MAX_INSIGHTS,
	buildHeuristicInsights,
	buildInsightPrompt,
	parseInsightResponse,
	summarizeFarmForInsight,
} from "./ai-insight.mjs";

test("summarizeFarmForInsight gracefully handles missing/garbage input", () => {
	const empty = summarizeFarmForInsight(null);
	assert.equal(empty.totalHeadcount, 0);
	assert.equal(empty.monthlySalesCount, 0);
	assert.equal(empty.monthlySalesManwon, 0);
	assert.equal(empty.thi, null);
	assert.equal(empty.shipmentCandidates, 0);
	assert.equal(empty.decliningMarginCount, 0);
	assert.equal(empty.topShipment, null);
	assert.deepEqual(empty.notificationCounts, {
		estrus: 0,
		calving: 0,
		alert: 0,
	});

	const garbage = summarizeFarmForInsight({
		totalHeadcount: "not-a-number",
		monthlySalesTotal: undefined,
		profitabilityItems: "nope",
		notifications: 42,
		weather: "warm",
	});
	assert.equal(garbage.totalHeadcount, 0);
	assert.equal(garbage.monthlySalesManwon, 0);
	assert.equal(garbage.thi, null);
});

test("summarizeFarmForInsight aggregates profitability and notifications", () => {
	const summary = summarizeFarmForInsight({
		totalHeadcount: 42.7,
		monthlySalesCount: 3,
		monthlySalesTotal: 27_000_000,
		profitabilityItems: [
			{
				tagNumber: "002-12345",
				recommendShipment: true,
				currentProfit: 850_000,
				marginalGain: -120_000,
			},
			{ recommendShipment: false, marginalGain: -5_000 },
			{ recommendShipment: false, marginalGain: 50_000 },
		],
		notifications: [
			{ type: "estrus" },
			{ type: "estrus" },
			{ type: "calving" },
			{ type: "alert" },
			{},
		],
		weather: { thi: 79.4, temp: 31.2, humidity: 65 },
	});

	assert.equal(summary.totalHeadcount, 43);
	assert.equal(summary.monthlySalesCount, 3);
	assert.equal(summary.monthlySalesManwon, 2700);
	assert.equal(summary.shipmentCandidates, 1);
	assert.equal(summary.decliningMarginCount, 2);
	assert.equal(summary.thi, 79);
	assert.equal(summary.temp, 31);
	assert.equal(summary.humidity, 65);
	assert.deepEqual(summary.notificationCounts, {
		estrus: 2,
		calving: 1,
		alert: 1,
	});
	assert.deepEqual(summary.topShipment, {
		tag: "2345",
		marginManwon: 85,
	});
});

test("summarizeFarmForInsight ignores malformed margin rows and clamps negative sales", () => {
	const summary = summarizeFarmForInsight({
		monthlySalesCount: -2,
		monthlySalesTotal: -3_400_000,
		profitabilityItems: [
			{},
			{ marginalGain: undefined },
			{ marginalGain: Number.NaN },
			{ marginalGain: "-1000" },
			{ marginalGain: 0 },
			{ marginalGain: 125_000 },
		],
	});

	assert.equal(summary.monthlySalesCount, 0);
	assert.equal(summary.monthlySalesManwon, 0);
	assert.equal(summary.decliningMarginCount, 2);
});

test("buildInsightPrompt embeds the snapshot and requests strict JSON", () => {
	const prompt = buildInsightPrompt({
		totalHeadcount: 12,
		monthlySalesCount: 1,
		monthlySalesTotal: 8_000_000,
		profitabilityItems: [{ recommendShipment: true, currentProfit: 200_000 }],
		notifications: [{ type: "estrus" }],
		weather: { thi: 80, temp: 32, humidity: 70 },
	});
	assert.match(prompt, /총 사육두수: 12두/);
	assert.match(prompt, /이번달 출하: 1두/);
	assert.match(prompt, /즉시 출하 권장 개체: 1두/);
	assert.match(prompt, /발정 알림: 1건/);
	assert.match(prompt, /THI 80/);
	assert.match(prompt, /JSON 배열로 정확히 3개의 인사이트/);
	assert.match(prompt, /순수 JSON만 반환/);
});

test("parseInsightResponse accepts well-formed arrays and {insights} envelopes", () => {
	const direct = parseInsightResponse([
		{ title: "헤드라인", body: "조언", priority: "high" },
		{ title: "또다른", body: "조언", priority: "MEDIUM" },
	]);
	assert.equal(direct.length, 2);
	assert.equal(direct[0].priority, "high");
	assert.equal(direct[1].priority, "medium");

	const envelope = parseInsightResponse({
		insights: [{ title: "A", body: "B", priority: "low" }],
	});
	assert.equal(envelope.length, 1);
	assert.equal(envelope[0].priority, "low");
});

test("parseInsightResponse strips code fences from string payloads", () => {
	const fenced = `\`\`\`json\n[{"title":"제목","body":"본문","priority":"high"}]\n\`\`\``;
	const parsed = parseInsightResponse(fenced);
	assert.equal(parsed.length, 1);
	assert.equal(parsed[0].title, "제목");
});

test("parseInsightResponse drops bad items, caps at MAX_INSIGHTS, and rejects total garbage", () => {
	assert.equal(parseInsightResponse(null), null);
	assert.equal(parseInsightResponse("not json"), null);
	assert.equal(parseInsightResponse({}), null);

	const dropped = parseInsightResponse([
		{ title: "ok", body: "body", priority: "high" },
		{ title: "", body: "missing title", priority: "high" },
		{ title: "missing body", body: "" },
		{ title: "default priority", body: "body" },
		{ title: "fourth", body: "body" },
		{ title: "fifth", body: "body" },
	]);
	assert.equal(dropped.length, MAX_INSIGHTS);
	assert.equal(dropped[1].priority, "medium");
});

test("buildHeuristicInsights surfaces a shipment recommendation when present", () => {
	const insights = buildHeuristicInsights({
		totalHeadcount: 30,
		monthlySalesCount: 2,
		monthlySalesTotal: 20_000_000,
		profitabilityItems: [
			{
				tagNumber: "001-99999",
				recommendShipment: true,
				currentProfit: 1_200_000,
				marginalGain: -100_000,
			},
		],
		notifications: [],
		weather: { thi: 70 },
	});
	assert.equal(insights.length, MAX_INSIGHTS);
	const titles = insights.map((i) => i.title);
	assert.ok(
		titles.includes("즉시 출하 권장"),
		"shipment insight should always surface when recommendShipment is true",
	);
	const shipment = insights.find((i) => i.title === "즉시 출하 권장");
	assert.equal(shipment.priority, "high");
	assert.match(shipment.body, /9999호/);
	assert.match(shipment.body, /\+120만원/);
});

test("buildHeuristicInsights surfaces THI heat warning when severe", () => {
	const insights = buildHeuristicInsights({
		totalHeadcount: 5,
		profitabilityItems: [],
		notifications: [],
		weather: { thi: 82 },
	});
	const titles = insights.map((i) => i.title);
	assert.ok(titles.includes("고온 스트레스 경고"));
});

test("buildHeuristicInsights returns 3 safe defaults when no signals exist", () => {
	const insights = buildHeuristicInsights({});
	assert.equal(insights.length, MAX_INSIGHTS);
	insights.forEach((insight) => {
		assert.ok(typeof insight.title === "string" && insight.title.length > 0);
		assert.ok(typeof insight.body === "string" && insight.body.length > 0);
		assert.ok(["high", "medium", "low"].includes(insight.priority));
	});
});

test("buildHeuristicInsights sorts by priority (high → medium → low)", () => {
	const insights = buildHeuristicInsights({
		totalHeadcount: 50,
		monthlySalesCount: 5,
		monthlySalesTotal: 50_000_000,
		profitabilityItems: [
			{ recommendShipment: true, currentProfit: 800_000 },
			{ marginalGain: -10_000 },
		],
		notifications: [{ type: "estrus" }],
		weather: { thi: 80 },
	});
	const priorities = insights.map((i) => i.priority);
	const sorted = [...priorities].sort((a, b) => {
		const order = { high: 0, medium: 1, low: 2 };
		return order[a] - order[b];
	});
	assert.deepEqual(priorities, sorted);
});
