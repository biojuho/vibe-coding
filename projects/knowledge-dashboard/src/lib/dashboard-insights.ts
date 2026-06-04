export interface GithubRepoLike {
	language: string | null;
	stargazers_count?: number;
}

export interface NotebookLike {
	title: string;
	source_count: number;
}

export interface LanguageDatum {
	name: string;
	value: number;
	share: number;
}

export interface NotebookDatum {
	name: string;
	sources: number;
	fullTitle: string;
}

export interface InsightBadge {
	title: string;
	description: string;
	tone: "blue" | "emerald" | "amber" | "rose" | "violet";
}

export interface RecommendedAction {
	priority: "now" | "next" | "watch";
	title: string;
	description: string;
	metricLabel: string;
	metricValue: string;
	tone: "blue" | "emerald" | "amber" | "rose" | "violet";
}

export interface DashboardInsights {
	languageData: LanguageDatum[];
	notebookData: NotebookDatum[];
	badges: InsightBadge[];
	actions: RecommendedAction[];
	summary: {
		repoCount: number;
		notebookCount: number;
		languageCount: number;
		totalSources: number;
		avgSourcesPerNotebook: number;
		medianSourcesPerNotebook: number;
		sourceCoverageRatio: number;
		diversityScore: number;
		dominantLanguage: string | null;
		dominantLanguageShare: number;
		zeroSourceNotebookCount: number;
		unspecifiedLanguageCount: number;
		unspecifiedLanguageShare: number;
		healthScore: number;
	};
}

const LANGUAGE_LIMIT = 5;
const NOTEBOOK_LIMIT = 5;
// Centralize the heuristic thresholds so review and tuning happen in one place.
const INSIGHT_THRESHOLDS = {
	metadataGapBadge: 35,
	metadataGapAction: 30,
	concentrationShare: 65,
	balancedDiversity: 70,
	denseReferences: 5,
	thinReferences: 2,
	coverageBadge: 75,
	coverageAction: 80,
	deepenAverageSources: 3,
	healthConcentrationBaseline: 45,
	healthMetadataBaseline: 20,
} as const;

function round(value: number, digits = 1) {
	const factor = 10 ** digits;
	return Math.round(value * factor) / factor;
}

function clamp(value: number, min: number, max: number) {
	return Math.min(Math.max(value, min), max);
}

function truncateLabel(value: string, maxLength = 18) {
	if (value.length <= maxLength) {
		return value;
	}

	return `${value.slice(0, maxLength - 3)}...`;
}

function calculateMedian(values: number[]) {
	if (values.length === 0) {
		return 0;
	}

	const sorted = [...values].sort((a, b) => a - b);
	const midpoint = Math.floor(sorted.length / 2);

	if (sorted.length % 2 === 0) {
		return (sorted[midpoint - 1] + sorted[midpoint]) / 2;
	}

	return sorted[midpoint];
}

function calculateDiversityScore(counts: number[]) {
	if (counts.length <= 1) {
		return 0;
	}

	const total = counts.reduce((sum, count) => sum + count, 0);
	if (total === 0) {
		return 0;
	}

	// Normalized Shannon entropy keeps the score stable even when the
	// number of visible languages changes with search filtering.
	const entropy = counts.reduce((sum, count) => {
		if (count === 0) {
			return sum;
		}

		const probability = count / total;
		return sum - probability * Math.log(probability);
	}, 0);

	return round((entropy / Math.log(counts.length)) * 100);
}

