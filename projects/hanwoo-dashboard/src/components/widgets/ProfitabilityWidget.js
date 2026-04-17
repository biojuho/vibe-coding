'use client';

import { PremiumCard, PremiumCardContent, PremiumCardHeader } from '@/components/ui/premium-card';

export function ProfitabilityWidget({ data, isLoading, error }) {
  if (isLoading) {
    return (
      <PremiumCard className="animate-pulse mb-4">
        <PremiumCardHeader title="출하 수익성 예측" icon="📈" />
        <PremiumCardContent>
          <div className="h-6 rounded w-3/4 mb-2 bg-[color:var(--color-surface-stroke)]"></div>
          <div className="h-4 rounded w-1/2 bg-[color:color-mix(in_srgb,var(--color-surface-stroke)_50%,transparent)]"></div>
        </PremiumCardContent>
      </PremiumCard>
    );
  }

  if (error) {
    return (
      <PremiumCard className="mb-4 bg-[color:color-mix(in_srgb,var(--color-danger)_10%,transparent)]">
        <PremiumCardHeader title="출하 수익성 예측" icon="⚠️" />
        <PremiumCardContent>
          <p className="text-sm font-bold text-[color:var(--color-danger)]">{error}</p>
        </PremiumCardContent>
      </PremiumCard>
    );
  }

  if (!data || data.length === 0) {
    return (
      <PremiumCard className="mb-4">
        <PremiumCardHeader title="출하 추천 개체" icon="📈" />
        <PremiumCardContent>
          <p className="text-sm text-[color:var(--color-text-muted)]">현재 출하 적령기(24개월 이상)인 개체가 없거나 분석 데이터가 부족합니다.</p>
        </PremiumCardContent>
      </PremiumCard>
    );
  }

  return (
    <PremiumCard className="mb-4 overflow-visible">
      <PremiumCardHeader 
        title="출하 수익성 추천" 
        icon="📈" 
        description="최적의 출하 타이밍과 예상 마진을 분석합니다."
      />
      <PremiumCardContent className="p-0">
        <div className="divide-y divide-gray-100">
          {data.map((item, idx) => (
            <div key={item.id} className="p-4 transition-colors hover:bg-[color:var(--color-surface-elevated)]">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-[color:var(--color-text)] border border-[color:var(--color-surface-stroke)] rounded px-1.5 py-0.5 text-xs">
                    {item.tagNumber.slice(-4)}
                  </span>
                  <span className="text-sm font-medium text-[color:var(--color-text)]">{item.name}</span>
                  {item.recommendShipment && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[color:color-mix(in_srgb,var(--color-danger)_16%,white_84%)] text-[color:var(--color-danger)]">
                      즉시 출하 권장
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <div className="text-sm font-black text-[color:var(--color-success)]">
                    {item.currentProfit > 0 ? '+' : ''}{(item.currentProfit / 10000).toFixed(0)}만원
                  </div>
                  <div className="text-[11px] font-medium text-[color:var(--color-text-muted)]">현재 예상 마진</div>
                </div>
              </div>

              <div className="flex items-center justify-between mt-3 text-xs rounded-lg p-2.5 outline outline-1 outline-[color:var(--color-surface-stroke)] bg-[color:color-mix(in_srgb,var(--color-surface-elevated)_50%,transparent)]">
                <div className="flex items-center gap-3">
                  <div>
                    <div className="text-[10px] mb-0.5 text-[color:var(--color-text-muted)]">현재 월령</div>
                    <div className="font-semibold text-[color:var(--color-text)]">{item.ageMonths}개월</div>
                  </div>
                  <div className="w-px h-6 bg-[color:var(--color-surface-stroke)]"></div>
                  <div>
                    <div className="text-[10px] mb-0.5 text-[color:var(--color-text-muted)]">현재 체중</div>
                    <div className="font-semibold text-[color:var(--color-text)]">{item.weight}kg</div>
                  </div>
                </div>

                <div className="flex flex-col items-end">
                  <div className="text-[10px] mb-0.5 text-[color:var(--color-text-muted)]">1개월 추가 비육 시</div>
                  <div className={`font-semibold flex items-center gap-1 ${item.marginalGain > 0 ? 'text-[color:var(--chart-clay-2)]' : 'text-[color:var(--color-warning)]'}`}>
                    {item.marginalGain > 0 ? '📈' : '📉'} 
                    {item.marginalGain > 0 ? '+' : ''}{(item.marginalGain / 10000).toFixed(0)}만원
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </PremiumCardContent>
    </PremiumCard>
  );
}
