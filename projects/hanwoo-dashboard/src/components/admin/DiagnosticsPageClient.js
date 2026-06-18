"use client";

import { Activity, ArrowLeft, Cpu, Database } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAppFeedback } from "@/components/feedback/FeedbackProvider";
import { getRawData, getSystemDiagnostics } from "@/lib/actions";
import { toFiniteNumber } from "@/lib/utils";

const STATUS_STYLES = {
	good: {
		accent: "var(--chart-clay-1)",
		background:
			"color-mix(in srgb, var(--chart-clay-1) 18%, var(--color-surface-elevated))",
	},
	bad: {
		accent: "var(--chart-clay-4)",
		background:
			"color-mix(in srgb, var(--chart-clay-4) 18%, var(--color-surface-elevated))",
	},
	neutral: {
		accent: "var(--chart-clay-5)",
		background:
			"color-mix(in srgb, var(--chart-clay-5) 18%, var(--color-surface-elevated))",
	},
};

const RETRY_MESSAGE = "잠시 후 다시 시도해 주세요.";
const DIAGNOSTICS_LOAD_ERROR_MESSAGE =
	"진단 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.";
const RAW_DATA_LOAD_ERROR_MESSAGE =
	"원본 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.";
const DASHBOARD_NAVIGATION_ERROR_MESSAGE =
	"대시보드로 이동하지 못했습니다. 잠시 후 다시 시도해 주세요.";
const RAW_DATA_UNAVAILABLE_TITLE = "원본 데이터를 표시할 수 없습니다.";
const EMPTY_RAW_DATA_MESSAGE =
	"선택한 원본 데이터에 표시할 레코드가 없습니다.";
const DATABASE_UNAVAILABLE_RAW_DATA_MESSAGE =
	"DB 연결 실패 상태에서는 원본 조회를 다시 시도할 수 없습니다.";

const MODEL_OPTIONS = [
	{ value: "cattle", label: "개체" },
	{ value: "salesRecord", label: "출하 기록" },
	{ value: "feedRecord", label: "급여 기록" },
	{ value: "scheduleEvent", label: "일정" },
	{ value: "inventoryItem", label: "재고" },
	{ value: "building", label: "축사" },
	{ value: "farmSettings", label: "농장 설정" },
];

const EMPTY_DIAGNOSTICS = {
	success: false,
	database: {
		status: "DB 상태 확인 불가",
		latency: "DB 응답 시간 확인 불가",
		recordCounts: {},
	},
	nodeVersion: "Node 버전 확인 불가",
	uptime: 0,
	memory: {
		heapUsed: 0,
		heapTotal: 0,
	},
};

function deferDiagnosticsTask(callback) {
	try {
		queueMicrotask(callback);
	} catch {
		Promise.resolve().then(callback);
	}
}

