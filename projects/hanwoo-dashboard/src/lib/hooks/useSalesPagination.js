"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { sanitizeDashboardPageInfoTransition } from "@/lib/dashboard/pagination-guard.mjs";

function normalizePaginationItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) => item && typeof item === "object" && !Array.isArray(item),
			)
		: [];
}

function normalizePaginationParams(params) {
	return params && typeof params === "object" && !Array.isArray(params)
		? params
		: {};
}

const PAGINATION_REQUEST_TIMEOUT_MS = 15000;
const SALES_PAGINATION_TIMEOUT_MESSAGE =
	"이전 판매 기록을 불러오는 데 시간이 오래 걸리고 있습니다. 잠시 후 다시 시도해 주세요.";
const SALES_PAGINATION_ERROR_MESSAGE =
	"이전 판매 기록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.";

/**
 * Sales 목록의 cursor-based pagination을 관리하는 훅.
 *
 * - initialItems: page.js에서 SSR로 가져온 첫 페이지 데이터
 * - initialPageInfo: 첫 fetch의 pageInfo (hasMore, nextCursor, ...)
 *
 * 반환:
 *   items       – 현재까지 누적된 sales 배열
 *   pageInfo    – 가장 최근 fetch의 pageInfo
 *   isLoading   – 추가 로드 진행 중 여부
 *   hasMore     – 다음 페이지가 있는지
 *   loadMore    – 다음 페이지 fetch 함수
 *   setItems    – 뮤테이션(추가) 시 직접 state 조작
 */
export function useSalesPagination(options = {}) {
	const { initialItems = [], initialPageInfo = null } =
		normalizePaginationParams(options);
	const [items, setItems] = useState(() =>
		normalizePaginationItems(initialItems),
	);
	const [pageInfo, setPageInfo] = useState(
		initialPageInfo ?? {
			hasMore: false,
			nextCursor: null,
			limit: 50,
			returnedCount: 0,
		},
	);
	const [isLoading, setIsLoading] = useState(false);
	const [loadError, setLoadError] = useState("");
	const abortRef = useRef(null);
	const loadInFlightRef = useRef(false);
	const mountedRef = useRef(true);

	const hasMore = pageInfo?.hasMore ?? false;

	useEffect(() => {
		mountedRef.current = true;

		return () => {
			mountedRef.current = false;
			loadInFlightRef.current = false;
			if (abortRef.current) {
				abortRef.current.abort();
				abortRef.current = null;
			}
		};
	}, []);

	const loadMore = useCallback(
		async (params = {}) => {
			const { from, to } = normalizePaginationParams(params);
			if (loadInFlightRef.current || isLoading || !hasMore) return;
			loadInFlightRef.current = true;

			// Abort 이전 요청
			if (abortRef.current) abortRef.current.abort();
			const controller = new AbortController();
			abortRef.current = controller;
			let didTimeout = false;
			let timeoutId = null;
			try {
				timeoutId = window.setTimeout(() => {
					didTimeout = true;
					controller.abort();
				}, PAGINATION_REQUEST_TIMEOUT_MS);
			} catch (error) {
				console.error("Failed to schedule sales pagination timeout:", error);
				didTimeout = true;
				controller.abort();
			}

			setIsLoading(true);
			setLoadError("");
			try {
				const params = new URLSearchParams();
				if (pageInfo.nextCursor) params.set("cursor", pageInfo.nextCursor);
				params.set("limit", String(pageInfo.limit || 50));
				if (from) params.set("from", from);
				if (to) params.set("to", to);

				const res = await fetch(`/api/dashboard/sales?${params.toString()}`, {
					signal: controller.signal,
				});
				if (!mountedRef.current || controller.signal.aborted) {
					return;
				}

				if (!res.ok) {
					console.error("Failed to load more sales:", res.status);
					setLoadError(SALES_PAGINATION_ERROR_MESSAGE);
					return;
				}

				const json = await res.json();
				if (!json.success) {
					console.error("Sales API error:", json.message);
					setLoadError(SALES_PAGINATION_ERROR_MESSAGE);
					return;
				}

				const { items: newItems, pageInfo: newPageInfo } = json.data ?? {};
				const safeNewItems = normalizePaginationItems(newItems);
				const safePageInfo = sanitizeDashboardPageInfoTransition({
					currentPageInfo: pageInfo,
					receivedPageInfo: newPageInfo,
					source: "/api/dashboard/sales",
				});

				if (safePageInfo.paginationError) {
					console.error(safePageInfo.paginationError);
					setLoadError(SALES_PAGINATION_ERROR_MESSAGE);
				}

				if (!mountedRef.current || controller.signal.aborted) {
					return;
				}

				setItems((prev) => [
					...normalizePaginationItems(prev),
					...safeNewItems,
				]);
				setPageInfo(safePageInfo);
			} catch (error) {
				if (error.name === "AbortError") {
					if (didTimeout && mountedRef.current) {
						console.error("Load more sales timed out.");
						setLoadError(SALES_PAGINATION_TIMEOUT_MESSAGE);
					}
				} else {
					console.error("Load more sales error:", error);
					setLoadError(SALES_PAGINATION_ERROR_MESSAGE);
				}
			} finally {
				if (timeoutId !== null) {
					try {
						window.clearTimeout(timeoutId);
					} catch {}
				}
				loadInFlightRef.current = false;
				if (abortRef.current === controller) {
					abortRef.current = null;
				}
				if (mountedRef.current && (!controller.signal.aborted || didTimeout)) {
					setIsLoading(false);
				}
			}
		},
		[hasMore, pageInfo],
	);

	return { items, setItems, pageInfo, isLoading, hasMore, loadMore, loadError };
}
