"use client";

import { RefreshCwIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getRealTimeMarketPrice } from "@/lib/actions";
import { formatMoney } from "@/lib/utils";

function normalizePricePanelOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizePricePanelRows(rows) {
	return Array.isArray(rows) ? rows.filter((row) => Array.isArray(row)) : [];
}

function PricePanel(options = {}) {
	const { title, rows } = normalizePricePanelOptions(options);
	const visibleRows = normalizePricePanelRows(rows);

	return (
		<div className="clay-inset rounded-[24px] p-4 transition-[box-shadow,transform] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5">
			<div className="mb-3 border-b border-[color:var(--color-surface-border)] pb-3">
				<span className="text-sm font-bold text-[color:var(--color-text)] tracking-[-0.01em]">
					{title}
				</span>
			</div>
			<div className="grid gap-2.5">
				{visibleRows.map(([grade, value], index) => (
					<div
						key={`${grade ?? "price"}-${index}`}
						className="flex items-center justify-between text-sm transition-[background,transform] duration-200 rounded-lg px-2 py-1.5 -mx-2 hover:bg-[color:color-mix(in_srgb,var(--color-surface-elevated)_60%,transparent)]"
						style={{
							borderBottom:
								index === visibleRows.length - 1
									? "none"
									: "1px solid color-mix(in srgb, var(--color-surface-border) 45%, transparent)",
						}}
					>
						<span className="font-medium text-[color:var(--color-text-secondary)]">
							{grade}
						</span>
						<span className="font-bold text-[color:var(--color-text)] tabular-nums">
							kg당 {formatMoney(value)}
						</span>
					</div>
				))}
			</div>
		</div>
	);
}

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

function toValidUpdatedAt(value, fallback = new Date()) {
	if (!value) {
		return fallback;
	}

	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? fallback : date;
}

function normalizePriceSnapshot(data) {
	return data
		? {
				...data,
				bull: data.bull ?? {},
				cow: data.cow ?? {},
			}
		: data;
}

function normalizeMarketPriceWidgetOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

const MARKET_PRICE_POLL_INTERVAL_MS = 1000 * 60 * 60;

