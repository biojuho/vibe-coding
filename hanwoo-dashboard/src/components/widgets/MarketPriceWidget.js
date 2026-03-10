"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { RefreshCwIcon } from 'lucide-react';
import { getRealTimeMarketPrice } from '@/lib/actions';
import { formatMoney } from '@/lib/utils';

export default function MarketPriceWidget() {
  const [prices, setPrices] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchPrices = async () => {
    setLoading(true);
    try {
      const data = await getRealTimeMarketPrice();
      setPrices(data);
      setLastUpdated(new Date());
    } catch (error) {
      console.error("Failed to fetch market prices:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, 1000 * 60 * 60); // Refresh every hour
    return () => clearInterval(interval);
  }, []);

  const renderPriceRow = (grade, value) => (
    <div
      className="flex items-center justify-between py-1.5 text-sm"
      style={{ borderBottom: "1px solid var(--color-border)" }}
    >
      <span style={{ color: "var(--color-text-secondary)", fontWeight: 500 }}>{grade}</span>
      <span style={{ fontWeight: 700, color: "var(--color-text)" }}>
        {formatMoney(value)}원
      </span>
    </div>
  );

  if (loading && !prices) {
    return (
      <Card className="w-full animate-pulse" style={{ height: "240px", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>시세 정보 로딩 중...</div>
      </Card>
    );
  }

  if (!prices) {
    return (
      <Card className="w-full" style={{ height: "100px", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>시세 정보를 불러올 수 없습니다.</div>
      </Card>
    );
  }

  return (
    <Card className="w-full shadow-sm hover:shadow-md transition-shadow animate-fadeInUp">
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
        <div className="flex items-center gap-2 flex-wrap">
          <CardTitle className="text-lg font-bold" style={{ color: "var(--color-text)" }}>
            📊 오늘의 한우 시세
          </CardTitle>
          <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
            ({prices.date} 기준, 전국 평균)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            style={{
              fontSize: "10px",
              padding: "3px 10px",
              borderRadius: "var(--radius-full)",
              fontWeight: 700,
              background: prices.isRealtime
                ? "rgba(59, 130, 246, 0.12)"
                : "rgba(245, 158, 11, 0.12)",
              color: prices.isRealtime
                ? "var(--color-info, #3b82f6)"
                : "var(--color-warning, #f59e0b)",
              border: `1px solid ${prices.isRealtime ? "rgba(59,130,246,0.3)" : "rgba(245,158,11,0.3)"}`,
            }}
          >
            {prices.isRealtime ? "🟢 실시간 (API)" : "🟡 시뮬레이션"}
          </span>
          <button
            onClick={fetchPrices}
            disabled={loading}
            style={{
              background: "transparent",
              border: "none",
              padding: "6px",
              borderRadius: "var(--radius-full)",
              cursor: "pointer",
              color: "var(--color-text-secondary)",
              transition: "background var(--transition-fast)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            onMouseEnter={e => e.currentTarget.style.background = "var(--color-border-light)"}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}
          >
            <RefreshCwIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {/* 거세우 섹션 */}
          <div
            style={{
              background: "var(--color-border-light)",
              borderRadius: "var(--radius-lg)",
              padding: "12px",
            }}
          >
            <div
              style={{
                fontSize: "12px",
                fontWeight: 700,
                color: "var(--color-text)",
                marginBottom: "8px",
                paddingBottom: "8px",
                borderBottom: "1px solid var(--color-border)",
              }}
            >
              🐂 거세우 (지육 kg)
            </div>
            {renderPriceRow("1++등급", prices.bull.grade1pp)}
            {renderPriceRow("1+등급", prices.bull.grade1p)}
            <div className="flex items-center justify-between py-1.5 text-sm">
              <span style={{ color: "var(--color-text-secondary)", fontWeight: 500 }}>1등급</span>
              <span style={{ fontWeight: 700, color: "var(--color-text)" }}>{formatMoney(prices.bull.grade1)}원</span>
            </div>
          </div>

          {/* 암소 섹션 */}
          <div
            style={{
              background: "var(--color-border-light)",
              borderRadius: "var(--radius-lg)",
              padding: "12px",
            }}
          >
            <div
              style={{
                fontSize: "12px",
                fontWeight: 700,
                color: "var(--color-text)",
                marginBottom: "8px",
                paddingBottom: "8px",
                borderBottom: "1px solid var(--color-border)",
              }}
            >
              🐄 암소 (지육 kg)
            </div>
            {renderPriceRow("1++등급", prices.cow.grade1pp)}
            {renderPriceRow("1+등급", prices.cow.grade1p)}
            <div className="flex items-center justify-between py-1.5 text-sm">
              <span style={{ color: "var(--color-text-secondary)", fontWeight: 500 }}>1등급</span>
              <span style={{ fontWeight: 700, color: "var(--color-text)" }}>{formatMoney(prices.cow.grade1)}원</span>
            </div>
          </div>
        </div>

        {lastUpdated && (
          <div
            className="mt-3 flex justify-between items-center"
            style={{ fontSize: "10px", color: "var(--color-text-secondary)" }}
          >
            <span>업데이트: {lastUpdated.toLocaleTimeString()}</span>
            <span>출처: 축산물품질평가원</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