function buildLanguageData(repos: GithubRepoLike[]) {
	const counts = new Map<string, number>();

	for (const repo of repos) {
		const language = repo.language?.trim() || "Unspecified";
		counts.set(language, (counts.get(language) ?? 0) + 1);
	}

	const total = repos.length;
	const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
	const head = sorted.slice(0, LANGUAGE_LIMIT);
	const tail = sorted.slice(LANGUAGE_LIMIT);

	const data: LanguageDatum[] = head.map(([name, value]) => ({
		name,
		value,
		share: total > 0 ? round((value / total) * 100) : 0,
	}));

	if (tail.length > 0) {
		const otherValue = tail.reduce((sum, [, value]) => sum + value, 0);
		data.push({
			name: "Other",
			value: otherValue,
			share: total > 0 ? round((otherValue / total) * 100) : 0,
		});
	}

	return {
		data,
		distinctCount: sorted.length,
		rawCounts: sorted.map(([, value]) => value),
		unspecifiedCount: counts.get("Unspecified") ?? 0,
	};
}

function buildNotebookData(notebooks: NotebookLike[]) {
	return [...notebooks]
		.sort((a, b) => b.source_count - a.source_count)
		.slice(0, NOTEBOOK_LIMIT)
		.map((notebook) => ({
			name: truncateLabel(notebook.title),
			sources: notebook.source_count,
			fullTitle: notebook.title,
		}));
}

function buildInsightBadges({
	repoCount,
	notebookCount,
	diversityScore,
	dominantLanguage,
	dominantLanguageShare,
	avgSourcesPerNotebook,
	sourceCoverageRatio,
	zeroSourceNotebookCount,
	unspecifiedLanguageCount,
	unspecifiedLanguageShare,
	query,
}: {
	repoCount: number;
	notebookCount: number;
	diversityScore: number;
	dominantLanguage: string | null;
	dominantLanguageShare: number;
	avgSourcesPerNotebook: number;
	sourceCoverageRatio: number;
	zeroSourceNotebookCount: number;
	unspecifiedLanguageCount: number;
	unspecifiedLanguageShare: number;
	query?: string;
}) {
	const badges: InsightBadge[] = [];

	if (query) {
		badges.push({
			title: "집중 모드",
			description: `차트와 추천이 "${query}" 항목으로만 좁혀졌습니다.`,
			tone: "blue",
		});
	}

	if (
		repoCount > 0 &&
		unspecifiedLanguageCount > 0 &&
		unspecifiedLanguageShare >= INSIGHT_THRESHOLDS.metadataGapBadge
	) {
		badges.push({
			title: "메타데이터 누락",
			description: `표시된 저장소의 ${round(unspecifiedLanguageShare)}%에 언어 메타데이터가 없습니다.`,
			tone: "amber",
		});
	}

	if (
		repoCount >= 3 &&
		dominantLanguage &&
		dominantLanguageShare >= INSIGHT_THRESHOLDS.concentrationShare
	) {
		badges.push({
			title: "스택 편중",
			description: `${dominantLanguage}이(가) 표시된 저장소의 ${round(dominantLanguageShare)}%를 차지합니다.`,
			tone: "amber",
		});
	} else if (
		repoCount >= 3 &&
		diversityScore >= INSIGHT_THRESHOLDS.balancedDiversity
	) {
		badges.push({
			title: "균형 잡힌 구성",
			description:
				"표시된 저장소가 여러 언어에 고르게 분포되어 있습니다.",
			tone: "emerald",
		});
	}

	if (
		notebookCount > 0 &&
		avgSourcesPerNotebook >= INSIGHT_THRESHOLDS.denseReferences
	) {
		badges.push({
			title: "풍부한 참조",
			description:
				"평균 노트북의 소스 깊이가 충분해 더 풍부한 후속 답변을 만들 수 있습니다.",
			tone: "violet",
		});
	} else if (
		notebookCount > 0 &&
		avgSourcesPerNotebook < INSIGHT_THRESHOLDS.thinReferences
	) {
		badges.push({
			title: "빈약한 참조",
			description:
				"여러 노트북의 소스가 얕아 복잡한 질문에서 신뢰도가 떨어질 수 있습니다.",
			tone: "rose",
		});
	}

	if (
		notebookCount > 0 &&
		sourceCoverageRatio < INSIGHT_THRESHOLDS.coverageBadge
	) {
		badges.push({
			title: "커버리지 부족",
			description: `표시된 노트북의 ${round(100 - sourceCoverageRatio)}%가 아직 연결된 소스가 하나도 없습니다.`,
			tone: "rose",
		});
	} else if (notebookCount > 0 && sourceCoverageRatio === 100) {
		badges.push({
			title: "모두 연결됨",
			description: "표시된 모든 노트북에 최소 한 개의 소스가 연결되어 있습니다.",
			tone: "emerald",
		});
	}

	if (zeroSourceNotebookCount > 0) {
		badges.push({
			title: "빈 노트북",
			description: `${zeroSourceNotebookCount}개 노트북이 아직 비어 있습니다.`,
			tone: "amber",
		});
	}

	return badges.slice(0, 4);
}

