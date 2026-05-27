"use client";

import { RefreshCw, Sparkles } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
	PremiumCard,
	PremiumCardContent,
	PremiumCardHeader,
} from "@/components/ui/premium-card";
import {
	MAX_INSIGHTS,
	buildHeuristicInsights,
	parseInsightResponse,
} from "@/lib/ai-insight.mjs";

const AI_INSIGHT_TIMEOUT_MS = 12000;
const AI_INSIGHT_TIMEOUT_REASON =
	"AI 분석 응답이 지연되어 기본 규칙 인사이트로 전환했습니다.";
const AI_INSIGHT_HEURISTIC_REASON =
	"AI 분석 대신 기본 규칙 인사이트로 표시합니다.";

const PRIORITY_STYLE = {
	high: {
		label: "긴급",
		bg: "color-mix(in srgb, var(--color-danger) 14%, white 86%)",
		fg: "var(--color-danger)",
	},
	medium: {
		label: "주의",
		bg: "color-mix(in srgb, var(--color-warning) 16%, white 84%)",
		fg: "var(--color-warning)",
	},
	low: {
		label: "참고",
		bg: "color-mix(in srgb, var(--color-success) 14%, white 86%)",
		fg: "var(--color-success)",
	},
};

function PriorityBadge({ priority }) {
	const style = PRIORITY_STYLE[priority] ?? PRIORITY_STYLE.medium;
	return (
		<span
			className="px-1.5 py-0.5 rounded-full text-[10px] font-bold tracking-tight"
			style={{ background: style.bg, color: style.fg }}
		>
			{style.label}
		</span>
	);
}

function SourceBadge({ source }) {
	const isAi = source === "ai";
	return (
		<span
			className="px-1.5 py-0.5 rounded-full text-[11px] font-medium tracking-tight"
			style={{
				background: isAi
					? "color-mix(in srgb, var(--color-primary) 16%, white 84%)"
					: "color-mix(in srgb, var(--color-text-muted) 16%, white 84%)",
				color: isAi ? "var(--color-primary)" : "var(--color-text-muted)",
			}}
		>
			{isAi ? "AI 분석" : "기본 규칙"}
		</span>
	);
}

