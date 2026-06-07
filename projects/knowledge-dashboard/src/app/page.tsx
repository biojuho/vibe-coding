"use client";

import {
	Book,
	Clock,
	Code,
	ExternalLink,
	FileText,
	FolderGit2,
	Layers,
	LogOut,
	PieChart,
	RefreshCw,
	Search,
	Shield,
	Smartphone,
	SquareActivity,
	X,
} from "lucide-react";
import {
	startTransition,
	useDeferredValue,
	useEffect,
	useMemo,
	useState,
} from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import ActivityTimeline from "../components/ActivityTimeline";
import DashboardCharts from "../components/DashboardCharts";
import ExportMenu from "../components/ExportMenu";
import ProductReadinessPanel from "../components/ProductReadinessPanel";
import QaQcPanel from "../components/QaQcPanel";
import {
	getApiErrorMessage,
	isDashboardDataPayload,
	isObject,
	isProductReadinessPayload,
	isQaQcPayload,
	isSkillLintPayload,
} from "@/lib/dashboard-payload";
import type { DashboardData, Notebook, TabId } from "@/lib/dashboard-types";
import {
	computeLanguageStats,
	filterDashboard,
	getDataFreshness,
	getGithubRepoDisplayName,
	getTags,
} from "@/lib/dashboard-view";

const SESSION_REQUEST_TIMEOUT_MS = 10000;

async function requestSession(
	method: "POST" | "DELETE",
	body?: { apiKey: string },
): Promise<{ response: Response; payload: unknown }> {
	const controller = new AbortController();
	const timeoutId = window.setTimeout(
		() => controller.abort(),
		SESSION_REQUEST_TIMEOUT_MS,
	);

	try {
		const response = await fetch("/api/auth/session", {
			method,
			cache: "no-store",
			signal: controller.signal,
			headers: body ? { "content-type": "application/json" } : undefined,
			body: body ? JSON.stringify(body) : undefined,
		});
		const payload = await response.json().catch(() => null);
		return { response, payload };
	} catch (error) {
		if (error instanceof DOMException && error.name === "AbortError") {
			throw new Error(
				`Session request timed out after ${SESSION_REQUEST_TIMEOUT_MS}ms.`,
			);
		}

		throw error;
	} finally {
		window.clearTimeout(timeoutId);
	}
}

async function clearSession(fallbackMessage: string) {
	const { response, payload } = await requestSession("DELETE");
	if (!response.ok) {
		throw new Error(getApiErrorMessage(payload, fallbackMessage));
	}
}

const FRESHNESS_DOT: Record<string, string> = {
	fresh: "bg-green-500",
	recent: "bg-blue-400",
	stale: "bg-amber-400",
};

function isAuthenticatedSessionPayload(value: unknown) {
	return isObject(value) && value.authenticated === true;
}

