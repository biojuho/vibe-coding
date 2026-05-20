'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshCwIcon } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getRealTimeMarketPrice } from '@/lib/actions';
import { formatMoney } from '@/lib/utils';

function PricePanel({ title, rows }) {
  return (
    <div className="clay-inset rounded-[24px] p-4 transition-[box-shadow,transform] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5">
      <div className="mb-3 border-b border-[color:var(--color-surface-border)] pb-3">
        <span className="text-sm font-bold text-[color:var(--color-text)] tracking-[-0.01em]">{title}</span>
      </div>
      <div className="grid gap-2.5">
        {rows.map(([grade, value], index) => (
          <div
            key={grade}
            className="flex items-center justify-between text-sm transition-[background,transform] duration-200 rounded-lg px-2 py-1.5 -mx-2 hover:bg-[color:color-mix(in_srgb,var(--color-surface-elevated)_60%,transparent)]"
            style={{
              borderBottom:
                index === rows.length - 1
                  ? 'none'
                  : '1px solid color-mix(in srgb, var(--color-surface-border) 45%, transparent)',
            }}
          >
            <span className="font-medium text-[color:var(--color-text-secondary)]">{grade}</span>
            <span className="font-bold text-[color:var(--color-text)] tabular-nums">{formatMoney(value)} / kg</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function getSourcePresentation(prices) {
  switch (prices?.source) {
    case 'kape-live':
      return {
        label: '실시간 KAPE',
        style: {
          background: 'color-mix(in srgb, var(--chart-clay-5) 18%, white 82%)',
          color: 'var(--chart-clay-5)',
          borderColor: 'color-mix(in srgb, var(--chart-clay-5) 32%, transparent)',
        },
      };
    case 'kape-cache':
      return {
        label: '저장된 KAPE',
        style: {
          background: 'color-mix(in srgb, var(--chart-clay-3) 18%, white 82%)',
          color: 'var(--chart-clay-3)',
          borderColor: 'color-mix(in srgb, var(--chart-clay-3) 32%, transparent)',
        },
      };
    case 'cache-stale':
      return {
        label: '이전 저장값',
        style: {
          background: 'color-mix(in srgb, var(--chart-clay-2) 18%, white 82%)',
          color: 'var(--chart-clay-2)',
          borderColor: 'color-mix(in srgb, var(--chart-clay-2) 32%, transparent)',
        },
      };
    default:
      return {
        label: '확인 불가',
        style: {
          background: 'color-mix(in srgb, #9aa2ad 18%, white 82%)',
          color: '#637083',
          borderColor: 'color-mix(in srgb, #9aa2ad 32%, transparent)',
        },
      };
  }
}

export default function MarketPriceWidget({ initialData = null }) {
  const [prices, setPrices] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);
  const isMountedRef = useRef(false);
  const inFlightRequestRef = useRef(null);
  const requestSequenceRef = useRef(0);
  const [lastUpdated, setLastUpdated] = useState(() => {
    if (!initialData?.fetchedAt) {
      return initialData ? new Date() : null;
    }

    return new Date(initialData.fetchedAt);
  });

  const applyPriceSnapshot = useCallback((data) => {
    setPrices(data);
    setLastUpdated(data?.fetchedAt ? new Date(data.fetchedAt) : new Date());
  }, []);

  const fetchPrices = useCallback(() => {
    if (inFlightRequestRef.current) {
      return inFlightRequestRef.current;
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
        console.error('Failed to fetch market prices:', error);
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

    if (!initialData) {
      refreshTimer = window.setTimeout(() => {
        void fetchPrices();
      }, 0);
    }

    const interval = window.setInterval(() => {
      void fetchPrices();
    }, 1000 * 60 * 60);

    return () => {
      isMountedRef.current = false;
      if (refreshTimer) {
        window.clearTimeout(refreshTimer);
      }
      window.clearInterval(interval);
    };
  }, [fetchPrices, initialData]);

  if (loading && !prices) {
    return (
      <Card className="animate-fadeInUp">
        <CardContent className="flex h-60 items-center justify-center">
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
        <CardContent className="flex min-h-36 items-center justify-center text-center">
          <div className="text-sm text-[color:var(--color-text-secondary)]">
            {prices?.message ?? '지금은 한우 시세 데이터를 확인할 수 없습니다.'}
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
              {prices.date ?? '최근'} 가중평균 거래가
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
              aria-label={loading ? '시세 갱신 중' : '한우 시세 새로고침'}
              title={loading ? '시세 갱신 중' : '한우 시세 새로고침'}
              className="clay-pressable inline-flex h-10 w-10 items-center justify-center rounded-full text-[color:var(--color-text-secondary)]"
            >
              <RefreshCwIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="grid gap-3 md:grid-cols-2">
          <PricePanel
            title="수소 / kg"
            rows={[
              ['1++ 등급', prices.bull.grade1pp],
              ['1+ 등급', prices.bull.grade1p],
              ['1 등급', prices.bull.grade1],
            ]}
          />
          <PricePanel
            title="암소 / kg"
            rows={[
              ['1++ 등급', prices.cow.grade1pp],
              ['1+ 등급', prices.cow.grade1p],
              ['1 등급', prices.cow.grade1],
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
            <span>갱신 {lastUpdated.toLocaleTimeString()}</span>
            <span>출처: KAPE</span>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