function calculateHealthScore({
	repoCount,
	notebookCount,
	diversityScore,
	dominantLanguageShare,
	unspecifiedLanguageShare,
	sourceCoverageRatio,
	avgSourcesPerNotebook,
}: {
	repoCount: number;
	notebookCount: number;
	diversityScore: number;
	dominantLanguageShare: number;
	unspecifiedLanguageShare: number;
	sourceCoverageRatio: number;
	avgSourcesPerNotebook: number;
}) {
	const weightedScores: Array<{ weight: number; score: number }> = [];

	if (repoCount > 0) {
		// Missing metadata should lower trust in the score, even if the visible
		// language mix looks balanced on paper.
		const concentrationPenalty = clamp(
			(dominantLanguageShare - INSIGHT_THRESHOLDS.healthConcentrationBaseline) *
				1.4,
			0,
			35,
		);
		const metadataPenalty = clamp(
			(unspecifiedLanguageShare - INSIGHT_THRESHOLDS.healthMetadataBaseline) *
				1.2,
			0,
			25,
		);
		weightedScores.push({
			weight: 0.45,
			score: clamp(
				diversityScore - concentrationPenalty - metadataPenalty,
				0,
				100,
			),
		});
	}

	if (notebookCount > 0) {
		weightedScores.push({
			weight: 0.35,
			score: sourceCoverageRatio,
		});
		weightedScores.push({
			weight: 0.2,
			score: clamp((avgSourcesPerNotebook / 5) * 100, 0, 100),
		});
	}

	if (weightedScores.length === 0) {
		return 0;
	}

	const totalWeight = weightedScores.reduce(
		(sum, item) => sum + item.weight,
		0,
	);
	const weightedAverage = weightedScores.reduce(
		(sum, item) => sum + item.weight * item.score,
		0,
	);

	return round(weightedAverage / totalWeight);
}