// ── Tab Component ────────────────────────────────────
function TabBar({
	activeTab,
	onTabChange,
	data,
}: {
	activeTab: TabId;
	onTabChange: (t: TabId) => void;
	data: DashboardData | null;
}) {
	const tabs: {
		id: TabId;
		label: string;
		icon: React.ReactNode;
		count?: number;
	}[] = [
		{
			id: "operations",
			label: "운영 콘솔",
			icon: <SquareActivity className="w-4 h-4" />,
			count: data?.readiness?.overall?.blocked_count,
		},
		{
			id: "knowledge",
			label: "지식 현황",
			icon: <Layers className="w-4 h-4" />,
			count: data ? data.github.length + data.notebooklm.length : 0,
		},
		{
			id: "qaqc",
			label: "QA/QC 현황",
			icon: <Shield className="w-4 h-4" />,
			// Show attention (failed), not success, so the badge matches the
			// "needs attention" semantics of the other tabs' counts.
			count: data?.qaqc?.total?.failed,
		},
		{
			id: "activity",
			label: "활동 타임라인",
			icon: <Clock className="w-4 h-4" />,
			count: data?.sessions?.length,
		},
	];

	// Roving-tabindex keyboard support per the WAI-ARIA tabs pattern: arrows move
	// between tabs (focus follows selection), Home/End jump to the ends.
	const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
		const currentIndex = tabs.findIndex((tab) => tab.id === activeTab);
		let nextIndex: number | null = null;

		if (event.key === "ArrowRight" || event.key === "ArrowDown") {
			nextIndex = (currentIndex + 1) % tabs.length;
		} else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
			nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
		} else if (event.key === "Home") {
			nextIndex = 0;
		} else if (event.key === "End") {
			nextIndex = tabs.length - 1;
		}

		if (nextIndex !== null) {
			event.preventDefault();
			const nextId = tabs[nextIndex].id;
			onTabChange(nextId);
			requestAnimationFrame(() => {
				document.getElementById(`tab-${nextId}`)?.focus();
			});
		}
	};

	return (
		<div
			role="tablist"
			aria-label="대시보드 섹션"
			onKeyDown={handleKeyDown}
			className="flex flex-wrap gap-2 bg-slate-900/60 p-1.5 rounded-xl border border-white/5 backdrop-blur-sm"
		>
			{tabs.map((tab) => {
				const selected = activeTab === tab.id;
				return (
					<button
						key={tab.id}
						type="button"
						role="tab"
						id={`tab-${tab.id}`}
						aria-selected={selected}
						aria-controls={`panel-${tab.id}`}
						tabIndex={selected ? 0 : -1}
						onClick={() => onTabChange(tab.id)}
						className={`flex min-h-11 items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 ${
							selected
								? "bg-white/10 text-white shadow-sm"
								: "text-slate-400 hover:text-slate-200 hover:bg-white/5"
						}`}
					>
						<span aria-hidden="true">{tab.icon}</span>
						{tab.label}
						{tab.count !== undefined && tab.count > 0 && (
							<span className="ml-1 text-xs bg-slate-700/80 px-1.5 py-0.5 rounded-full">
								{tab.count}
							</span>
						)}
					</button>
				);
			})}
		</div>
	);
}

function NoDataHint({ command }: { command: string }) {
	return (
		<div className="text-slate-400 text-center py-8 bg-slate-900/20 rounded-xl border border-white/5 border-dashed">
			<p className="text-sm">아직 동기화된 데이터가 없습니다.</p>
			<p className="mt-2 text-xs text-slate-500">
				<code className="bg-slate-800 px-2 py-1 rounded">{command}</code>
				를 실행해 데이터를 수집하세요.
			</p>
		</div>
	);
}

