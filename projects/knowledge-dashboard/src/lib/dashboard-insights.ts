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
      title: "Focus mode",
      description: `Charts and recommendations are narrowed to "${query}" only.`,
      tone: "blue",
    });
  }

  if (
    repoCount > 0 &&
    unspecifiedLanguageCount > 0 &&
    unspecifiedLanguageShare >= INSIGHT_THRESHOLDS.metadataGapBadge
  ) {
    badges.push({
      title: "Metadata gap",
      description: `${round(unspecifiedLanguageShare)}% of visible repositories are missing language metadata.`,
      tone: "amber",
    });
  }

  if (
    repoCount >= 3 &&
    dominantLanguage &&
    dominantLanguageShare >= INSIGHT_THRESHOLDS.concentrationShare
  ) {
    badges.push({
      title: "Stack concentration",
      description: `${dominantLanguage} owns ${round(dominantLanguageShare)}% of visible repositories.`,
      tone: "amber",
    });
  } else if (repoCount >= 3 && diversityScore >= INSIGHT_THRESHOLDS.balancedDiversity) {
    badges.push({
      title: "Balanced portfolio",
      description: "The visible repository mix is broadly distributed across multiple languages.",
      tone: "emerald",
    });
  }

  if (notebookCount > 0 && avgSourcesPerNotebook >= INSIGHT_THRESHOLDS.denseReferences) {
    badges.push({
      title: "Dense references",
      description: "The average notebook already has enough source depth for richer downstream answers.",
      tone: "violet",
    });
  } else if (notebookCount > 0 && avgSourcesPerNotebook < INSIGHT_THRESHOLDS.thinReferences) {
    badges.push({
      title: "Thin references",
      description: "Several notebooks are shallow enough to reduce confidence on complex prompts.",
      tone: "rose",
    });
  }

  if (notebookCount > 0 && sourceCoverageRatio < INSIGHT_THRESHOLDS.coverageBadge) {
    badges.push({
      title: "Coverage gap",
      description: `${round(100 - sourceCoverageRatio)}% of visible notebooks still need at least one linked source.`,
      tone: "rose",
    });
  } else if (notebookCount > 0 && sourceCoverageRatio === 100) {
    badges.push({
      title: "Fully linked",
      description: "Every visible notebook has at least one linked source attached.",
      tone: "emerald",
    });
  }

  if (zeroSourceNotebookCount > 0) {
    badges.push({
      title: "Orphan notebooks",
      description: `${zeroSourceNotebookCount} notebook${zeroSourceNotebookCount > 1 ? "s are" : " is"} still empty.`,
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
      (dominantLanguageShare - INSIGHT_THRESHOLDS.healthConcentrationBaseline) * 1.4,
      0,
      35,
    );
    const metadataPenalty = clamp(
      (unspecifiedLanguageShare - INSIGHT_THRESHOLDS.healthMetadataBaseline) * 1.2,
      0,
      25,
    );
    weightedScores.push({
      weight: 0.45,
      score: clamp(diversityScore - concentrationPenalty - metadataPenalty, 0, 100),
    });
  }

  if (notebookCount > 0) {
    weightedScores.push({
      weight: 0.35,
      score: sourceCoverageRatio,
    });
    weightedScores.push({
      weight: 0.20,
      score: clamp((avgSourcesPerNotebook / 5) * 100, 0, 100),
    });
  }

  if (weightedScores.length === 0) {
    return 0;
  }

  const totalWeight = weightedScores.reduce((sum, item) => sum + item.weight, 0);
  const weightedAverage = weightedScores.reduce((sum, item) => sum + item.weight * item.score, 0);

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
      title: "Backfill repository metadata",
      description: "Too many repositories are missing language metadata, so the dashboard can misread stack balance until sync quality improves.",
      metricLabel: "Unknown language",
      metricValue: `${round(unspecifiedLanguageShare)}%`,
      tone: "amber",
    });
  }

  if (zeroSourceNotebookCount > 0) {
    actions.push({
      priority: "now",
      title: "Attach sources to empty notebooks",
      description: "Notebooks with zero references are the fastest way to improve answer quality and reduce dead-end knowledge hubs.",
      metricLabel: "Orphan notebooks",
      metricValue: `${zeroSourceNotebookCount}`,
      tone: "rose",
    });
  }

  if (notebookCount > 0 && sourceCoverageRatio < INSIGHT_THRESHOLDS.coverageAction) {
    actions.push({
      priority: zeroSourceNotebookCount > 0 ? "next" : "now",
      title: "Raise notebook coverage",
      description: "Prioritize linking at least one source to each visible notebook before adding more long-tail content.",
      metricLabel: "Coverage",
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
      title: "Diversify the visible stack",
      description: `The current slice leans heavily on ${dominantLanguage}. Adding or surfacing adjacent stacks will reduce concentration risk.`,
      metricLabel: "Dominant share",
      metricValue: `${round(dominantLanguageShare)}%`,
      tone: "violet",
    });
  }

  if (notebookCount > 0 && avgSourcesPerNotebook < INSIGHT_THRESHOLDS.deepenAverageSources) {
    actions.push({
      priority: actions.length === 0 ? "now" : "next",
      title: "Deepen notebook references",
      description: "Move the average source depth above 3 so insight generation has enough supporting material.",
      metricLabel: "Avg sources",
      metricValue: `${round(avgSourcesPerNotebook)}`,
      tone: "blue",
    });
  }

  if (query && totalItems > 0) {
    actions.push({
      priority: "watch",
      title: "Review this filtered slice",
      description: "Search mode is showing a narrower portfolio. Validate whether this slice needs its own curation rule or tagging shortcut.",
      metricLabel: "Visible items",
      metricValue: `${totalItems}`,
      tone: "blue",
    });
  }

  if (actions.length === 0) {
    actions.push({
      priority: "watch",
      title: "Maintain the current balance",
      description: "The visible portfolio is in a healthy range. Preserve coverage and diversity as new items are added.",
      metricLabel: "Health score",
      metricValue: `${healthScore}`,
      tone: "emerald",
    });
  }

  if (actions.length < 3) {
    actions.push({
      priority: "watch",
      title: "Monitor language balance",
      description: diversityScore >= INSIGHT_THRESHOLDS.balancedDiversity
        ? "The language mix is healthy now, so watch new additions for hidden concentration drift."
        : "Small language skew can compound quickly. Re-check balance when the next batch of repositories lands.",
      metricLabel: "Diversity",
      metricValue: `${round(diversityScore)}`,
      tone: diversityScore >= INSIGHT_THRESHOLDS.balancedDiversity ? "emerald" : "amber",
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
  const totalSources = safeNotebooks.reduce((sum, notebook) => sum + notebook.source_count, 0);
  const sourceCounts = safeNotebooks.map((notebook) => notebook.source_count);
  const notebooksWithSources = sourceCounts.filter((count) => count > 0).length;
  const zeroSourceNotebookCount = sourceCounts.filter((count) => count === 0).length;
  const diversityScore = calculateDiversityScore(rawCounts);
  const dominantLanguageEntry = languageData.find(
    (entry) => entry.name !== "Other" && entry.name !== "Unspecified",
  );
  const dominantLanguage = dominantLanguageEntry?.name ?? null;
  const dominantLanguageShare = dominantLanguageEntry?.share ?? 0;
  const avgSourcesPerNotebook = safeNotebooks.length > 0 ? totalSources / safeNotebooks.length : 0;
  const sourceCoverageRatio = safeNotebooks.length > 0
    ? (notebooksWithSources / safeNotebooks.length) * 100
    : 0;
  const unspecifiedLanguageShare = safeRepos.length > 0
    ? (unspecifiedCount / safeRepos.length) * 100
    : 0;
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