function buildRecommendedActions({
	repoCount,
	notebookCount,
	totalItems,
	diversityScore,
	dominantLanguage,
	dominantLanguageShare,
	avgSourcesPerNotebook,
	sourceCoverageRatio,
	zeroSourceNotebookCount,
	unspecifiedLanguageCount,
	unspecifiedLanguageShare,
	healthScore,
	query,
}: {
	repoCount: number;
	notebookCount: number;
	totalItems: number;
	diversityScore: number;
	dominantLanguage: string | null;
	dominantLanguageShare: number;
	avgSourcesPerNotebook: number;
	sourceCoverageRatio: number;
	zeroSourceNotebookCount: number;
	unspecifiedLanguageCount: number;
	unspecifiedLanguageShare: number;
	healthScore: number;
	query?: string;
}) {
	const actions: RecommendedAction[] = [];

	if (
		repoCount > 0 &&
		unspecifiedLanguageCount > 0 &&
		unspecifiedLanguageShare >= INSIGHT_THRESHOLDS.metadataGapAction
	) {
		actions.push({
			priority: "now",
			title: "저장소 메타데이터 보완",
			description:
				"언어 메타데이터가 없는 저장소가 많아, 동기화 품질이 개선되기 전까지 스택 균형을 잘못 읽을 수 있습니다.",
			metricLabel: "언어 미상",
			metricValue: `${round(unspecifiedLanguageShare)}%`,
			tone: "amber",
		});
	}

	if (zeroSourceNotebookCount > 0) {
		actions.push({
			priority: "now",
			title: "빈 노트북에 소스 연결",
			description:
				"참조가 0인 노트북부터 채우는 것이 답변 품질을 가장 빠르게 높이고 막다른 지식 허브를 줄이는 방법입니다.",
			metricLabel: "빈 노트북",
			metricValue: `${zeroSourceNotebookCount}`,
			tone: "rose",
		});
	}

	if (
		notebookCount > 0 &&
		sourceCoverageRatio < INSIGHT_THRESHOLDS.coverageAction
	) {
		actions.push({
			priority: zeroSourceNotebookCount > 0 ? "next" : "now",
			title: "노트북 커버리지 향상",
			description:
				"긴 꼬리 콘텐츠를 더 추가하기 전에, 표시된 각 노트북에 최소 한 개의 소스를 연결하세요.",
			metricLabel: "커버리지",
			metricValue: `${round(sourceCoverageRatio)}%`,
			tone: "amber",
		});
	}

	if (
		repoCount >= 3 &&
		dominantLanguage &&
		dominantLanguageShare >= INSIGHT_THRESHOLDS.concentrationShare
	) {
		actions.push({
			priority: "next",
			title: "스택 다양화",
			description: `현재 범위가 ${dominantLanguage}에 크게 치우쳐 있습니다. 인접 스택을 추가하거나 노출하면 편중 위험이 줄어듭니다.`,
			metricLabel: "주력 비중",
			metricValue: `${round(dominantLanguageShare)}%`,
			tone: "violet",
		});
	}

	if (
		notebookCount > 0 &&
		avgSourcesPerNotebook < INSIGHT_THRESHOLDS.deepenAverageSources
	) {
		actions.push({
			priority: actions.length === 0 ? "now" : "next",
			title: "노트북 참조 강화",
			description:
				"인사이트 생성에 충분한 근거가 모이도록 평균 소스 깊이를 3개 이상으로 높이세요.",
			metricLabel: "평균 소스",
			metricValue: `${round(avgSourcesPerNotebook)}`,
			tone: "blue",
		});
	}

	if (query && totalItems > 0) {
		actions.push({
			priority: "watch",
			title: "필터된 범위 검토",
			description:
				"검색 모드가 더 좁은 포트폴리오를 보여주고 있습니다. 이 범위에 별도의 큐레이션 규칙이나 태그가 필요한지 확인하세요.",
			metricLabel: "표시 항목",
			metricValue: `${totalItems}`,
			tone: "blue",
		});
	}

	if (actions.length === 0) {
		actions.push({
			priority: "watch",
			title: "현재 균형 유지",
			description:
				"표시된 포트폴리오가 건강한 범위에 있습니다. 새 항목이 추가되어도 커버리지와 다양성을 유지하세요.",
			metricLabel: "건강 점수",
			metricValue: `${healthScore}`,
			tone: "emerald",
		});
	}

	if (actions.length < 3) {
		actions.push({
			priority: "watch",
			title: "언어 균형 관찰",
			description:
				diversityScore >= INSIGHT_THRESHOLDS.balancedDiversity
					? "언어 구성이 현재 건강하니, 새 항목이 추가될 때 숨은 편중이 생기는지 관찰하세요."
					: "작은 언어 편향도 빠르게 누적될 수 있습니다. 다음 저장소 묶음이 들어오면 균형을 다시 확인하세요.",
			metricLabel: "다양성",
			metricValue: `${round(diversityScore)}`,
			tone:
				diversityScore >= INSIGHT_THRESHOLDS.balancedDiversity
					? "emerald"
					: "amber",
		});
	}

	return actions.slice(0, 3);
}

