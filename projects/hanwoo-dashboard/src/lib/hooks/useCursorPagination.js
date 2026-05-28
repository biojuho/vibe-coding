"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { sanitizeDashboardPageInfoTransition } from "@/lib/dashboard/pagination-guard.mjs";

const PAGINATION_REQUEST_TIMEOUT_MS = 15000;

function normalizePaginationParams(params) {
	return params && typeof params === "object" && !Array.isArray(params)
		? params
		: {};
}

function normalizePaginationItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) => item && typeof item === "object" && !Array.isArray(item),
			)
		: [];
}

/**
 * 공용 Cursor-based pagination을 관리하는 훅.
 *
 * @param {Object} props
 * @param {string} props.endpoint - 데이터를 페치할 API 엔드포인트 URL
 * @param {Array} props.initialItems - 초기에 세팅할 데이터 배열
 * @param {Object} props.initialPageInfo - 초기 pageInfo 객체
 */
export function useCursorPagination(options = {}) {
	const {
		endpoint,
		initialItems = [],
		initialPageInfo = null,
	} = normalizePaginationParams(options);
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
	const abortRef = useRef(null);
	const mountedRef = useRef(true);

	const hasMore = pageInfo?.hasMore ?? false;

	useEffect(() => {
		mountedRef.current = true;

		return () => {
			mountedRef.current = false;
			if (abortRef.current) {
				abortRef.current.abort();
				abortRef.current = null;
			}
		};
	}, []);

	const loadMore = useCallback(
		async (extraParams = {}) => {
			const safeExtraParams = normalizePaginationParams(extraParams);
			if (isLoading || !hasMore) return;

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
				console.error(`Failed to schedule load-more timeout at ${endpoint}:`, error);
				didTimeout = true;
				controller.abort();
			}

			setIsLoading(true);
			try {
				const params = new URLSearchParams();
				if (pageInfo.nextCursor) params.set("cursor", pageInfo.nextCursor);
				params.set("limit", String(pageInfo.limit || 50));

				// 동적 파라미터 매핑
				for (const [key, value] of Object.entries(safeExtraParams)) {
					if (value !== undefined && value !== null && value !== "") {
						params.set(key, String(value));
					}
				}

				const res = await fetch(`${endpoint}?${params.toString()}`, {
					signal: controller.signal,
				});
				if (!mountedRef.current || controller.signal.aborted) {
					return;
				}

				if (!res.ok) {
					console.error(`Failed to load more from ${endpoint}:`, res.status);
					return;
				}

				const json = await res.json();
				if (!json.success) {
					console.error(`Pagination API error at ${endpoint}:`, json.message);
					return;
				}

				const { items: newItems, pageInfo: newPageInfo } = json.data ?? {};
				const safeNewItems = normalizePaginationItems(newItems);
				const safePageInfo = sanitizeDashboardPageInfoTransition({
					currentPageInfo: pageInfo,
					receivedPageInfo: newPageInfo,
					source: endpoint,
				});

				if (safePageInfo.paginationError) {
					console.error(safePageInfo.paginationError);
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
						console.error(`Load more timed out at ${endpoint}.`);
					}
				} else {
					console.error(`Load more error at ${endpoint}:`, error);
				}
			} finally {
				if (timeoutId !== null) {
					try {
						window.clearTimeout(timeoutId);
					} catch {}
				}
				if (abortRef.current === controller) {
					abortRef.current = null;
				}
				if (mountedRef.current && (!controller.signal.aborted || didTimeout)) {
					setIsLoading(false);
				}
			}
		},
		[isLoading, hasMore, pageInfo, endpoint],
	);

	return { items, setItems, pageInfo, isLoading, hasMore, loadMore };
}
