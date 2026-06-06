"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ReceiptText } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import {
	Bar,
	BarChart,
	Legend,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import EmptyState from "@/components/ui/empty-state";
import { PremiumButton } from "@/components/ui/premium-button";
import { PremiumCard, PremiumCardContent } from "@/components/ui/premium-card";
import {
	PremiumInput,
	PremiumLabel,
	PremiumSelect,
} from "@/components/ui/premium-input";
import MarketPriceWidget from "@/components/widgets/MarketPriceWidget";
import { createSalesFormValues, salesFormSchema } from "@/lib/formSchemas";
import { focusElementSafely } from "@/lib/safeFocus";
import { formatMoney, toFiniteNumber } from "@/lib/utils";

const errorTextStyle = {
	fontSize: "12px",
	marginTop: "6px",
	color: "var(--color-danger)",
	fontWeight: 600,
};

function getSaleDateTime(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime())
		? Number.NEGATIVE_INFINITY
		: date.getTime();
}

function normalizeSalesItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) => item && typeof item === "object" && !Array.isArray(item),
			)
		: [];
}

function normalizeSalesTabOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeSalesPaginationOptions(pagination) {
	return pagination && typeof pagination === "object" && !Array.isArray(pagination)
		? pagination
		: {};
}

export default function SalesTab(options = {}) {
	const {
		saleRecords,
		cattleList,
		onCreateSale,
		expenseRecords = [],
		initialMarketPrice = null,
		salesPagination = null,
		quickActionIntent = null,
	} = normalizeSalesTabOptions(options);
	const handleCreateSale =
		typeof onCreateSale === "function" ? onCreateSale : async () => false;
	const safeSalesPagination = normalizeSalesPaginationOptions(salesPagination);
	const handleLoadMoreSales =
		typeof safeSalesPagination.loadMore === "function"
			? safeSalesPagination.loadMore
			: () => {};
	const [isAdding, setIsAdding] = useState(
		() => quickActionIntent?.actionId === "record-sale",
	);
	const [isSaving, setIsSaving] = useState(false);
	const isMountedRef = useRef(false);
	const salesFormRef = useRef(null);
	const saleDateInputRef = useRef(null);
	const saveInFlightRef = useRef(false);

	const {
		register,
		handleSubmit,
		reset,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(salesFormSchema),
		defaultValues: createSalesFormValues(),
	});
	const saleDateRegistration = register("saleDate");

	const safeSaleRecords = useMemo(
		() => normalizeSalesItems(saleRecords),
		[saleRecords],
	);
	const safeCattleList = useMemo(
		() => normalizeSalesItems(cattleList),
		[cattleList],
	);
	const safeExpenseRecords = useMemo(
		() => normalizeSalesItems(expenseRecords),
		[expenseRecords],
	);

	const processedRecords = useMemo(() => {
		return [...safeSaleRecords]
			.map((record) => {
				const cow =
					safeCattleList.find((item) => item.id === record.cattleId) || {};
				const cattleExpenses = safeExpenseRecords.filter(
					(expense) => expense.cattleId === record.cattleId,
				);
				const salePrice = toFiniteNumber(record.price);
				const purchaseCost = toFiniteNumber(cow.purchasePrice);
				const feedCost = cattleExpenses
					.filter((expense) => expense.category === "feed")
					.reduce((sum, expense) => sum + toFiniteNumber(expense.amount), 0);
				const medicalCost = cattleExpenses
					.filter((expense) => expense.category === "medicine")
					.reduce((sum, expense) => sum + toFiniteNumber(expense.amount), 0);
				const otherCost = cattleExpenses
					.filter(
						(expense) =>
							expense.category !== "feed" && expense.category !== "medicine",
					)
					.reduce((sum, expense) => sum + toFiniteNumber(expense.amount), 0);
				const totalCost = purchaseCost + feedCost + medicalCost + otherCost;
				const hasExpenseData = cattleExpenses.length > 0 || purchaseCost > 0;

				return {
					...record,
					name: cow.name || "개체명 미등록",
					tagNumber: cow.tagNumber || "이력번호 미등록",
					costs: {
						purchase: purchaseCost,
						feed: feedCost,
						medical: medicalCost,
						other: otherCost,
						total: totalCost,
					},
					price: salePrice,
					profit: hasExpenseData ? salePrice - totalCost : null,
					hasExpenseData,
				};
			})
			.sort(
				(first, second) =>
					getSaleDateTime(second.saleDate) - getSaleDateTime(first.saleDate),
			);
	}, [safeSaleRecords, safeCattleList, safeExpenseRecords]);

	const safeTotalSales = useMemo(
		() =>
			processedRecords.reduce(
				(sum, record) => sum + toFiniteNumber(record.price),
				0,
			),
		[processedRecords],
	);

	const safeTotalProfit = useMemo(() => {
		const recordsWithProfit = processedRecords.filter(
			(record) => record.profit !== null,
		);
		return recordsWithProfit.reduce(
			(sum, record) => sum + toFiniteNumber(record.profit),
			0,
		);
	}, [processedRecords]);

	const safeChartData = useMemo(
		() =>
			processedRecords
				.slice(0, 5)
				.reverse()
				.map((record) => ({
					name: record.name,
					saleAmount: record.price,
					profit: record.profit ?? 0,
				})),
		[processedRecords],
	);
	const loadMoreLabel = safeSalesPagination.isLoading
		? "이전 판매 기록 불러오는 중"
		: "이전 판매 기록 더 보기";
	const submitButtonLabel = isSaving
		? "판매 기록 등록 중"
		: "판매 기록 등록";
	const submitButtonText = isSaving
		? "판매 기록 등록 중..."
		: "판매 기록 등록";
	const addFormButtonLabel = isSaving
		? "판매 기록 저장 중에는 등록 창을 닫을 수 없습니다"
		: isAdding
			? "판매 기록 등록 취소"
			: "판매 기록 등록 창 열기";
	const addFormButtonText = isSaving
		? "판매 기록 저장 중..."
		: isAdding
			? "판매 기록 등록 취소"
			: "판매 기록 등록";
	const salesProfitChartLabel =
		"최근 5건 수익 분석 차트. 판매금액과 수익을 출하 개체별로 비교합니다.";

	useEffect(() => {
		isMountedRef.current = true;

		return () => {
			isMountedRef.current = false;
			saveInFlightRef.current = false;
		};
	}, []);

	useEffect(() => {
		if (quickActionIntent?.actionId === "record-sale") {
			setIsAdding(true);
		}
	}, [quickActionIntent?.actionId, quickActionIntent?.nonce]);

	useEffect(() => {
		if (!isAdding) {
			return;
		}

		const timeoutId = window.setTimeout(() => {
			try {
				salesFormRef.current?.scrollIntoView({
					behavior: "smooth",
					block: "start",
					inline: "nearest",
				});
			} catch {
				salesFormRef.current?.scrollIntoView();
			}

			focusElementSafely(saleDateInputRef.current);
		}, 0);

		return () => {
			window.clearTimeout(timeoutId);
		};
	}, [isAdding, quickActionIntent?.nonce]);

	const toggleAddForm = () => {
		if (saveInFlightRef.current || isSaving) {
			return;
		}

		const next = !isAdding;
		setIsAdding(next);

		if (!next) {
			setIsSaving(false);
			reset(createSalesFormValues());
		}
	};

	const submitSale = async (values) => {
		if (saveInFlightRef.current) {
			return;
		}

		saveInFlightRef.current = true;
		setIsSaving(true);

		try {
			const saved = await handleCreateSale(values);
			if (!saved || !isMountedRef.current) {
				return;
			}

			setIsAdding(false);
			reset(createSalesFormValues());
		} finally {
			saveInFlightRef.current = false;
			if (isMountedRef.current) {
				setIsSaving(false);
			}
		}
	};

	const handleSaleSubmit = (event) => {
		void handleSubmit(submitSale)(event);
	};

	return (
		<div>
			<MarketPriceWidget initialData={initialMarketPrice} />

			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
					marginBottom: "14px",
				}}
			>
				<div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
					<span aria-hidden="true" style={{ fontSize: "20px", lineHeight: 1 }}>
						💰
					</span>
					<span
						style={{
							fontSize: "17px",
							fontWeight: 800,
							color: "var(--color-text)",
							letterSpacing: "-0.01em",
						}}
					>
						출하 및 판매 분석
					</span>
				</div>
				<PremiumButton
					variant="outline"
					size="sm"
					onClick={toggleAddForm}
					disabled={isSaving}
					aria-busy={isSaving}
					aria-label={addFormButtonLabel}
					title={addFormButtonLabel}
					className="text-[13px] text-green-400 border-green-500/50 hover:bg-green-500/10 px-3 py-1.5 rounded-lg font-bold"
				>
					{addFormButtonText}
				</PremiumButton>
			</div>

			{isAdding ? (
				<form ref={salesFormRef} onSubmit={handleSaleSubmit} className="mb-4">
					<PremiumCard className="bg-slate-800/60 w-full mb-4">
						<PremiumCardContent className="p-4">
							<div
								style={{
									fontSize: "14px",
									fontWeight: 700,
									marginBottom: "12px",
								}}
							>
								새 판매 기록 등록
							</div>
							<div style={{ display: "grid", gap: "10px" }}>
								<div>
									<PremiumLabel htmlFor="sale-date">출하일자</PremiumLabel>
									<PremiumInput
										id="sale-date"
										type="date"
										{...saleDateRegistration}
										ref={(element) => {
											saleDateRegistration.ref(element);
											saleDateInputRef.current = element;
										}}
										aria-invalid={Boolean(errors.saleDate)}
										aria-describedby={
											errors.saleDate ? "sale-date-error" : undefined
										}
										hasError={!!errors.saleDate}
									/>
									{errors.saleDate ? (
										<div
											id="sale-date-error"
											role="alert"
											style={errorTextStyle}
										>
											{errors.saleDate.message}
										</div>
									) : null}
								</div>

								<div>
									<PremiumLabel htmlFor="sale-price">
										판매 가격 (원)
									</PremiumLabel>
									<PremiumInput
										id="sale-price"
										type="number"
										{...register("price")}
										placeholder="예: 8500000"
										aria-invalid={Boolean(errors.price)}
										aria-describedby={
											errors.price ? "sale-price-error" : undefined
										}
										hasError={!!errors.price}
									/>
									{errors.price ? (
										<div
											id="sale-price-error"
											role="alert"
											style={errorTextStyle}
										>
											{errors.price.message}
										</div>
									) : null}
								</div>

								<div>
									<PremiumLabel htmlFor="sale-cattle">출하 개체</PremiumLabel>
									<PremiumSelect
										id="sale-cattle"
										{...register("cattleId")}
										aria-invalid={Boolean(errors.cattleId)}
										aria-describedby={
											errors.cattleId ? "sale-cattle-error" : undefined
										}
										hasError={!!errors.cattleId}
									>
										<option value="" className="bg-slate-900">
											선택해 주세요
										</option>
										{safeCattleList.map((cow) => (
											<option
												key={cow.id}
												value={cow.id}
												className="bg-slate-900"
											>
												{cow.name} ({cow.tagNumber})
											</option>
										))}
									</PremiumSelect>
									{errors.cattleId ? (
										<div
											id="sale-cattle-error"
											role="alert"
											style={errorTextStyle}
										>
											{errors.cattleId.message}
										</div>
									) : null}
								</div>

								<div
									style={{
										display: "grid",
										gridTemplateColumns: "1fr 1fr",
										gap: "10px",
									}}
								>
									<div>
										<PremiumLabel htmlFor="sale-grade">등급</PremiumLabel>
										<PremiumSelect
											id="sale-grade"
											{...register("grade")}
											aria-invalid={Boolean(errors.grade)}
											aria-describedby={
												errors.grade ? "sale-grade-error" : undefined
											}
											hasError={!!errors.grade}
										>
											<option value="1++" className="bg-slate-900">
												1++
											</option>
											<option value="1+" className="bg-slate-900">
												1+
											</option>
											<option value="1" className="bg-slate-900">
												1
											</option>
											<option value="2" className="bg-slate-900">
												2
											</option>
											<option value="3" className="bg-slate-900">
												3
											</option>
										</PremiumSelect>
										{errors.grade ? (
											<div
												id="sale-grade-error"
												role="alert"
												style={errorTextStyle}
											>
												{errors.grade.message}
											</div>
										) : null}
									</div>

									<div>
										<PremiumLabel htmlFor="sale-purchaser">구매처</PremiumLabel>
										<PremiumInput
											id="sale-purchaser"
											{...register("purchaser")}
											placeholder="예: 남원축협"
											aria-invalid={Boolean(errors.purchaser)}
											aria-describedby={
												errors.purchaser ? "sale-purchaser-error" : undefined
											}
											hasError={!!errors.purchaser}
										/>
										{errors.purchaser ? (
											<div
												id="sale-purchaser-error"
												role="alert"
												style={errorTextStyle}
											>
												{errors.purchaser.message}
											</div>
										) : null}
									</div>
								</div>

								<PremiumButton
									type="submit"
									disabled={!safeCattleList.length || isSaving}
									aria-busy={isSaving}
									aria-label={submitButtonLabel}
									title={submitButtonLabel}
									className="w-full py-3 mt-2 rounded-lg"
									variant="primary"
									glow
								>
									{submitButtonText}
								</PremiumButton>

								{!safeCattleList.length ? (
									<div
										style={{
											fontSize: "12px",
											color: "var(--color-text-muted)",
										}}
									>
										먼저 개체를 등록해야 판매 기록을 추가할 수 있습니다.
									</div>
								) : null}
							</div>
						</PremiumCardContent>
					</PremiumCard>
				</form>
			) : null}

			<div
				style={{
					display: "flex",
					gap: "10px",
					overflowX: "auto",
					paddingBottom: "10px",
					marginBottom: "10px",
				}}
			>
				<PremiumCard className="bg-linear-to-br border-primary/20 flex-1 min-w-[140px] from-orange-400 to-orange-600">
					<PremiumCardContent className="p-4 text-white">
						<div style={{ fontSize: "11px", opacity: 0.7 }}>총 누적 판매액</div>
						<div
							style={{
								fontSize: "20px",
								fontWeight: 800,
								fontFamily: "'Outfit',sans-serif",
							}}
						>
							{formatMoney(safeTotalSales / 10000)}만
						</div>
					</PremiumCardContent>
				</PremiumCard>
				<PremiumCard className="flex-1 min-w-[140px]">
					<PremiumCardContent className="p-4">
						<div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
							평균 수익률
						</div>
						<div
							style={{
								fontSize: "20px",
								fontWeight: 800,
								color:
									safeTotalProfit >= 0
										? "var(--color-success)"
										: "var(--color-danger)",
								fontFamily: "'Outfit',sans-serif",
							}}
						>
							{safeTotalSales > 0
								? ((safeTotalProfit / safeTotalSales) * 100).toFixed(1)
								: 0}
							%
						</div>
					</PremiumCardContent>
				</PremiumCard>
			</div>

			<PremiumCard className="mb-4">
				<PremiumCardContent className="p-5">
					<div
						style={{
							fontSize: "13px",
							fontWeight: 700,
							marginBottom: "16px",
							color: "var(--color-text)",
						}}
					>
						최근 5건 수익 분석
					</div>
					<div
						role="img"
						aria-label={salesProfitChartLabel}
						title={salesProfitChartLabel}
						style={{ height: "200px", fontSize: "10px" }}
					>
						<ResponsiveContainer
							width="100%"
							height="100%"
							minWidth={0}
							minHeight={0}
							initialDimension={{ width: 1, height: 1 }}
						>
							<BarChart
								data={safeChartData}
								margin={{ top: 5, right: 5, left: -20, bottom: 0 }}
							>
								<XAxis dataKey="name" tickLine={false} axisLine={false} />
								<YAxis
									tickLine={false}
									axisLine={false}
									tickFormatter={(value) => `${value / 10000}`}
								/>
								<Tooltip
									contentStyle={{
										borderRadius: "8px",
										border: "none",
										boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
									}}
									formatter={(value) => `${formatMoney(value)}원`}
								/>
								<Legend />
								<Bar
									dataKey="saleAmount"
									name="판매금액"
									fill="#BCAAA4"
									radius={[4, 4, 0, 0]}
									barSize={20}
								/>
								<Bar
									dataKey="profit"
									name="수익"
									fill="var(--color-primary-light)"
									radius={[4, 4, 0, 0]}
									barSize={20}
								/>
							</BarChart>
						</ResponsiveContainer>
					</div>
				</PremiumCardContent>
			</PremiumCard>

			<div
				style={{
					fontSize: "14px",
					fontWeight: 700,
					marginBottom: "10px",
					color: "var(--color-text)",
				}}
			>
				출하 이력
			</div>
			<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
				{processedRecords.length === 0 ? (
					<EmptyState
						icon={ReceiptText}
						title="출하 내역이 없습니다"
						description={
							safeCattleList.length
								? "첫 출하 기록을 남기면 판매액, 등급, 수익 분석 차트가 바로 채워집니다."
								: "개체를 먼저 등록하면 출하 기록과 수익 분석을 연결할 수 있습니다."
						}
						actionLabel={
							safeCattleList.length
								? "판매 기록 등록"
								: "개체를 먼저 등록해 주세요"
						}
						onAction={() => setIsAdding(true)}
						disabled={!safeCattleList.length}
					/>
				) : (
					processedRecords.map((record, index) => (
						<PremiumCard key={record.id || index} className="p-0">
							<PremiumCardContent className="p-3.5">
								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
										marginBottom: "8px",
									}}
								>
									<div>
										<div style={{ fontWeight: 700, fontSize: "14px" }}>
											{record.name} ({record.grade})
										</div>
										<div
											style={{
												fontSize: "11px",
												color: "var(--color-text-muted)",
											}}
										>
											{record.tagNumber}
										</div>
									</div>
									<div style={{ textAlign: "right" }}>
										<div
											style={{
												fontWeight: 800,
												fontSize: "15px",
												color: "var(--color-primary-light)",
											}}
										>
											{formatMoney(record.price)}원
										</div>
										<div
											style={{
												fontSize: "11px",
												color: "var(--color-text-muted)",
											}}
										>
											{record.auctionLocation || record.purchaser}
										</div>
									</div>
								</div>

								<div className="bg-slate-900/30 rounded-lg p-2 flex justify-between text-xs">
									{record.hasExpenseData ? (
										<>
											<span className="text-slate-400">
												총 비용: {formatMoney(record.costs.total)}원
											</span>
											<span
												className={
													record.profit >= 0
														? "text-green-400 font-bold"
														: "text-red-400 font-bold"
												}
											>
												순수익: {record.profit >= 0 ? "+" : ""}
												{formatMoney(record.profit)}원
											</span>
										</>
									) : (
										<>
											<span className="text-slate-500 italic">연결된 비용 기록 없음</span>
											<span className="text-slate-500">비용 기록 없어 수익 추정 불가</span>
										</>
									)}
								</div>
							</PremiumCardContent>
						</PremiumCard>
					))
				)}
			</div>

			{safeSalesPagination.hasMore && (
				<>
					<PremiumButton
						variant="secondary"
						onClick={handleLoadMoreSales}
						disabled={safeSalesPagination.isLoading}
						aria-busy={safeSalesPagination.isLoading}
						aria-label={loadMoreLabel}
						title={loadMoreLabel}
						className="w-full mt-3 py-3"
					>
						{safeSalesPagination.isLoading
							? "이전 판매 기록 불러오는 중..."
							: "이전 판매 기록 더 보기"}
					</PremiumButton>
					{safeSalesPagination.loadError ? (
						<p
							role="status"
							aria-live="polite"
							aria-atomic="true"
							className="mt-2 text-center text-xs font-semibold text-red-300"
						>
							{safeSalesPagination.loadError}
						</p>
					) : null}
				</>
			)}
		</div>
	);
}
