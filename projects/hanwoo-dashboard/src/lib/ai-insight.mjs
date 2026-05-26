/**
 * AI 인사이트 위젯의 순수 로직.
 *
 * - `summarizeFarmForInsight` — 대시보드 데이터를 LLM이 읽을 정규화 객체로.
 * - `buildInsightPrompt` — 정규화 요약을 한국어 프롬프트 문자열로.
 * - `parseInsightResponse` — LLM JSON 응답을 안전하게 파싱·검증.
 * - `buildHeuristicInsights` — LLM 미사용/실패 시의 결정론 폴백.
 *
 * 이 모듈은 클라이언트/서버/테스트가 모두 import 한다. side-effect 금지.
 */

export const MAX_INSIGHTS = 3;
export const VALID_PRIORITIES = new Set(["high", "medium", "low"]);
export const VALID_SOURCES = new Set(["ai", "heuristic"]);

const PRIORITY_ORDER = { high: 0, medium: 1, low: 2 };

function toFiniteOrZero(value) {
	const n = Number(value);
	return Number.isFinite(n) ? n : 0;
}

function toFiniteNumberOrNull(value) {
	const n = Number(value);
	return Number.isFinite(n) ? n : null;
}

function clampString(value, max) {
	if (typeof value !== "string") return "";
	const trimmed = value.trim();
	return trimmed.length > max ? `${trimmed.slice(0, max - 1)}…` : trimmed;
}

export function summarizeFarmForInsight(input) {
	const safe = input && typeof input === "object" ? input : {};
	const profitabilityItems = Array.isArray(safe.profitabilityItems)
		? safe.profitabilityItems
		: [];
	const notifications = Array.isArray(safe.notifications)
		? safe.notifications
		: [];
	const weather = safe.weather && typeof safe.weather === "object"
		? safe.weather
		: {};

	const recommendedShipments = profitabilityItems.filter(
		(item) => item && item.recommendShipment === true,
	);
	const decliningMarginCount = profitabilityItems.filter(
		(item) => {
			if (!item || typeof item !== "object") return false;
			const marginalGain = toFiniteNumberOrNull(item.marginalGain);
			return marginalGain !== null && marginalGain <= 0;
		},
	).length;
	const notificationCounts = notifications.reduce((acc, note) => {
		const type = note && typeof note.type === "string" ? note.type : "etc";
		acc[type] = (acc[type] ?? 0) + 1;
		return acc;
	}, {});

	const topShipment = recommendedShipments[0]
		? {
				tag: String(recommendedShipments[0].tagNumber ?? "")
					.trim()
					.slice(-4),
				marginManwon: Math.round(
					toFiniteOrZero(recommendedShipments[0].currentProfit) / 10000,
				),
			}
		: null;

	return {
		totalHeadcount: Math.max(0, Math.round(toFiniteOrZero(safe.totalHeadcount))),
		monthlySalesCount: Math.max(
			0,
			Math.round(toFiniteOrZero(safe.monthlySalesCount)),
		),
		monthlySalesManwon: Math.max(
			0,
			Math.round(toFiniteOrZero(safe.monthlySalesTotal) / 10000),
		),
		thi: Number.isFinite(weather.thi) ? Math.round(weather.thi) : null,
		temp: Number.isFinite(weather.temp) ? Math.round(weather.temp) : null,
		humidity: Number.isFinite(weather.humidity)
			? Math.round(weather.humidity)
			: null,
		shipmentCandidates: recommendedShipments.length,
		decliningMarginCount,
		topShipment,
		notificationCounts: {
			estrus: notificationCounts.estrus ?? 0,
			calving: notificationCounts.calving ?? 0,
			alert: notificationCounts.alert ?? 0,
		},
	};
}

export function buildInsightPrompt(summary) {
	const normalized = summarizeFarmForInsight(summary);
	const lines = [
		"## 농장 현황 스냅샷",
		`- 총 사육두수: ${normalized.totalHeadcount}두`,
		`- 이번 달 출하: ${normalized.monthlySalesCount}두 (판매액 ${normalized.monthlySalesManwon}만원)`,
		`- 즉시 출하 권장 개체: ${normalized.shipmentCandidates}두`,
		`- 추가 비육 시 마진 감소 예상: ${normalized.decliningMarginCount}두`,
		`- 발정 알림: ${normalized.notificationCounts.estrus}건 / 분만 알림: ${normalized.notificationCounts.calving}건`,
	];
	if (normalized.thi !== null) {
		const tempText =
			normalized.temp !== null ? `기온 ${normalized.temp}℃` : "기온 확인 불가";
		const humidityText =
			normalized.humidity !== null
				? `습도 ${normalized.humidity}%`
				: "습도 확인 불가";
		lines.push(
			`- 날씨: THI ${normalized.thi}, ${tempText}, ${humidityText}`,
		);
	}
	lines.push("", "## 출력 형식");
	lines.push(
		"JSON 배열로 정확히 3개의 인사이트만 반환. 각 항목은 다음 키 필수:",
	);
	lines.push(
		'- title: 12자 내외 한국어 헤드라인',
	);
	lines.push('- body: 60자 이내 한국어 실행 가능한 조언');
	lines.push(
		'- priority: "high" | "medium" | "low" 중 하나 (데이터 기반)',
	);
	lines.push("", "마크다운/코드펜스/설명 없이 순수 JSON만 반환.");
	return lines.join("\n");
}

