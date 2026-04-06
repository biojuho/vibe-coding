'use client';

import { useState, useCallback, useRef } from 'react';

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
export function useSalesPagination({ initialItems = [], initialPageInfo = null } = {}) {
  const [items, setItems] = useState(initialItems);
  const [pageInfo, setPageInfo] = useState(
    initialPageInfo ?? { hasMore: false, nextCursor: null, limit: 50, returnedCount: 0 },
  );
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef(null);

  const hasMore = pageInfo?.hasMore ?? false;

  const loadMore = useCallback(
    async ({ from, to } = {}) => {
      if (isLoading || !hasMore) return;

      // Abort 이전 요청
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      try {
        const params = new URLSearchParams();
        if (pageInfo.nextCursor) params.set('cursor', pageInfo.nextCursor);
        params.set('limit', String(pageInfo.limit || 50));
        if (from) params.set('from', from);
        if (to) params.set('to', to);

        const res = await fetch(`/api/dashboard/sales?${params.toString()}`, {
          signal: controller.signal,
        });

        if (!res.ok) {
          console.error('Failed to load more sales:', res.status);
          return;
        }

        const json = await res.json();
        if (!json.success) {
          console.error('Sales API error:', json.message);
          return;
        }

        const { items: newItems, pageInfo: newPageInfo } = json.data;
        setItems((prev) => [...prev, ...newItems]);
        setPageInfo(newPageInfo);
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Load more sales error:', error);
        }
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, hasMore, pageInfo],
  );

  return { items, setItems, pageInfo, isLoading, hasMore, loadMore };
}