function normalizeDiagnosticsObject(value) {
	return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function normalizeDiagnosticsStats(value) {
	const safeValue = normalizeDiagnosticsObject(value);
	const safeDatabase = normalizeDiagnosticsObject(safeValue.database);
	const safeMemory = normalizeDiagnosticsObject(safeValue.memory);

	return {
		...EMPTY_DIAGNOSTICS,
		...safeValue,
		database: {
			...EMPTY_DIAGNOSTICS.database,
			...safeDatabase,
			recordCounts: normalizeDiagnosticsObject(safeDatabase.recordCounts),
		},
		memory: {
			...EMPTY_DIAGNOSTICS.memory,
			...safeMemory,
		},
	};
}

function normalizeDiagnosticsMessage(value) {
	return typeof value === "string" && value.trim() ? value : RETRY_MESSAGE;
}

function normalizeStatusCardOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function hasRenderableRawData(value) {
	if (Array.isArray(value)) {
		return value.length > 0;
	}

	if (value && typeof value === "object") {
		return Object.keys(value).length > 0;
	}

	return value !== null && value !== undefined && value !== "";
}

export default function DiagnosticsPageClient() {
	const router = useRouter();
	const { notify } = useAppFeedback();
	const [stats, setStats] = useState(null);
	const [loading, setLoading] = useState(true);
	const [selectedModel, setSelectedModel] = useState("cattle");
	const [rawData, setRawData] = useState(null);
	const [rawDataErrorMessage, setRawDataErrorMessage] = useState(null);
	const [dataLoading, setDataLoading] = useState(true);
	const diagnosticsRequestRef = useRef(0);
	const rawDataRequestRef = useRef(0);

	const recordCounts = useMemo(
		() =>
			stats?.database?.recordCounts
				? Object.entries(stats.database.recordCounts).map(([key, value]) => [
						key,
						toFiniteNumber(value),
					])
				: [],
		[stats],
	);
	const isDatabaseAvailable = stats?.success === true;
	const rawDataNoteId = "diagnostics-raw-data-note";
	const hasRawDataPayload = hasRenderableRawData(rawData);
	const rawDataPreview = hasRawDataPayload
		? JSON.stringify(rawData, null, 2)
		: "";
	const uptimeMinutes = Math.floor(toFiniteNumber(stats?.uptime) / 60);
	const heapUsedMb = Math.round(
		toFiniteNumber(stats?.memory?.heapUsed) / 1024 / 1024,
	);
	const heapTotalMb = Math.round(
		toFiniteNumber(stats?.memory?.heapTotal) / 1024 / 1024,
	);
	const handleDashboardReturn = () => {
		try {
			router.push("/");
		} catch (error) {
			console.error("Failed to navigate from diagnostics to dashboard:", error);
			notify({
				title: "대시보드로 이동하지 못했습니다.",
				description: DASHBOARD_NAVIGATION_ERROR_MESSAGE,
				variant: "error",
			});
		}
	};

	useEffect(() => {
		let cancelled = false;
		const requestId = ++diagnosticsRequestRef.current;
		deferDiagnosticsTask(() => {
			if (!cancelled && requestId === diagnosticsRequestRef.current) {
				setLoading(true);
			}
		});

		void (async () => {
			try {
				const result = await getSystemDiagnostics();
				if (cancelled || requestId !== diagnosticsRequestRef.current) {
					return;
				}

				setStats(normalizeDiagnosticsStats(result));
			} catch (error) {
				if (cancelled || requestId !== diagnosticsRequestRef.current) {
					return;
				}

				console.error("Failed to load system diagnostics:", error);
				setStats(EMPTY_DIAGNOSTICS);
				notify({
					title: "진단 정보를 불러오지 못했습니다.",
					description: DIAGNOSTICS_LOAD_ERROR_MESSAGE,
					variant: "error",
				});
			} finally {
				if (!cancelled && requestId === diagnosticsRequestRef.current) {
					setLoading(false);
				}
			}
		})();

		return () => {
			cancelled = true;
		};
	}, [notify]);

	useEffect(() => {
		if (loading) {
			return;
		}

		if (!isDatabaseAvailable) {
			deferDiagnosticsTask(() => {
				setDataLoading(false);
				setRawData(null);
				setRawDataErrorMessage(DATABASE_UNAVAILABLE_RAW_DATA_MESSAGE);
			});
			return;
		}

		let cancelled = false;
		const requestId = ++rawDataRequestRef.current;
		deferDiagnosticsTask(() => {
			if (!cancelled && requestId === rawDataRequestRef.current) {
				setDataLoading(true);
				setRawData(null);
				setRawDataErrorMessage(null);
			}
		});

		void (async () => {
			try {
				const result = await getRawData(selectedModel);
				if (cancelled || requestId !== rawDataRequestRef.current) {
					return;
				}

				const safeResult = normalizeDiagnosticsObject(result);
				if (safeResult.success) {
					setRawData(safeResult.data ?? null);
					setRawDataErrorMessage(null);
				} else {
					const message = normalizeDiagnosticsMessage(safeResult.message);
					setRawData(null);
					setRawDataErrorMessage(message);
					notify({
						title: "원본 데이터를 불러오지 못했습니다.",
						description: message,
						variant: "error",
					});
				}
			} catch (error) {
				if (cancelled || requestId !== rawDataRequestRef.current) {
					return;
				}

				console.error("Failed to load raw diagnostics data:", error);
				setRawData(null);
				setRawDataErrorMessage(RAW_DATA_LOAD_ERROR_MESSAGE);
				notify({
					title: "원본 데이터를 불러오지 못했습니다.",
					description: RAW_DATA_LOAD_ERROR_MESSAGE,
					variant: "error",
				});
			} finally {
				if (!cancelled && requestId === rawDataRequestRef.current) {
					setDataLoading(false);
				}
			}
		})();

		return () => {
			cancelled = true;
		};
	}, [isDatabaseAvailable, loading, notify, selectedModel]);

	if (loading) {
		return (
			<main className="clay-shell" id="main-content">
				<div
					className="clay-page-card p-8 text-center"
					role="status"
					aria-live="polite"
					aria-atomic="true"
					aria-busy="true"
				>
					<div className="clay-page-eyebrow mb-4">운영 진단</div>
					<h1 className="clay-page-title mb-3">
						시스템 상태를 확인하고 있습니다
					</h1>
					<p className="clay-page-subtitle">
						데이터베이스 연결과 런타임 상태를 점검하는 중입니다.
					</p>
				</div>
			</main>
		);
	}

	return (
		<main className="clay-shell" id="main-content">
			<div className="clay-page-card p-6 md:p-8">
				<div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
					<div className="max-w-2xl">
						<div className="clay-page-eyebrow mb-4">운영 진단</div>
						<h1 className="clay-page-title mb-3">시스템 상태 점검</h1>
						<p className="clay-page-subtitle">
							데이터베이스 연결, 메모리 사용량, 원본 레코드를 한 화면에서
							확인합니다.
						</p>
					</div>

					<button
						type="button"
						onClick={handleDashboardReturn}
						aria-label="운영 대시보드로 돌아가기"
						title="운영 대시보드로 돌아가기"
						className="clay-pressable inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold text-[color:var(--color-text)]"
					>
						<ArrowLeft className="h-4 w-4" aria-hidden="true" />
						대시보드로 돌아가기
					</button>
				</div>

				<div className="mb-6 grid gap-4 md:grid-cols-3">
					<StatusCard
						title="데이터베이스 상태"
						value={stats.database.status}
						sub={stats.database.latency}
						icon={<Database className="h-5 w-5" />}
						status={stats.success ? "good" : "bad"}
					/>
					<StatusCard
						title="Node.js 런타임"
						value={stats.nodeVersion}
						sub={`가동 ${uptimeMinutes}분`}
						icon={<Cpu className="h-5 w-5" />}
						status="neutral"
					/>
					<StatusCard
						title="메모리 사용량"
						value={`${heapUsedMb} MB`}
						sub={`전체 ${heapTotalMb} MB`}
						icon={<Activity className="h-5 w-5" />}
						status="neutral"
					/>
				</div>

				<section className="clay-page-section mb-6 p-5 md:p-6">
					<div className="mb-4 flex items-center justify-between gap-4">
						<div>
							<div className="clay-page-eyebrow mb-3">데이터 원장</div>
							<h2 className="text-xl font-bold text-[color:var(--color-text)]">
								테이블별 레코드 현황
							</h2>
						</div>
						<div className="clay-stat-chip">{recordCounts.length}개 모델</div>
					</div>

					<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
						{recordCounts.map(([key, value]) => (
							<div
								key={key}
								className="clay-inset rounded-[22px] p-4"
								style={{ borderColor: "var(--color-surface-stroke)" }}
							>
								<div className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-[color:var(--color-text-muted)]">
									{key}
								</div>
								<div
									className="text-3xl font-bold"
									style={{
										color: "var(--color-primary-custom)",
										fontFamily: "var(--font-display-custom)",
									}}
								>
									{value}
								</div>
							</div>
						))}
					</div>
				</section>

				<section className="clay-page-section p-5 md:p-6">
					<div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
						<div>
							<div className="clay-page-eyebrow mb-3">원본 데이터</div>
							<h2 className="text-xl font-bold text-[color:var(--color-text)]">
								레코드 검사기
							</h2>
						</div>

						<select
							aria-label="검사할 원본 데이터 선택"
							aria-describedby={rawDataNoteId}
							title="검사할 원본 데이터 선택"
							value={selectedModel}
							onChange={(event) => setSelectedModel(event.target.value)}
							disabled={!isDatabaseAvailable || dataLoading}
							className="clay-inset rounded-full px-4 py-3 text-sm font-medium text-[color:var(--color-text)] outline-none"
						>
							{MODEL_OPTIONS.map((option) => (
								<option key={option.value} value={option.value}>
									{option.label}
								</option>
							))}
						</select>
					</div>
					<p
						id={rawDataNoteId}
						className="mb-4 text-xs font-medium text-[color:var(--color-text-muted)]"
					>
						{isDatabaseAvailable
							? "모델을 바꾸면 최신 50개 원본 레코드를 다시 조회합니다."
							: DATABASE_UNAVAILABLE_RAW_DATA_MESSAGE}
					</p>

					{dataLoading ? (
						<div
							className="clay-inset rounded-[24px] px-6 py-14 text-center text-sm text-[color:var(--color-text-muted)]"
							role="status"
							aria-live="polite"
							aria-atomic="true"
							aria-busy="true"
						>
							레코드를 불러오는 중입니다.
						</div>
					) : rawDataErrorMessage ? (
						<div
							className="clay-inset rounded-[24px] px-6 py-14 text-center text-sm text-[color:var(--color-text-muted)]"
							role="status"
							aria-live="polite"
							aria-atomic="true"
						>
							<p className="mb-2 font-semibold text-[color:var(--color-text)]">
								{RAW_DATA_UNAVAILABLE_TITLE}
							</p>
							<p>{rawDataErrorMessage}</p>
						</div>
					) : !hasRawDataPayload ? (
						<div
							className="clay-inset rounded-[24px] px-6 py-14 text-center text-sm text-[color:var(--color-text-muted)]"
							role="status"
							aria-live="polite"
							aria-atomic="true"
						>
							{EMPTY_RAW_DATA_MESSAGE}
						</div>
					) : (
						<div className="clay-console h-96 overflow-auto p-5 text-sm leading-6">
							<pre className="m-0 whitespace-pre-wrap break-all">
								{rawDataPreview}
							</pre>
						</div>
					)}
				</section>
			</div>
		</main>
	);
}

function StatusCard(options = {}) {
	const { title, value, sub, icon, status } =
		normalizeStatusCardOptions(options);
	const style = STATUS_STYLES[status] || STATUS_STYLES.neutral;

	return (
		<div
			className="rounded-[26px] border p-5"
			style={{
				background: style.background,
				borderColor:
					"color-mix(in srgb, var(--color-surface-stroke) 84%, transparent)",
				boxShadow: "var(--shadow-sm)",
			}}
		>
			<div className="mb-3 flex items-center justify-between">
				<span className="text-sm font-semibold text-[color:var(--color-text-secondary)]">
					{title}
				</span>
				<span
					className="inline-flex h-10 w-10 items-center justify-center rounded-full"
					style={{
						background: `color-mix(in srgb, ${style.accent} 16%, white 84%)`,
						color: style.accent,
					}}
				>
					{icon}
				</span>
			</div>
			<div
				className="mb-1 text-3xl font-bold text-[color:var(--color-text)]"
				style={{ fontFamily: "var(--font-display-custom)" }}
			>
				{value}
			</div>
			<div className="text-xs font-medium text-[color:var(--color-text-muted)]">
				{sub}
			</div>
		</div>
	);
}