export default function AIInsightWidget({ summary }) {
	const stableSummary = useMemo(
		() => (summary && typeof summary === "object" ? summary : {}),
		[summary],
	);
	const [insights, setInsights] = useState(() =>
		buildHeuristicInsights(stableSummary),
	);
	const [source, setSource] = useState("heuristic");
	const [isLoading, setIsLoading] = useState(true);
	const [reason, setReason] = useState(null);
	const [refreshNonce, setRefreshNonce] = useState(0);
	const abortRef = useRef(null);
	const refreshButtonLabel = isLoading
		? "AI 인사이트 새로고침 중"
		: "AI 인사이트 새로고침";

	useEffect(() => {
		const controller = new AbortController();
		let didTimeout = false;
		abortRef.current = controller;
		queueMicrotask(() => {
			if (!controller.signal.aborted) {
				setInsights(buildHeuristicInsights(stableSummary));
				setSource("heuristic");
				setIsLoading(true);
				setReason(null);
			}
		});
		let timeoutId = null;
		try {
			timeoutId = window.setTimeout(() => {
				didTimeout = true;
				controller.abort();
			}, AI_INSIGHT_TIMEOUT_MS);
		} catch (error) {
			console.error("Failed to schedule AI insight timeout:", error);
		}

		fetch("/api/ai/insight", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ summary: stableSummary }),
			signal: controller.signal,
		})
			.then(async (res) => {
				if (!res.ok) {
					throw new Error(`서버 오류 (${res.status})`);
				}
				const payload = await res.json();
				const parsed = parseInsightResponse(payload.insights);
				if (!parsed || parsed.length !== MAX_INSIGHTS) {
					throw new Error("응답 형식이 올바르지 않습니다.");
				}
				const nextSource = payload.source === "ai" ? "ai" : "heuristic";
				setInsights(parsed);
				setSource(nextSource);
				if (nextSource === "heuristic") {
					const fallbackReason =
						typeof payload.reason === "string" && payload.reason.trim().length > 0
							? payload.reason.trim()
							: AI_INSIGHT_HEURISTIC_REASON;
					setReason(fallbackReason);
				} else {
					setReason(null);
				}
			})
			.catch((error) => {
				if (error.name === "AbortError" && !didTimeout) return;
				console.error("AI 인사이트 호출 실패:", error);
				setInsights(buildHeuristicInsights(stableSummary));
				setSource("heuristic");
				if (didTimeout) {
					setReason(AI_INSIGHT_TIMEOUT_REASON);
					return;
				}
				setReason("AI 분석 응답을 받지 못해 기본 규칙 인사이트로 표시합니다.");
			})
			.finally(() => {
				if (timeoutId !== null) {
					try {
						window.clearTimeout(timeoutId);
					} catch {}
				}
				if (!controller.signal.aborted || didTimeout) {
					setIsLoading(false);
				}
			});

		return () => {
			if (timeoutId !== null) {
				try {
					window.clearTimeout(timeoutId);
				} catch {}
			}
			controller.abort();
			if (abortRef.current === controller) {
				abortRef.current = null;
			}
		};
	}, [stableSummary, refreshNonce]);

	return (
		<PremiumCard className="mb-4">
			<PremiumCardHeader
				title="오늘의 AI 인사이트"
				icon="🤖"
				description="농장 기록을 기반으로 우선순위 3가지 행동을 정리합니다."
			>
				<div className="flex items-center gap-1.5 ml-auto">
					<SourceBadge source={source} />
					{isLoading ? (
						<span
							className="text-[11px] font-medium text-[color:var(--color-text-muted)]"
							role="status"
							aria-live="polite"
							aria-atomic="true"
							aria-busy={isLoading}
						>
							AI 인사이트 분석 중…
						</span>
					) : null}
					<button
						type="button"
						onClick={() => setRefreshNonce((current) => current + 1)}
						disabled={isLoading}
						aria-busy={isLoading}
						aria-label={refreshButtonLabel}
						title={refreshButtonLabel}
						className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-[color:var(--color-surface-stroke)] text-[color:var(--color-text-muted)] transition hover:text-[color:var(--color-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--color-primary)] disabled:cursor-not-allowed disabled:opacity-60"
					>
						<RefreshCw
							size={14}
							aria-hidden="true"
							className={isLoading ? "animate-spin" : ""}
						/>
					</button>
				</div>
			</PremiumCardHeader>
			<PremiumCardContent>
				{reason ? (
					<p
						className="mb-2 text-[11px] text-[color:var(--color-text-muted)]"
						data-testid="ai-insight-reason"
						role="status"
						aria-live="polite"
						aria-atomic="true"
					>
						{reason}
					</p>
				) : null}
				<ul
					className="flex flex-col gap-2"
					aria-label="AI 인사이트 목록"
					aria-busy={isLoading}
					aria-live="polite"
					aria-relevant="additions text"
				>
					{insights.map((insight, index) => (
						<li
							key={`${insight.title}-${index}`}
							className="flex items-start gap-2 p-2.5 rounded-lg outline outline-1 outline-[color:var(--color-surface-stroke)] bg-[color:color-mix(in_srgb,var(--color-surface-elevated)_50%,transparent)]"
						>
							<Sparkles
								size={16}
								aria-hidden="true"
								className="mt-0.5 shrink-0 text-[color:var(--color-primary)]"
							/>
							<div className="flex-1 min-w-0">
								<div className="flex items-center gap-1.5 mb-1">
									<span className="text-sm font-bold text-[color:var(--color-text)]">
										{insight.title}
									</span>
									<PriorityBadge priority={insight.priority} />
								</div>
								<p className="text-xs leading-relaxed text-[color:var(--color-text-muted)]">
									{insight.body}
								</p>
							</div>
						</li>
					))}
				</ul>
			</PremiumCardContent>
		</PremiumCard>
	);
}