export function buildDashboardInsights(
	repos: GithubRepoLike[],
	notebooks: NotebookLike[],
	query?: string,
): DashboardInsights {
	const safeRepos = repos ?? [];
	const safeNotebooks = notebooks ?? [];
	const {
		data: languageData,
		distinctCount,
		rawCounts,
		unspecifiedCount,
	} = buildLanguageData(safeRepos);
	const notebookData = buildNotebookData(safeNotebooks);
	const totalSources = safeNotebooks.reduce(
		(sum, notebook) => sum + notebook.source_count,
		0,
	);
	const sourceCounts = safeNotebooks.map((notebook) => notebook.source_count);
	const notebooksWithSources = sourceCounts.filter((count) => count > 0).length;
	const zeroSourceNotebookCount = sourceCounts.filter(
		(count) => count === 0,
	).length;
	const diversityScore = calculateDiversityScore(rawCounts);
	const dominantLanguageEntry = languageData.find(
		(entry) => entry.name !== "Other" && entry.name !== "Unspecified",
	);
	const dominantLanguage = dominantLanguageEntry?.name ?? null;
	const dominantLanguageShare = dominantLanguageEntry?.share ?? 0;
	const avgSourcesPerNotebook =
		safeNotebooks.length > 0 ? totalSources / safeNotebooks.length : 0;
	const sourceCoverageRatio =
		safeNotebooks.length > 0
			? (notebooksWithSources / safeNotebooks.length) * 100
			: 0;
	const unspecifiedLanguageShare =
		safeRepos.length > 0 ? (unspecifiedCount / safeRepos.length) * 100 : 0;
	const roundedCoverage = round(sourceCoverageRatio);
	const roundedAverageSources = round(avgSourcesPerNotebook);
	const roundedUnspecifiedShare = round(unspecifiedLanguageShare);
	const healthScore = calculateHealthScore({
		repoCount: safeRepos.length,
		notebookCount: safeNotebooks.length,
		diversityScore,
		dominantLanguageShare,
		unspecifiedLanguageShare: roundedUnspecifiedShare,
		sourceCoverageRatio: roundedCoverage,
		avgSourcesPerNotebook: roundedAverageSources,
	});

	return {
		languageData,
		notebookData,
		badges: buildInsightBadges({
			repoCount: safeRepos.length,
			notebookCount: safeNotebooks.length,
			diversityScore,
			dominantLanguage,
			dominantLanguageShare,
			avgSourcesPerNotebook: roundedAverageSources,
			sourceCoverageRatio: roundedCoverage,
			zeroSourceNotebookCount,
			unspecifiedLanguageCount: unspecifiedCount,
			unspecifiedLanguageShare: roundedUnspecifiedShare,
			query: query?.trim(),
		}),
		actions: buildRecommendedActions({
			repoCount: safeRepos.length,
			notebookCount: safeNotebooks.length,
			totalItems: safeRepos.length + safeNotebooks.length,
			diversityScore,
			dominantLanguage,
			dominantLanguageShare,
			avgSourcesPerNotebook: roundedAverageSources,
			sourceCoverageRatio: roundedCoverage,
			zeroSourceNotebookCount,
			unspecifiedLanguageCount: unspecifiedCount,
			unspecifiedLanguageShare: roundedUnspecifiedShare,
			healthScore,
			query: query?.trim(),
		}),
		summary: {
			repoCount: safeRepos.length,
			notebookCount: safeNotebooks.length,
			languageCount: distinctCount,
			totalSources,
			avgSourcesPerNotebook: roundedAverageSources,
			medianSourcesPerNotebook: round(calculateMedian(sourceCounts)),
			sourceCoverageRatio: roundedCoverage,
			diversityScore,
			dominantLanguage,
			dominantLanguageShare: round(dominantLanguageShare),
			zeroSourceNotebookCount,
			unspecifiedLanguageCount: unspecifiedCount,
			unspecifiedLanguageShare: roundedUnspecifiedShare,
			healthScore,
		},
	};
}