export function parseInsightResponse(raw) {
	if (raw == null) return null;
	let candidate = raw;
	if (typeof raw === "string") {
		const text = raw.trim();
		if (text.length === 0) return null;
		const stripped = text
			.replace(/^```(?:json)?\s*/i, "")
			.replace(/```\s*$/i, "")
			.trim();
		try {
			candidate = JSON.parse(stripped);
		} catch {
			return null;
		}
	}
	const arr = Array.isArray(candidate)
		? candidate
		: Array.isArray(candidate?.insights)
			? candidate.insights
			: null;
	if (!arr) return null;
	const sanitized = arr
		.map((item) => {
			if (!item || typeof item !== "object") return null;
			const title = clampString(item.title, 24);
			const body = clampString(item.body, 120);
			if (!title || !body) return null;
			const priorityRaw =
				typeof item.priority === "string"
					? item.priority.toLowerCase()
					: "medium";
			const priority = VALID_PRIORITIES.has(priorityRaw)
				? priorityRaw
				: "medium";
			return { title, body, priority };
		})
		.filter(Boolean)
		.slice(0, MAX_INSIGHTS);
	return sanitized.length > 0 ? sanitized : null;
}

export function buildHeuristicInsights(input) {
	const s = summarizeFarmForInsight(input);
	const candidates = [];

	if (s.shipmentCandidates > 0) {
		const tagSuffix = s.topShipment?.tag ? ` ${s.topShipment.tag}호` : "";
		const margin = s.topShipment?.marginManwon ?? 0;
		const marginText = margin > 0 ? ` (예상 +${margin}만원)` : "";
		candidates.push({
			title: "즉시 출하 권장",
			body: `${s.shipmentCandidates}두 출하 적령기 도달${tagSuffix}${marginText}. 24시간 내 출고 일정을 확정해 주세요.`,
			priority: "high",
		});
	}

	if (s.notificationCounts.estrus > 0) {
		candidates.push({
			title: "발정 적기 임박",
			body: `발정 알림 ${s.notificationCounts.estrus}건. 발견 후 12~18시간 내 수정 적기, 오늘 안에 처치 일정을 잡아 주세요.`,
			priority: "high",
		});
	}

	if (s.notificationCounts.calving > 0) {
		candidates.push({
			title: "분만 임박 개체 확인",
			body: `분만 알림 ${s.notificationCounts.calving}건. 산방 청결·보온·요오드 소독 준비를 점검해 주세요.`,
			priority: "high",
		});
	}

	if (s.thi !== null && s.thi >= 78) {
		candidates.push({
			title: "고온 스트레스 경고",
			body: `THI ${s.thi}로 스트레스 구간. 환기·미스트팬을 가동하고 급수기를 4회 이상 점검해 주세요.`,
			priority: "high",
		});
	}

	if (s.decliningMarginCount > 0) {
		candidates.push({
			title: "추가 비육 마진 점검",
			body: `${s.decliningMarginCount}두는 추가 비육 시 마진 감소 예상. 단가·증체 추세를 재검토해 주세요.`,
			priority: "medium",
		});
	}

	if (s.monthlySalesCount > 0) {
		candidates.push({
			title: "이번 달 출하 요약",
			body: `${s.monthlySalesCount}두 출하·판매액 ${s.monthlySalesManwon}만원. 다음 달 출하 후보군 미리 확정.`,
			priority: "low",
		});
	}

	if (s.thi !== null && s.thi < 72) {
		candidates.push({
			title: "사양 컨디션 안정",
			body: `THI ${s.thi}로 활동 적합 구간. 사료 증량·체중 측정 데이터 갱신에 적합한 시점.`,
			priority: "low",
		});
	}

	if (s.totalHeadcount === 0) {
		candidates.push({
			title: "개체 등록부터 시작",
			body: "등록된 개체가 없습니다. 좌측 메뉴에서 개체 등록을 먼저 진행해 주세요.",
			priority: "medium",
		});
	}

	const safeDefaults = [
		{
			title: "오늘의 점검 루틴",
			body: "발정·분만·사료·물·축사 환기 5가지 일상 점검을 진행해 주세요.",
			priority: "low",
		},
		{
			title: "데이터 보강 안내",
			body: "체중·판매액·시세 데이터를 갱신하면 더 정확한 인사이트를 제공합니다.",
			priority: "low",
		},
		{
			title: "다음 주 일정 확인",
			body: "백신·검진·번식 등 다음 주 일정을 미리 캘린더에서 확인해 주세요.",
			priority: "low",
		},
	];
	const existingTitles = new Set(candidates.map((c) => c.title));
	for (const fallback of safeDefaults) {
		if (candidates.length >= MAX_INSIGHTS) break;
		if (!existingTitles.has(fallback.title)) {
			candidates.push(fallback);
			existingTitles.add(fallback.title);
		}
	}

	candidates.sort(
		(a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority],
	);
	return candidates.slice(0, MAX_INSIGHTS);
}
