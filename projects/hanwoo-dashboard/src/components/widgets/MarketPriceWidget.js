'use client';

import { useEffect, useState } from 'react';
import { RefreshCwIcon } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getRealTimeMarketPrice } from '@/lib/actions';
import { formatMoney } from '@/lib/utils';

function PricePanel({ title, emoji, rows }) {
  return (
    <div className="clay-inset rounded-[24px] p-4">
      <div className="mb-3 flex items-center gap-2 border-b border-[color:var(--color-surface-border)] pb-3">
        <span className="text-lg">{emoji}</span>
        <span className="text-sm font-bold text-[color:var(--color-text)]">{title}</span>
      </div>
      <div className="grid gap-2">
        {rows.map(([grade, value], index) => (
          <div
            key={grade}
            className="flex items-center justify-between text-sm"
            style={{
              paddingBottom: index === rows.length - 1 ? 0 : '8px',
              borderBottom:
                index === rows.length - 1 ? 'none' : '1px solid color-mix(in srgb, var(--color-surface-border) 65%, transparent)',
            }}
          >
            <span className="font-medium text-[color:var(--color-text-secondary)]">{grade}</span>
            <span className="font-bold text-[color:var(--color-text)]">{formatMoney(value)}원</span>
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
        label: 'Live KAPE',
        style: {
          background: 'color-mix(in srgb, var(--chart-clay-5) 18%, white 82%)',
          color: 'var(--chart-clay-5)',
          borderColor: 'color-mix(in srgb, var(--chart-clay-5) 32%, transparent)',
        },
      };
    case 'kape-cache':
      return {
        label: 'Cached KAPE',
        style: {
          background: 'color-mix(in srgb, var(--chart-clay-3) 18%, white 82%)',
          color: 'var(--chart-clay-3)',
          borderColor: 'color-mix(in srgb, var(--chart-clay-3) 32%, transparent)',
        },
      };
    case 'cache-stale':
      return {
        label: 'Stale Cache',
        style: {
          background: 'color-mix(in srgb, var(--chart-clay-2) 18%, white 82%)',
          color: 'var(--chart-clay-2)',
          borderColor: 'color-mix(in srgb, var(--chart-clay-2) 32%, transparent)',
        },
      };
    default:
      return {
        label: 'Unavailable',
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
  const [lastUpdated, setLastUpdated] = useState(() => {
    if (!initialData?.fetchedAt) {
      return initialData ? new Date() : null;
    }

    return new Date(initialData.fetchedAt);
  });

  const fetchPrices = async () => {
    setLoading(true);
    try {
      const data = await getRealTimeMarketPrice();
      setPrices(data);
      setLastUpdated(data?.fetchedAt ? new Date(data.fetchedAt) : new Date());
    } catch (error) {
      console.error('Failed to fetch market prices:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialData) {
      fetchPrices();
    }

    const interval = setInterval(fetchPrices, 1000 * 60 * 60);
    return () => clearInterval(interval);
  }, [initialData]);

  if (loading && !prices) {
    return (
      <Card className="animate-fadeInUp">
        <CardContent className="flex h-60 items-center justify-center">
          <div className="text-sm text-[color:var(--color-text-secondary)]">시세 정보를 불러오는 중입니다.</div>
        </CardContent>
      </Card>
    );
  }

  if (!prices) {
    return (
      <Card className="animate-fadeInUp">
        <CardContent className="flex h-28 items-center justify-center">
          <div className="text-sm text-[color:var(--color-text-secondary)]">시세 정보를 불러오지 못했습니다.</div>
        </CardContent>
      </Card>
    );
  }

  const badgeStyle = prices.isRealtime
    ? {
        background: 'color-mix(in srgb, var(--chart-clay-5) 18%, white 82%)',
        color: 'var(--chart-clay-5)',
        borderColor: 'color-mix(in srgb, var(--chart-clay-5) 32%, transparent)',
      }
    : {
        background: 'color-mix(in srgb, var(--chart-clay-2) 18%, white 82%)',
        color: 'var(--chart-clay-2)',
        borderColor: 'color-mix(in srgb, var(--chart-clay-2) 32%, transparent)',
      };

  return (
    <Card className="animate-fadeInUp overflow-hidden">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="clay-page-eyebrow mb-3">Market Pulse</div>
            <CardTitle className="text-xl font-bold text-[color:var(--color-text)]">오늘의 한우 시세</CardTitle>
            <p className="mt-2 text-xs text-[color:var(--color-text-secondary)]">
              {prices.date} 기준, 등급별 평균 거래가
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span
              className="inline-flex rounded-full border px-3 py-1 text-[11px] font-bold"
              style={badgeStyle}
            >
              {prices.isRealtime ? '실시간 API' : '샘플 데이터'}
            </span>
            <button
              type="button"
              onClick={fetchPrices}
              disabled={loading}
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
            title="거세우 지육 kg"
            emoji="🐂"
            rows={[
              ['1++ 등급', prices.bull.grade1pp],
              ['1+ 등급', prices.bull.grade1p],
              ['1 등급', prices.bull.grade1],
            ]}
          />
          <PricePanel
            title="암소 지육 kg"
            emoji="🐄"
            rows={[
              ['1++ 등급', prices.cow.grade1pp],
              ['1+ 등급', prices.cow.grade1p],
              ['1 등급', prices.cow.grade1],
            ]}
          />
        </div>

        {lastUpdated ? (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-[11px] text-[color:var(--color-text-muted)]">
            <span>업데이트 {lastUpdated.toLocaleTimeString()}</span>
            <span>출처 축산물품질평가원</span>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