// ── Main Dashboard ───────────────────────────────────
export default function Dashboard() {
	const [data, setData] = useState<DashboardData | null>(null);
	const [loading, setLoading] = useState(true);
	const [searchTerm, setSearchTerm] = useState("");
	const [selectedNotebook, setSelectedNotebook] = useState<Notebook | null>(
		null,
	);
	const [activeTab, setActiveTab] = useState<TabId>("operations");

	const [authError, setAuthError] = useState(false);
	const [authAttempted, setAuthAttempted] = useState(false);
	const [authSubmitting, setAuthSubmitting] = useState(false);
	const [loadError, setLoadError] = useState<string | null>(null);
	const [sessionVersion, setSessionVersion] = useState(0);
	const deferredSearchTerm = useDeferredValue(searchTerm);

	useEffect(() => {
		let isActive = true;
		const controllers = new Set<AbortController>();
		startTransition(() => {
			setLoading(true);
			setLoadError(null);
		});

		// Treat transport errors and shape errors separately so the UI can
		// distinguish bad credentials from broken data.
		const fetchJson = async (url: string, timeoutMs = 15000) => {
			const controller = new AbortController();
			const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
			controllers.add(controller);

			let response: Response;
			let payload: unknown = null;

			try {
				response = await fetch(url, {
					cache: "no-store",
					signal: controller.signal,
				});
				payload = await response.json().catch(() => null);
			} catch (error) {
				if (error instanceof DOMException && error.name === "AbortError") {
					throw new Error(`Request timed out while loading ${url}.`);
				}

				throw error;
			} finally {
				window.clearTimeout(timeoutId);
				controllers.delete(controller);
			}

			if (response.status === 401) {
				throw new Error("Unauthorized");
			}

			if (!response.ok) {
				throw new Error(
					getApiErrorMessage(payload, `Request failed (${response.status})`),
				);
			}

			return payload;
		};

		void (async () => {
			try {
				const sessionPayload = await fetchJson(
					"/api/auth/session",
					SESSION_REQUEST_TIMEOUT_MS,
				);
				if (!isAuthenticatedSessionPayload(sessionPayload)) {
					if (!isActive) return;

					startTransition(() => {
						setData(null);
						setAuthError(true);
						setLoadError(null);
						setLoading(false);
					});
					return;
				}

				const dashboardPayload = await fetchJson("/api/data/dashboard");
				if (!isDashboardDataPayload(dashboardPayload)) {
					throw new Error("Dashboard payload is malformed.");
				}

				const nextData: DashboardData = { ...dashboardPayload };

				try {
					const qaqcPayload = await fetchJson("/api/data/qaqc");
					if (isQaQcPayload(qaqcPayload)) {
						nextData.qaqc = qaqcPayload;
					}
				} catch (error) {
					if (error instanceof Error && error.message === "Unauthorized") {
						throw error;
					}

					console.warn(
						"QA/QC payload could not be loaded. Continuing without it.",
						error,
					);
				}

				try {
					const readinessPayload = await fetchJson("/api/data/readiness");
					if (isProductReadinessPayload(readinessPayload)) {
						nextData.readiness = readinessPayload;
					}
				} catch (error) {
					if (error instanceof Error && error.message === "Unauthorized") {
						throw error;
					}

					console.warn(
						"Product readiness payload could not be loaded. Continuing without it.",
						error,
					);
				}

				try {
					const skillLintPayload = await fetchJson("/api/data/skills");
					if (isSkillLintPayload(skillLintPayload)) {
						nextData.skill_lint = skillLintPayload;
					}
				} catch (error) {
					if (error instanceof Error && error.message === "Unauthorized") {
						throw error;
					}

					console.warn(
						"Skill lint payload could not be loaded. Continuing without it.",
						error,
					);
				}

				if (!isActive) return;

				startTransition(() => {
					setData(nextData);
					setAuthError(false);
					setAuthAttempted(false);
					setLoadError(null);
					setLoading(false);
				});
			} catch (error) {
				if (!isActive) return;

				const unauthorized =
					error instanceof Error && error.message === "Unauthorized";
				const message =
					error instanceof Error
						? error.message
						: "Dashboard data could not be loaded.";

				startTransition(() => {
					setData(null);
					setAuthError(unauthorized);
					setLoadError(unauthorized ? null : message);
					setLoading(false);
				});
			}
		})();

		return () => {
			isActive = false;
			controllers.forEach((controller) => controller.abort());
			controllers.clear();
		};
	}, [sessionVersion]);

	// Soft refetch — re-runs the load effect without tearing down React or losing
	// the active tab / search term (unlike window.location.reload).
	const softRefresh = () => {
		if (loading) return;
		setLoadError(null);
		setSessionVersion((current) => current + 1);
	};

	const handleLogout = async () => {
		try {
			await clearSession("인증 토큰을 종료하지 못했습니다.");
			setData(null);
			setLoadError(null);
			setAuthError(true);
			setAuthAttempted(false);
		} catch (error) {
			setLoadError(
				error instanceof Error
					? error.message
					: "인증 토큰 종료에 실패했습니다.",
			);
		}
	};

	// Smart Search (delegated to the shared, tested helper).
	const filteredData = useMemo(
		() => filterDashboard(data, deferredSearchTerm),
		[data, deferredSearchTerm],
	);

	// Stats Logic — classifiedCount is the correct denominator for the language bar.
	const stats = useMemo(() => {
		if (!data) return null;
		return computeLanguageStats(filteredData.github, filteredData.notebooklm);
	}, [data, filteredData]);

	const githubCount = filteredData.github.length;
	const notebookCount = filteredData.notebooklm.length;
	const hasSearch = deferredSearchTerm.trim().length > 0;
	const freshness = data ? getDataFreshness(data.last_updated) : null;

	if (authError) {
		return (
			<div className="min-h-screen bg-[#0f172a] text-white flex items-center justify-center font-sans p-4 relative overflow-hidden">
				<div className="absolute top-0 left-0 w-[500px] h-[500px] bg-purple-600/20 blur-[120px] rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
				<Card className="w-full max-w-md bg-slate-900/60 border-white/10 backdrop-blur-md z-10 p-2">
					<CardContent className="pt-6 space-y-6">
						<div className="text-center space-y-2">
							<Shield
								className="w-12 h-12 text-blue-400 mx-auto mb-4"
								aria-hidden="true"
							/>
							<h2 className="text-2xl font-bold">인증이 필요합니다</h2>
							<p className="text-sm text-slate-400">
								대시보드 데이터를 조회하려면 API 키를 입력하세요.
							</p>
						</div>
						<form
							onSubmit={async (e) => {
								e.preventDefault();
								const fd = new FormData(e.currentTarget);
								const apiKeyInput = String(fd.get("apiKey") ?? "").trim();
								if (!apiKeyInput) {
									return;
								}

								setAuthSubmitting(true);
								setAuthAttempted(true);
								setLoadError(null);

								try {
									const { response, payload } = await requestSession("POST", {
										apiKey: apiKeyInput,
									});

									if (response.status === 401) {
										setAuthError(true);
										return;
									}

									if (!response.ok) {
										setAuthError(false);
										setLoadError(
											getApiErrorMessage(
												payload,
												"세션을 생성하지 못했습니다.",
											),
										);
										return;
									}

									setAuthError(false);
									setAuthAttempted(false);
									setLoadError(null);
									setLoading(true);
									setSessionVersion((current) => current + 1);
								} catch (error) {
									setAuthError(false);
									setLoadError(
										error instanceof Error
											? error.message
											: "세션을 생성하지 못했습니다.",
									);
								} finally {
									setAuthSubmitting(false);
								}
							}}
							className="space-y-4"
						>
							<input
								type="text"
								name="username"
								autoComplete="username"
								defaultValue="knowledge-dashboard"
								className="hidden"
								aria-hidden="true"
								tabIndex={-1}
							/>
							<Input
								name="apiKey"
								type="password"
								placeholder="DASHBOARD_API_KEY 입력..."
								aria-label="DASHBOARD_API_KEY"
								className="bg-slate-800/50 border-white/10 text-white"
								autoComplete="new-password"
								autoFocus
							/>
							{authError && authAttempted && (
								<p className="text-sm text-red-400 text-center" role="alert">
									인증에 실패했습니다. 키를 확인하세요.
								</p>
							)}
							<Button
								type="submit"
								className="w-full bg-blue-600 hover:bg-blue-500"
								disabled={authSubmitting}
							>
								인증 후 접속
							</Button>
						</form>
					</CardContent>
				</Card>
			</div>
		);
	}

	if (loadError) {
		return (
			<div className="min-h-screen bg-[#0f172a] text-white flex items-center justify-center font-sans p-4 relative overflow-hidden">
				<div className="absolute top-0 left-0 w-[500px] h-[500px] bg-blue-600/20 blur-[120px] rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
				<Card className="w-full max-w-lg bg-slate-900/60 border-white/10 backdrop-blur-md z-10 p-2">
					<CardContent className="pt-6 space-y-5">
						<div className="space-y-2 text-center">
							<Shield
								className="w-12 h-12 text-amber-400 mx-auto mb-4"
								aria-hidden="true"
							/>
							<h2 className="text-2xl font-bold text-white">
								데이터를 불러오지 못했습니다
							</h2>
							<p className="text-sm text-slate-400">
								인증은 통과했지만 대시보드 응답이 유효하지 않았습니다.
							</p>
						</div>
						<div
							className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm leading-6 text-amber-100"
							role="alert"
						>
							{loadError}
						</div>
						<div className="flex flex-col gap-3 sm:flex-row">
							<Button
								className="flex-1 bg-blue-600 hover:bg-blue-500"
								onClick={() => {
									setLoadError(null);
									setLoading(true);
									setSessionVersion((current) => current + 1);
								}}
							>
								다시 시도
							</Button>
							<Button
								variant="outline"
								className="flex-1 border-white/10 bg-white/5 hover:bg-white/10"
								onClick={async () => {
									try {
										await clearSession("기존 인증 토큰을 삭제하지 못했습니다.");
										setLoadError(null);
										setAuthError(true);
									} catch (error) {
										setLoadError(
											error instanceof Error
												? error.message
												: "인증 토큰 초기화에 실패했습니다.",
										);
									}
								}}
							>
								키 다시 입력
							</Button>
						</div>
					</CardContent>
				</Card>
			</div>
		);
	}

	return (
		<div className="min-h-screen bg-[#0f172a] text-white p-4 sm:p-6 lg:p-8 relative overflow-hidden font-sans">
			<a
				href="#main"
				className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-sm focus:text-white"
			>
				본문으로 건너뛰기
			</a>

			{/* Background Gradients */}
			<div className="absolute top-0 left-0 w-[500px] h-[500px] bg-purple-600/20 blur-[120px] rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none" />
			<div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-blue-600/20 blur-[120px] rounded-full translate-x-1/2 translate-y-1/2 pointer-events-none" />

			<main
				id="main"
				tabIndex={-1}
				className="max-w-7xl mx-auto relative z-10 space-y-8 focus:outline-none"
			>
				<header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
					<div>
						<h1 className="text-3xl sm:text-4xl font-bold bg-clip-text text-transparent bg-linear-to-r from-blue-400 to-purple-400 mb-2">
							나만의 지식 관리 대시보드
						</h1>
						<p className="text-slate-400 flex flex-wrap items-center gap-2">
							<span
								className={`w-2 h-2 rounded-full ${
									freshness ? FRESHNESS_DOT[freshness.tone] : "bg-slate-500"
								} ${freshness?.tone === "fresh" ? "animate-pulse" : ""}`}
								aria-hidden="true"
							/>
							{freshness ? freshness.label : "연결 중…"}
							{freshness && (
								<span
									className="text-xs text-slate-400 ml-1"
									title={freshness.absolute}
								>
									{freshness.relative} 동기화
								</span>
							)}
						</p>
					</div>

					<div className="flex flex-wrap items-center gap-3">
						{activeTab === "knowledge" && (
							<div className="relative group">
								<div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
									<Search className="h-4 w-4 text-slate-400 group-focus-within:text-blue-400 transition-colors" />
								</div>
								<Input
									type="text"
									aria-label="프로젝트나 노트북 검색"
									placeholder="프로젝트나 노트북 검색..."
									value={searchTerm}
									onChange={(e) => setSearchTerm(e.target.value)}
									className="pl-10 pr-9 py-2 bg-slate-800/50 border-white/10 w-full sm:w-64 placeholder:text-slate-500"
								/>
								{searchTerm && (
									<button
										type="button"
										onClick={() => setSearchTerm("")}
										aria-label="검색어 지우기"
										className="absolute inset-y-0 right-0 flex min-w-11 items-center justify-center text-slate-400 hover:text-white focus-visible:outline-none focus-visible:text-blue-400"
									>
										<X className="h-4 w-4" />
									</button>
								)}
							</div>
						)}
						{data && (
							<ExportMenu
								data={data}
								filteredGithub={filteredData.github}
								filteredNotebooks={filteredData.notebooklm}
							/>
						)}
						<Button
							variant="outline"
							onClick={softRefresh}
							disabled={loading}
							aria-label="데이터 새로고침"
							className="bg-white/5 hover:bg-white/10 border-white/10 backdrop-blur-md group"
						>
							<RefreshCw
								className={`w-4 h-4 transition-transform duration-500 ${
									loading ? "animate-spin" : "group-hover:rotate-180"
								}`}
							/>
							새로고침
						</Button>
						{data && (
							<Button
								variant="outline"
								onClick={handleLogout}
								aria-label="로그아웃"
								className="bg-white/5 hover:bg-white/10 border-white/10 backdrop-blur-md"
							>
								<LogOut className="w-4 h-4" />
								로그아웃
							</Button>
						)}
					</div>
				</header>

				{/* Tab Bar */}
				{!loading && (
					<TabBar activeTab={activeTab} onTabChange={setActiveTab} data={data} />
				)}

				{loading ? (
					<div
						className="flex items-center justify-center h-64"
						role="status"
						aria-live="polite"
					>
						<div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 motion-reduce:animate-none" />
						<span className="sr-only">대시보드 데이터를 불러오는 중…</span>
					</div>
				) : (
					<div
						role="tabpanel"
						id={`panel-${activeTab}`}
						aria-labelledby={`tab-${activeTab}`}
						tabIndex={0}
						className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 rounded-xl"
					>
						{activeTab === "operations" &&
							(data?.readiness ? (
								<ProductReadinessPanel
									data={data.readiness}
									skillLint={data.skill_lint}
								/>
							) : (
								<div className="text-center py-16 text-slate-400">
									<SquareActivity
										className="w-16 h-16 mx-auto mb-4 opacity-20"
										aria-hidden="true"
									/>
									<p className="text-lg">제품 출시 점수 데이터가 아직 없습니다</p>
									<p className="text-sm mt-2 text-slate-500">
										<code className="bg-slate-800 px-2 py-1 rounded text-xs">
											python execution/product_readiness_score.py
										</code>
										를 실행해 최신 운영 데이터를 생성하세요.
									</p>
								</div>
							))}

						{/* ── TAB: 지식 현황 ──────────────── */}
						{activeTab === "knowledge" && (
							<>
								<p role="status" aria-live="polite" className="sr-only">
									{hasSearch
										? `프로젝트 ${githubCount}개, 노트북 ${notebookCount}개 검색됨`
										: ""}
								</p>
								{stats && (
									<div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
										<Card className="bg-linear-to-br from-slate-900 via-slate-900 to-slate-800">
											<CardContent className="p-5 flex items-center gap-4">
												<div className="p-3 bg-blue-500/20 rounded-xl text-blue-400">
													<Layers className="w-6 h-6" aria-hidden="true" />
												</div>
												<div>
													<p className="text-slate-400 text-sm">연동된 자산</p>
													<div className="flex items-baseline gap-2">
														<span className="text-2xl font-bold text-white">
															{githubCount + notebookCount}
														</span>
														<span className="text-xs text-slate-400">
															Items
														</span>
													</div>
												</div>
											</CardContent>
										</Card>

										<Card className="bg-linear-to-br from-slate-900 via-slate-900 to-slate-800">
											<CardContent className="p-5 flex flex-col justify-center gap-2">
												<div className="flex items-center gap-2 mb-1">
													<PieChart
														className="w-4 h-4 text-emerald-400"
														aria-hidden="true"
													/>
													<p className="text-slate-400 text-sm">
														주요 언어 분포
													</p>
												</div>
												<div
													className="flex gap-2 h-2 w-full bg-slate-800 rounded-full overflow-hidden"
													role="img"
													aria-label={`언어 분포: ${stats.sortedLangs
														.slice(0, 3)
														.map(([lang, count]) => `${lang} ${count}개`)
														.join(", ")}`}
												>
													{stats.sortedLangs
														.slice(0, 3)
														.map(([lang, count]) => (
															<div
																key={lang}
																className={`h-full ${getLanguageColor(lang)}`}
																style={{
																	width: `${
																		stats.classifiedCount > 0
																			? (count / stats.classifiedCount) * 100
																			: 0
																	}%`,
																}}
															/>
														))}
												</div>
												<div className="flex flex-wrap gap-3 text-xs text-slate-400">
													{stats.sortedLangs
														.slice(0, 3)
														.map(([lang, count]) => (
															<span
																key={lang}
																className="flex items-center gap-1"
															>
																<div
																	className={`w-1.5 h-1.5 rounded-full ${getLanguageColor(lang)}`}
																/>
																{lang} ({count})
															</span>
														))}
												</div>
											</CardContent>
										</Card>

										<Card className="bg-linear-to-br from-slate-900 via-slate-900 to-slate-800">
											<CardContent className="p-5 flex items-center gap-4">
												<div className="p-3 bg-purple-500/20 rounded-xl text-purple-400">
													<FileText className="w-6 h-6" aria-hidden="true" />
												</div>
												<div>
													<p className="text-slate-400 text-sm">
														참조된 소스 파일
													</p>
													<div className="flex items-baseline gap-2">
														<span className="text-2xl font-bold text-white">
															{stats.totalSources}
														</span>
														<span className="text-xs text-slate-400">
															Files
														</span>
													</div>
												</div>
											</CardContent>
										</Card>
									</div>
								)}

								{data && (
									<DashboardCharts
										githubData={filteredData.github}
										notebookData={filteredData.notebooklm}
										query={deferredSearchTerm}
									/>
								)}

								<div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
									{/* GitHub Section */}
									<section className="space-y-6">
										<div className="flex items-center gap-3 mb-2">
											<div className="p-3 bg-slate-800/50 rounded-xl border border-white/5">
												<FolderGit2
													className="w-6 h-6 text-white"
													aria-hidden="true"
												/>
											</div>
											<div className="flex-1">
												<h2 className="text-2xl font-semibold">코딩 프로젝트</h2>
												<p className="text-sm text-slate-400">
													GitHub Repositories
												</p>
											</div>
											<Badge
												variant="secondary"
												className="bg-slate-800 text-slate-300 rounded-full"
											>
												{filteredData.github.length}
											</Badge>
										</div>

										<div className="grid gap-4">
											{filteredData.github.length > 0 ? (
												filteredData.github.map((repo) => {
													const repoDisplayName =
														getGithubRepoDisplayName(repo);
													return (
													<a
														key={repo.id}
														href={repo.html_url}
														target="_blank"
														rel="noopener noreferrer"
														aria-label={`${repoDisplayName} 저장소 열기 (새 탭)`}
														className="group relative block p-6 bg-slate-900/40 border border-white/5 hover:border-blue-500/30 rounded-2xl hover:bg-slate-800/40 transition-all duration-300 backdrop-blur-sm cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
													>
														<div className="flex justify-between items-start mb-4">
															<div>
																<h3 className="text-lg font-medium text-blue-100 group-hover:text-blue-400 transition-colors">
																	{repoDisplayName}
																</h3>
																{repo.language && (
																	<div className="flex items-center gap-2 mt-2">
																		<span className="text-xs bg-slate-800 px-2 py-0.5 rounded flex items-center gap-1.5 text-slate-300">
																			<span
																				className={`w-1.5 h-1.5 rounded-full ${getLanguageColor(repo.language)}`}
																			/>
																			{repo.language}
																		</span>
																		{getTags(repo).map((tag) => (
																			<span
																				key={tag.label}
																				className={`text-xs px-2 py-0.5 rounded ${tag.color}`}
																			>
																				{tag.label}
																			</span>
																		))}
																	</div>
																)}
															</div>
															<div className="p-2 text-slate-400 group-hover:text-white group-hover:bg-white/10 rounded-lg transition-colors">
																<ExternalLink
																	className="w-4 h-4"
																	aria-hidden="true"
																/>
															</div>
														</div>
														<p className="text-slate-400 text-sm line-clamp-2 min-h-[40px]">
															{repo.description || "설명이 없습니다."}
														</p>
													</a>
													);
												})
											) : hasSearch ? (
												<div className="text-slate-400 text-center py-8 bg-slate-900/20 rounded-xl border border-white/5 border-dashed">
													검색 결과가 없습니다.
												</div>
											) : (
												<NoDataHint command="python scripts/sync_data.py" />
											)}
										</div>
									</section>

									{/* NotebookLM Section */}
									<section className="space-y-6">
										<div className="flex items-center gap-3 mb-2">
											<div className="p-3 bg-slate-800/50 rounded-xl border border-white/5">
												<Book
													className="w-6 h-6 text-purple-400"
													aria-hidden="true"
												/>
											</div>
											<div className="flex-1">
												<h2 className="text-2xl font-semibold">지식 베이스</h2>
												<p className="text-sm text-slate-400">
													NotebookLM Notebooks
												</p>
											</div>
											<Badge
												variant="secondary"
												className="bg-slate-800 text-slate-300 rounded-full"
											>
												{filteredData.notebooklm.length}
											</Badge>
										</div>

										<div className="grid gap-4">
											{filteredData.notebooklm.length > 0 ? (
												filteredData.notebooklm.map((notebook) => (
													<button
														key={notebook.id}
														type="button"
														onClick={() => setSelectedNotebook(notebook)}
														aria-label={`${notebook.title} 상세 보기`}
														className="group relative block w-full text-left p-6 bg-slate-900/40 border border-white/5 hover:border-purple-500/30 rounded-2xl hover:bg-slate-800/40 transition-all duration-300 backdrop-blur-sm cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
													>
														<div className="flex justify-between items-start mb-2">
															<div>
																<h3 className="text-lg font-medium text-purple-100 group-hover:text-purple-400 transition-colors line-clamp-1">
																	{notebook.title}
																</h3>
																<div className="flex gap-2 mt-2">
																	{getTags(notebook).map((tag) => (
																		<span
																			key={tag.label}
																			className={`text-xs px-2 py-0.5 rounded ${tag.color}`}
																		>
																			{tag.label}
																		</span>
																	))}
																</div>
															</div>
															<div className="p-2 text-slate-400 group-hover:text-white transition-colors opacity-0 group-hover:opacity-100">
																<Search className="w-4 h-4" aria-hidden="true" />
															</div>
														</div>
														<div className="flex items-center gap-4 text-sm text-slate-400 mt-3">
															<div className="flex items-center gap-1.5">
																<Code className="w-4 h-4" aria-hidden="true" />
																<span>{notebook.source_count}개 소스</span>
															</div>
															<div className="flex items-center gap-1.5">
																<Smartphone
																	className="w-4 h-4"
																	aria-hidden="true"
																/>
																<span className="capitalize">
																	{notebook.ownership === "owned"
																		? "내 문서"
																		: "공유됨"}
																</span>
															</div>
														</div>
													</button>
												))
											) : hasSearch ? (
												<div className="text-slate-400 text-center py-8 bg-slate-900/20 rounded-xl border border-white/5 border-dashed">
													검색 결과가 없습니다.
												</div>
											) : (
												<NoDataHint command="python scripts/sync_data.py" />
											)}
										</div>
									</section>
								</div>
							</>
						)}

						{/* ── TAB: QA/QC 현황 ─────────────── */}
						{activeTab === "qaqc" &&
							(data?.qaqc ? (
								<QaQcPanel data={data.qaqc} />
							) : (
								<div className="text-center py-16 text-slate-400">
									<Shield
										className="w-16 h-16 mx-auto mb-4 opacity-20"
										aria-hidden="true"
									/>
									<p className="text-lg">QA/QC 데이터가 아직 없습니다</p>
									<p className="text-sm mt-2 text-slate-500">
										<code className="bg-slate-800 px-2 py-1 rounded text-xs">
											python workspace/execution/qaqc_runner.py
										</code>
										를 실행하세요
									</p>
								</div>
							))}

						{/* ── TAB: 활동 타임라인 ──────────── */}
						{activeTab === "activity" && (
							<ActivityTimeline sessions={data?.sessions || []} />
						)}
					</div>
				)}
			</main>

			{/* Details Modal */}
			<Dialog
				open={!!selectedNotebook}
				onOpenChange={(open) => !open && setSelectedNotebook(null)}
			>
				{selectedNotebook && (
					<DialogContent>
						<DialogHeader>
							<DialogTitle>{selectedNotebook.title}</DialogTitle>
							<DialogDescription>
								<span className="font-mono text-xs text-slate-400">
									{selectedNotebook.id}
								</span>
								{getTags(selectedNotebook).length > 0 && (
									<span className="ml-2">
										{getTags(selectedNotebook).map((tag) => (
											<Badge
												key={tag.label}
												variant="outline"
												className={`${tag.color.replace("/20", "/10")} ml-1`}
											>
												{tag.label}
											</Badge>
										))}
									</span>
								)}
							</DialogDescription>
						</DialogHeader>

						<div className="p-6 max-h-[60vh] overflow-y-auto">
							<h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
								연결된 소스 파일 ({selectedNotebook.source_count})
							</h3>
							<div className="space-y-2">
								{selectedNotebook.sources &&
								selectedNotebook.sources.length > 0 ? (
									selectedNotebook.sources.map((source) => (
										<div
											key={source.id ?? source.title}
											className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg border border-white/5"
										>
											<div className="p-2 bg-purple-500/20 rounded text-purple-400">
												<FileText className="w-4 h-4" aria-hidden="true" />
											</div>
											<div className="flex-1 min-w-0">
												<p className="text-sm font-medium text-slate-200 truncate">
													{source.title}
												</p>
												{source.type && (
													<p className="text-xs text-slate-400">{source.type}</p>
												)}
											</div>
										</div>
									))
								) : (
									<p className="text-slate-400 italic">
										표시할 소스 정보가 없습니다.
									</p>
								)}
							</div>
						</div>

						<DialogFooter>
							<a
								href={selectedNotebook.url}
								target="_blank"
								rel="noopener noreferrer"
							>
								<Button className="bg-purple-600 hover:bg-purple-500">
									NotebookLM에서 열기
									<ExternalLink className="w-4 h-4" aria-hidden="true" />
								</Button>
							</a>
						</DialogFooter>
					</DialogContent>
				)}
			</Dialog>
		</div>
	);
}

function getLanguageColor(lang: string) {
	const colors: { [key: string]: string } = {
		TypeScript: "bg-blue-500",
		JavaScript: "bg-yellow-400",
		Python: "bg-green-500",
		HTML: "bg-orange-500",
		CSS: "bg-blue-300",
		Vue: "bg-green-400",
		Unknown: "bg-slate-600",
	};
	return colors[lang] || "bg-slate-500";
}
