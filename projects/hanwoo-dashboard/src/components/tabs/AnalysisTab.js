"use client";

import { DollarSign, TrendingDown, TrendingUp } from "lucide-react";
import { useMemo } from "react";
import {
	Bar,
	BarChart,
	CartesianGrid,
	Cell,
	Legend,
	Pie,
	PieChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import { formatMoney, toFiniteNumber } from "@/lib/utils";
import { ProfitabilityWidget } from "@/components/widgets/ProfitabilityWidget";

const GRADE_ORDER = ["1++", "1+", "1", "2", "3", "D"];
const MARKET_GRADE_MAP = { "1++": "grade1pp", "1+": "grade1p", "1": "grade1" };

function getMarketPriceForGrade(marketPrice, grade, gender) {
	if (!marketPrice) return null;
	const key = MARKET_GRADE_MAP[grade];
	if (!key) return null;
	const isBull = typeof gender === "string" && gender.includes("수");
	const tier = isBull ? marketPrice.bull : marketPrice.cow;
	return tier?.[key] ?? null;
}

const CATEGORY_CONFIG = {
	feed: { name: "사료비", color: "var(--chart-clay-2)" },
	medicine: { name: "약품/진료", color: "var(--chart-clay-4)" },
	labor: { name: "인건비", color: "var(--chart-clay-1)" },
	other: { name: "기타", color: "var(--chart-clay-5)" },
};

const RANK_COLORS = [
	"var(--chart-clay-2)",
	"var(--chart-clay-5)",
	"var(--chart-clay-4)",
];

function toMonthKey(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	if (Number.isNaN(date.getTime())) {
		return null;
	}

	if (typeof value === "string") {
		const dateKey = value.trim().slice(0, 10);
		if (/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) {
			const strictDate = new Date(`${dateKey}T00:00:00.000Z`);
			if (
				Number.isNaN(strictDate.getTime()) ||
				strictDate.toISOString().slice(0, 10) !== dateKey
			) {
				return null;
			}
		}
	}

	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function normalizeAnalysisItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) => item && typeof item === "object" && !Array.isArray(item),
			)
		: [];
}

function normalizeKpiCardOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeAnalysisTabOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export default function AnalysisTab(options = {}) {
	const {
		saleRecords = [],
		feedHistory = [],
		cattleList = [],
		expenseRecords = [],
		marketPrice = null,
		profitability = null,
		isPremium = true,
	} = normalizeAnalysisTabOptions(options);
	const safeSaleRecords = useMemo(
		() => normalizeAnalysisItems(saleRecords),
		[saleRecords],
	);
	const safeFeedHistory = useMemo(
		() => normalizeAnalysisItems(feedHistory),
		[feedHistory],
	);
	const safeCattleList = useMemo(
		() => normalizeAnalysisItems(cattleList),
		[cattleList],
	);
	const safeExpenseRecords = useMemo(
		() => normalizeAnalysisItems(expenseRecords),
		[expenseRecords],
	);
	const hasExpenseData = safeExpenseRecords.length > 0;
	const monthlyFlowChartLabel =
		"최근 12개월 월별 판매액, 비용, 수익 추이 차트입니다.";
	const costStructureChartLabel =
		"비용 구성 분석 차트. 카테고리별 비용 비중을 비교합니다.";

	const monthlyData = useMemo(() => {
		const data = {};
		const today = new Date();

		for (let index = 11; index >= 0; index -= 1) {
			const date = new Date(today.getFullYear(), today.getMonth() - index, 1);
			const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
			data[key] = { name: key, revenue: 0, cost: 0, profit: 0 };
		}

		safeSaleRecords.forEach((record) => {
			const key = toMonthKey(record.saleDate);
			if (data[key]) data[key].revenue += toFiniteNumber(record.price);
		});

		safeExpenseRecords.forEach((expense) => {
			const key = toMonthKey(expense.date);
			if (data[key]) data[key].cost += toFiniteNumber(expense.amount);
		});

		Object.keys(data).forEach((key) => {
			data[key].profit = data[key].revenue - data[key].cost;
		});

		return Object.values(data);
	}, [safeSaleRecords, safeExpenseRecords]);

	const costStructure = useMemo(() => {
		if (!hasExpenseData) return [];

		const totals = {};
		safeExpenseRecords.forEach((expense) => {
			const category = expense.category || "other";
			totals[category] =
				(totals[category] || 0) + toFiniteNumber(expense.amount);
		});

		return Object.entries(totals).map(([category, amount]) => ({
			name: CATEGORY_CONFIG[category]?.name || category,
			value: amount,
			color: CATEGORY_CONFIG[category]?.color || "var(--color-text-muted)",
		}));
	}, [safeExpenseRecords, hasExpenseData]);

	const topSales = useMemo(
		() =>
			[...safeSaleRecords]
				.sort(
					(first, second) =>
						toFiniteNumber(second.price) - toFiniteNumber(first.price),
				)
				.slice(0, 5),
		[safeSaleRecords],
	);

	const cattleMap = useMemo(
		() => new Map(safeCattleList.map((c) => [c.id, c])),
		[safeCattleList],
	);

	const gradeStats = useMemo(() => {
		const gradedSales = safeSaleRecords.filter((s) => s.grade);
		if (gradedSales.length === 0) return [];

		const counts = {};
		gradedSales.forEach((s) => {
			counts[s.grade] = (counts[s.grade] || 0) + 1;
		});
		const total = gradedSales.length;

		return GRADE_ORDER.filter((g) => counts[g]).map((grade) => ({
			grade,
			count: counts[grade],
			pct: Math.round((counts[grade] / total) * 100),
		}));
	}, [safeSaleRecords]);

	const recentGradedSales = useMemo(() => {
		return [...safeSaleRecords]
			.filter((s) => s.grade && MARKET_GRADE_MAP[s.grade])
			.sort((a, b) => {
				const diff =
					new Date(b.saleDate).getTime() - new Date(a.saleDate).getTime();
				return Number.isNaN(diff) ? 0 : diff;
			})
			.slice(0, 3)
			.map((sale) => {
				const cattle = cattleMap.get(sale.cattleId);
				const weight = cattle?.weight;
				const gender = cattle?.gender;
				const pricePerKg =
					weight > 0 ? Math.round(toFiniteNumber(sale.price) / weight) : null;
				const marketPricePerKg = getMarketPriceForGrade(
					marketPrice,
					sale.grade,
					gender,
				);
				return {
					id: sale.id,
					saleDate: sale.saleDate,
					grade: sale.grade,
					cattleName: sale.cattle?.name || cattle?.name,
					price: sale.price,
					weight,
					pricePerKg,
					marketPricePerKg,
					diff:
						pricePerKg && marketPricePerKg ? pricePerKg - marketPricePerKg : null,
				};
			});
	}, [safeSaleRecords, cattleMap, marketPrice]);

	const totalRevenue = monthlyData.reduce((sum, row) => sum + row.revenue, 0);
	const totalCost = monthlyData.reduce((sum, row) => sum + row.cost, 0);
	const totalProfit = totalRevenue - totalCost;
	const margin =
		totalRevenue > 0 ? ((totalProfit / totalRevenue) * 100).toFixed(1) : "0.0";
	const monthlyAverageFeed = safeFeedHistory.length
		? Math.round(
				safeFeedHistory.reduce(
					(sum, row) =>
						sum +
						toFiniteNumber(row.roughage) +
						toFiniteNumber(row.concentrate),
					0,
				) / safeFeedHistory.length,
			)
		: 0;

	return (
		<div className="animate-fadeIn">
			<div className="mb-5 flex items-center gap-3">
				<div className="clay-page-eyebrow">경영 분석</div>
				<div className="clay-stat-chip">두수 {safeCattleList.length}두</div>
				<div className="clay-stat-chip">월평균 급여 {monthlyAverageFeed}kg</div>
			</div>

			<div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<KpiCard
					title="연간 총판매액"
					value={totalRevenue}
					accent="var(--chart-clay-5)"
					icon={<DollarSign size={18} />}
				/>
				<KpiCard
					title="연간 총비용"
					value={totalCost}
					accent="var(--chart-clay-2)"
					icon={<TrendingDown size={18} />}
				/>
				<KpiCard
					title="연간 순이익"
					value={totalProfit}
					accent="var(--chart-clay-1)"
					icon={<TrendingUp size={18} />}
				/>
				<KpiCard
					title="이익률"
					value={`${margin}%`}
					accent={
						totalProfit >= 0 ? "var(--chart-clay-1)" : "var(--chart-clay-4)"
					}
				/>
			</div>

			<section className="clay-page-section mb-6 p-5 md:p-6">
				<div className="mb-4 flex items-center justify-between gap-4">
					<div>
						<div className="clay-page-eyebrow mb-3">월별 흐름</div>
						<h2 className="text-xl font-bold text-[color:var(--color-text)]">
							월별 판매액 · 비용 · 순이익 추이
						</h2>
					</div>
					<div className="text-right text-xs text-[color:var(--color-text-muted)]">
						최근 12개월 기준
					</div>
				</div>

				<div
					className="h-[320px]"
					role="img"
					aria-label={monthlyFlowChartLabel}
					title={monthlyFlowChartLabel}
				>
					<ResponsiveContainer
						width="100%"
						height="100%"
						minWidth={0}
						minHeight={0}
						initialDimension={{ width: 1, height: 1 }}
					>
						<BarChart data={monthlyData}>
							<CartesianGrid
								strokeDasharray="3 3"
								vertical={false}
								stroke="color-mix(in srgb, var(--color-surface-border) 68%, transparent)"
							/>
							<XAxis
								dataKey="name"
								axisLine={false}
								tickLine={false}
								tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
							/>
							<YAxis
								axisLine={false}
								tickLine={false}
								tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
								tickFormatter={(value) => `${Math.round(value / 10000)}만`}
							/>
							<Tooltip
								formatter={(value) => `${formatMoney(value)}원`}
								contentStyle={{
									borderRadius: 18,
									border: "1px solid var(--color-surface-stroke)",
									boxShadow: "var(--shadow-md)",
									background: "var(--surface-gradient)",
								}}
							/>
							<Legend />
							<Bar
								dataKey="revenue"
								name="판매액"
								fill="var(--chart-clay-1)"
								radius={[8, 8, 0, 0]}
							/>
							<Bar
								dataKey="cost"
								name="비용"
								fill="var(--chart-clay-2)"
								radius={[8, 8, 0, 0]}
							/>
							<Bar
								dataKey="profit"
								name="순이익"
								fill="var(--chart-clay-5)"
								radius={[8, 8, 0, 0]}
							/>
						</BarChart>
					</ResponsiveContainer>
				</div>
			</section>

			<div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
				<section className="clay-page-section p-5 md:p-6">
					<div className="mb-4 flex items-center justify-between gap-4">
						<div>
							<div className="clay-page-eyebrow mb-3">비용 구성</div>
							<h2 className="text-xl font-bold text-[color:var(--color-text)]">
								비용 구조 분석
							</h2>
						</div>
						<div className="text-right text-xs text-[color:var(--color-text-muted)]">
							{hasExpenseData
								? `${costStructure.length}개 카테고리`
								: "실제 비용 기록 없음"}
						</div>
					</div>

					{costStructure.length > 0 ? (
						<div
							className="h-[280px]"
							role="img"
							aria-label={costStructureChartLabel}
							title={costStructureChartLabel}
						>
							<ResponsiveContainer
								width="100%"
								height="100%"
								minWidth={0}
								minHeight={0}
								initialDimension={{ width: 1, height: 1 }}
							>
								<PieChart>
									<Pie
										data={costStructure}
										cx="50%"
										cy="50%"
										innerRadius={62}
										outerRadius={92}
										paddingAngle={4}
										dataKey="value"
									>
										{costStructure.map((entry) => (
											<Cell key={entry.name} fill={entry.color} />
										))}
									</Pie>
									<Tooltip
										formatter={(value) => `${formatMoney(value)}원`}
										contentStyle={{
											borderRadius: 18,
											border: "1px solid var(--color-surface-stroke)",
											boxShadow: "var(--shadow-md)",
											background: "var(--surface-gradient)",
										}}
									/>
									<Legend />
								</PieChart>
							</ResponsiveContainer>
						</div>
					) : (
						<div className="clay-inset flex h-[280px] items-center justify-center rounded-[24px] px-6 text-center text-sm text-[color:var(--color-text-muted)]">
							비용 기록이 아직 충분히 쌓이지 않았습니다.
						</div>
					)}
				</section>

				<section className="clay-page-section p-5 md:p-6">
					<div className="mb-4 flex items-center justify-between gap-4">
						<div>
							<div className="clay-page-eyebrow mb-3">상위 판매</div>
							<h2 className="text-xl font-bold text-[color:var(--color-text)]">
								최고가 판매 이력
							</h2>
						</div>
						<div className="text-right text-xs text-[color:var(--color-text-muted)]">
							상위 5건
						</div>
					</div>

					<div role="list" aria-label="상위 출하 목록" className="grid gap-3">
						{topSales.length > 0 ? (
							topSales.map((sale, index) => (
								<div
									key={sale.id}
									role="listitem"
									className="clay-inset flex items-center justify-between gap-3 rounded-[22px] p-4"
								>
									<div className="flex min-w-0 items-center gap-3">
										<div
											className="flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold text-white"
											style={{
												background:
													RANK_COLORS[index] || "var(--color-primary-custom)",
											}}
										>
											{index + 1}
										</div>
										<div className="min-w-0">
											<div className="truncate text-sm font-bold text-[color:var(--color-text)]">
												{sale.cattle?.name || "개체명 미등록"}
											</div>
											<div className="truncate text-xs text-[color:var(--color-text-muted)]">
												{sale.purchaser}
											</div>
										</div>
									</div>
									<div className="text-right text-sm font-bold text-[color:var(--color-text)]">
										{formatMoney(sale.price)}원
									</div>
								</div>
							))
						) : (
							<div className="clay-inset rounded-[24px] px-6 py-12 text-center text-sm text-[color:var(--color-text-muted)]">
								판매 기록이 아직 없습니다.
							</div>
						)}
					</div>
				</section>
			</div>

			{(gradeStats.length > 0 || marketPrice) && (
				<section className="clay-page-section mt-6 p-5 md:p-6">
					<div className="mb-4 flex items-center justify-between gap-4">
						<div>
							<div className="clay-page-eyebrow mb-3">시세 비교</div>
							<h2 className="text-xl font-bold text-[color:var(--color-text)]">
								출하 단가 vs. 시장 시세
							</h2>
						</div>
						{marketPrice?.date && (
							<div className="text-right text-xs text-[color:var(--color-text-muted)]">
								KAPE 기준 {marketPrice.date}
							</div>
						)}
					</div>

					<div className="grid gap-4 sm:grid-cols-2">
						<div>
							<div className="mb-3 text-xs font-semibold tracking-[0.08em] text-[color:var(--color-text-muted)]">
								등급별 출하 비중
							</div>
							{gradeStats.length > 0 ? (
								<div className="grid gap-2">
									{gradeStats.map(({ grade, count, pct }) => (
										<div
											key={grade}
											className="clay-inset flex items-center gap-3 rounded-[18px] px-4 py-3"
										>
											<div
												className="flex h-8 w-12 items-center justify-center rounded-lg text-xs font-bold text-white"
												style={{ background: "var(--color-primary-custom)" }}
											>
												{grade}
											</div>
											<div className="flex-1">
												<div className="mb-1 h-1.5 overflow-hidden rounded-full bg-[color:var(--color-surface-border)]">
													<div
														className="h-full rounded-full"
														style={{
															width: `${pct}%`,
															background: "var(--chart-clay-1)",
														}}
													/>
												</div>
											</div>
											<div className="text-right text-sm font-bold tabular-nums text-[color:var(--color-text)]">{pct}%</div>
											<div className="text-right text-xs text-[color:var(--color-text-muted)]">{count}건</div>
										</div>
									))}
								</div>
							) : (
								<div className="clay-inset rounded-[24px] px-6 py-10 text-center text-sm text-[color:var(--color-text-muted)]">
									등급 기록이 없습니다.
								</div>
							)}
						</div>

						<div>
							<div className="mb-3 text-xs font-semibold tracking-[0.08em] text-[color:var(--color-text-muted)]">
								최근 출하 단가 비교
							</div>
							{recentGradedSales.length > 0 ? (
								<div className="grid gap-2">
									{recentGradedSales.map((sale) => (
										<div key={sale.id} className="clay-inset rounded-[18px] px-4 py-3">
											<div className="mb-1 flex items-center justify-between gap-2">
												<span className="text-sm font-bold text-[color:var(--color-text)]">{sale.cattleName || "미등록"}</span>
												<span
													className="rounded-full px-2 py-0.5 text-[11px] font-bold"
													style={{
														background: "color-mix(in srgb, var(--chart-clay-1) 16%, white 84%)",
														color: "var(--chart-clay-1)",
													}}
												>
													{sale.grade} 등급
												</span>
											</div>
											{sale.pricePerKg && sale.marketPricePerKg ? (
												<div className="flex items-end justify-between gap-2 text-xs">
													<div>
														<div className="text-[color:var(--color-text-muted)]">출하 단가</div>
														<div className="text-base font-bold tabular-nums text-[color:var(--color-text)]">{formatMoney(sale.pricePerKg)}원/kg</div>
													</div>
													<div className="text-center">
														<div className="text-sm font-bold" style={{ color: sale.diff > 0 ? "var(--chart-clay-1)" : "var(--chart-clay-2)" }}>
															{sale.diff > 0 ? "+" : ""}{formatMoney(sale.diff)}원
														</div>
														<div className="text-[color:var(--color-text-muted)]">시세 대비</div>
													</div>
													<div className="text-right">
														<div className="text-[color:var(--color-text-muted)]">KAPE 시세</div>
														<div className="text-base font-bold tabular-nums text-[color:var(--color-text-muted)]">{formatMoney(sale.marketPricePerKg)}원/kg</div>
													</div>
												</div>
											) : sale.pricePerKg ? (
												<div className="text-xs text-[color:var(--color-text-muted)]">
													출하 단가 {formatMoney(sale.pricePerKg)}원/kg{!marketPrice && " · 시세 데이터 없음"}
												</div>
											) : (
												<div className="text-xs text-[color:var(--color-text-muted)]">
													총 {formatMoney(sale.price)}원{!sale.weight && " · 체중 미등록 (kg당 단가 계산 불가)"}
												</div>
											)}
										</div>
									))}
								</div>
							) : (
								<div className="clay-inset rounded-[24px] px-6 py-10 text-center text-sm text-[color:var(--color-text-muted)]">
									{safeSaleRecords.length === 0 ? "출하 기록이 없습니다." : "1·1+·1++ 등급 출하 기록이 없습니다."}
								</div>
							)}
						</div>
					</div>
				</section>
			)}

			<ProfitabilityWidget
				data={profitability?.data}
				error={profitability?.error}
				meta={profitability?.meta ?? null}
				isPremium={isPremium}
			/>
		</div>
	);
}

function KpiCard(options = {}) {
	const { title, value, icon, accent } = normalizeKpiCardOptions(options);

	return (
		<div className="clay-page-section p-4">
			<div className="mb-3 flex items-center justify-between gap-3">
				<span className="text-xs font-semibold tracking-[0.08em] text-[color:var(--color-text-muted)]">
					{title}
				</span>
				{icon ? (
					<span
						className="inline-flex h-9 w-9 items-center justify-center rounded-full"
						aria-hidden="true"
						style={{
							color: accent,
							background: `color-mix(in srgb, ${accent} 16%, white 84%)`,
						}}
					>
						{icon}
					</span>
				) : null}
			</div>
			<div
				className="text-3xl font-bold text-[color:var(--color-text)]"
				style={{ fontFamily: "var(--font-display-custom)" }}
			>
				{typeof value === "number" ? `${formatMoney(value)}원` : value}
			</div>
		</div>
	);
}