export default function MarketPriceWidget(options = {}) {
	const { initialData = null } = normalizeMarketPriceWidgetOptions(options);
	const [prices, setPrices] = useState(() =>
		normalizePriceSnapshot(initialData),
	);
	const [loading, setLoading] = useState(!initialData);
	const isMountedRef = useRef(false);
	const inFlightRequestRef = useRef(null);
	const requestSequenceRef = useRef(0);
	const [lastUpdated, setLastUpdated] = useState(() =>
		initialData ? toValidUpdatedAt(initialData.fetchedAt) : null,
	);

	const applyPriceSnapshot = useCallback((data) => {
		setPrices(normalizePriceSnapshot(data));
		setLastUpdated(toValidUpdatedAt(data?.fetchedAt));
	}, []);

	const fetchPrices = useCallback(() => {
		if (inFlightRequestRef.current) {
			return inFlightRequestRef.current;
		}

		if (!isMountedRef.current) {
			return Promise.resolve(null);
		}

		const requestId = requestSequenceRef.current + 1;
		requestSequenceRef.current = requestId;
		setLoading(true);

		const request = getRealTimeMarketPrice()
			.then((data) => {
				if (!data) {
					return data;
				}

				if (!isMountedRef.current || requestSequenceRef.current !== requestId) {
					return data;
				}

				applyPriceSnapshot(data);
				return data;
			})
			.catch((error) => {
				console.error("Failed to fetch market prices:", error);
				return null;
			})
			.finally(() => {
				if (inFlightRequestRef.current === request) {
					inFlightRequestRef.current = null;
				}

				if (isMountedRef.current && requestSequenceRef.current === requestId) {
					setLoading(false);
				}
			});

		inFlightRequestRef.current = request;
		return request;
	}, [applyPriceSnapshot]);

	useEffect(() => {
		isMountedRef.current = true;
		let refreshTimer = null;
		let interval = null;
		let fallbackPollTimer = null;

		const scheduleFallbackPolling = () => {
			try {
				fallbackPollTimer = window.setTimeout(() => {
					void fetchPrices();
					if (isMountedRef.current) {
						scheduleFallbackPolling();
					}
				}, MARKET_PRICE_POLL_INTERVAL_MS);
			} catch (error) {
				console.error("Failed to schedule market price fallback polling:", error);
			}
		};

		if (!initialData) {
			try {
				refreshTimer = window.setTimeout(() => {
					void fetchPrices();
				}, 0);
			} catch (error) {
				console.error("Failed to schedule market price refresh:", error);
				void Promise.resolve().then(() => fetchPrices());
			}
		}

		try {
			interval = window.setInterval(
				() => {
					void fetchPrices();
				},
				MARKET_PRICE_POLL_INTERVAL_MS,
			);
		} catch (error) {
			console.error("Failed to schedule market price polling:", error);
			scheduleFallbackPolling();
		}

		return () => {
			isMountedRef.current = false;
			if (refreshTimer) {
				try {
					window.clearTimeout(refreshTimer);
				} catch {}
			}
			if (interval) {
				try {
					window.clearInterval(interval);
				} catch {}
			}
			if (fallbackPollTimer) {
				try {
					window.clearTimeout(fallbackPollTimer);
				} catch {}
			}
		};
	}, [fetchPrices, initialData]);

	if (loading && !prices) {
		return (
			<Card className="animate-fadeInUp">
				<CardContent
					className="flex h-60 items-center justify-center"
					role="status"
					aria-live="polite"
					aria-atomic="true"
					aria-busy="true"
				>
					<div className="text-sm text-[color:var(--color-text-secondary)]">
						한우 시세를 불러오는 중입니다.
					</div>
				</CardContent>
			</Card>
		);
	}

	if (!prices || prices.available === false) {
		return (
			<Card className="animate-fadeInUp">
				<CardContent
					className="flex min-h-36 items-center justify-center text-center"
					role="status"
					aria-live="polite"
					aria-atomic="true"
				>
					<div className="text-sm text-[color:var(--color-text-secondary)]">
						{prices?.message ?? "지금은 한우 시세 정보를 확인할 수 없습니다."}
					</div>
				</CardContent>
			</Card>
		);
	}

	const sourcePresentation = getSourcePresentation(prices);

	return (
		<Card className="animate-fadeInUp overflow-hidden">
			<CardHeader className="pb-3">
				<div className="flex flex-wrap items-start justify-between gap-3">
					<div>
						<div className="clay-page-eyebrow mb-3">시세 흐름</div>
						<CardTitle className="text-xl font-bold text-[color:var(--color-text)]">
							한우 도매 시세
						</CardTitle>
						<p className="mt-2 text-xs text-[color:var(--color-text-secondary)]">
							{prices.date ?? "최근"} 가중평균 거래가
						</p>
					</div>

					<div className="flex items-center gap-2">
						<span
							className="inline-flex rounded-full border px-3 py-1 text-[11px] font-bold"
							style={sourcePresentation.style}
						>
							{sourcePresentation.label}
						</span>
						<button
							type="button"
							onClick={() => {
								void fetchPrices();
							}}
							disabled={loading}
							aria-busy={loading}
							aria-label={
								loading ? "한우 시세 갱신 중" : "한우 시세 새로고침"
							}
							title={loading ? "한우 시세 갱신 중" : "한우 시세 새로고침"}
							className="clay-pressable inline-flex h-10 w-10 items-center justify-center rounded-full text-[color:var(--color-text-secondary)]"
						>
							<RefreshCwIcon
								aria-hidden="true"
								className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
							/>
						</button>
					</div>
				</div>
			</CardHeader>

			<CardContent>
				<div className="grid gap-3 md:grid-cols-2">
					<PricePanel
						title="수소 kg당 시세"
						rows={[
							["1++ 등급", prices.bull.grade1pp],
							["1+ 등급", prices.bull.grade1p],
							["1 등급", prices.bull.grade1],
						]}
					/>
					<PricePanel
						title="암소 kg당 시세"
						rows={[
							["1++ 등급", prices.cow.grade1pp],
							["1+ 등급", prices.cow.grade1p],
							["1 등급", prices.cow.grade1],
						]}
					/>
				</div>

				{prices.message ? (
					<div className="mt-4 rounded-[18px] border border-[color:var(--color-surface-border)] bg-[color:var(--color-surface-muted)] px-4 py-3 text-xs text-[color:var(--color-text-secondary)]">
						{prices.message}
					</div>
				) : null}

				{lastUpdated ? (
					<div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-[11px] text-[color:var(--color-text-muted)]">
						<span>마지막 갱신 {lastUpdated.toLocaleTimeString()}</span>
						<span>데이터 출처: KAPE</span>
					</div>
				) : null}
			</CardContent>
		</Card>
	);
}
