'use client';

import { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { DollarSign, TrendingDown, TrendingUp } from 'lucide-react';
import { formatMoney } from '@/lib/utils';

const CATEGORY_CONFIG = {
  feed: { name: '사료비', color: 'var(--chart-clay-2)' },
  medicine: { name: '약품/진료', color: 'var(--chart-clay-4)' },
  labor: { name: '인건비', color: 'var(--chart-clay-1)' },
  other: { name: '기타', color: 'var(--chart-clay-5)' },
};

const RANK_COLORS = ['var(--chart-clay-2)', 'var(--chart-clay-5)', 'var(--chart-clay-4)'];

export default function AnalysisTab({
  saleRecords = [],
  feedHistory = [],
  cattleList = [],
  expenseRecords = [],
}) {
  const hasExpenseData = expenseRecords.length > 0;

  const monthlyData = useMemo(() => {
    const data = {};
    const today = new Date();

    for (let index = 11; index >= 0; index -= 1) {
      const date = new Date(today.getFullYear(), today.getMonth() - index, 1);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      data[key] = { name: key, revenue: 0, cost: 0, profit: 0 };
    }

    saleRecords.forEach((record) => {
      const date = new Date(record.saleDate);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      if (data[key]) data[key].revenue += record.price;
    });

    expenseRecords.forEach((expense) => {
      const date = new Date(expense.date);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      if (data[key]) data[key].cost += expense.amount;
    });

    Object.keys(data).forEach((key) => {
      data[key].profit = data[key].revenue - data[key].cost;
    });

    return Object.values(data);
  }, [saleRecords, expenseRecords]);

  const costStructure = useMemo(() => {
    if (!hasExpenseData) return [];

    const totals = {};
    expenseRecords.forEach((expense) => {
      const category = expense.category || 'other';
      totals[category] = (totals[category] || 0) + expense.amount;
    });

    return Object.entries(totals).map(([category, amount]) => ({
      name: CATEGORY_CONFIG[category]?.name || category,
      value: amount,
      color: CATEGORY_CONFIG[category]?.color || 'var(--color-text-muted)',
    }));
  }, [expenseRecords, hasExpenseData]);

  const topSales = useMemo(
    () => [...saleRecords].sort((first, second) => second.price - first.price).slice(0, 5),
    [saleRecords]
  );

  const totalRevenue = monthlyData.reduce((sum, row) => sum + row.revenue, 0);
  const totalCost = monthlyData.reduce((sum, row) => sum + row.cost, 0);
  const totalProfit = totalRevenue - totalCost;
  const margin = totalRevenue > 0 ? ((totalProfit / totalRevenue) * 100).toFixed(1) : '0.0';
  const monthlyAverageFeed = feedHistory.length
    ? Math.round(feedHistory.reduce((sum, row) => sum + row.roughage + row.concentrate, 0) / feedHistory.length)
    : 0;

  return (
    <div className="animate-fadeIn">
      <div className="mb-5 flex items-center gap-3">
        <div className="clay-page-eyebrow">Financial Analysis</div>
        <div className="clay-stat-chip">두수 {cattleList.length}두</div>
        <div className="clay-stat-chip">월평균 급여 {monthlyAverageFeed}kg</div>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard title="연간 총매출" value={totalRevenue} accent="var(--chart-clay-5)" icon={<DollarSign size={18} />} />
        <KpiCard title="연간 총비용" value={totalCost} accent="var(--chart-clay-2)" icon={<TrendingDown size={18} />} />
        <KpiCard title="연간 순이익" value={totalProfit} accent="var(--chart-clay-1)" icon={<TrendingUp size={18} />} />
        <KpiCard title="이익률" value={`${margin}%`} accent={totalProfit >= 0 ? 'var(--chart-clay-1)' : 'var(--chart-clay-4)'} />
      </div>

      <section className="clay-page-section mb-6 p-5 md:p-6">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <div className="clay-page-eyebrow mb-3">Monthly Flow</div>
            <h2 className="text-xl font-bold text-[color:var(--color-text)]">월별 매출 · 비용 · 순이익 추이</h2>
          </div>
          <div className="text-right text-xs text-[color:var(--color-text-muted)]">최근 12개월 기준</div>
        </div>

        <div className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="color-mix(in srgb, var(--color-surface-border) 68%, transparent)" />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }} />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
                tickFormatter={(value) => `${Math.round(value / 10000)}만`}
              />
              <Tooltip
                formatter={(value) => `${formatMoney(value)}원`}
                contentStyle={{
                  borderRadius: 18,
                  border: '1px solid var(--color-surface-stroke)',
                  boxShadow: 'var(--shadow-md)',
                  background: 'var(--surface-gradient)',
                }}
              />
              <Legend />
              <Bar dataKey="revenue" name="매출" fill="var(--chart-clay-1)" radius={[8, 8, 0, 0]} />
              <Bar dataKey="cost" name="비용" fill="var(--chart-clay-2)" radius={[8, 8, 0, 0]} />
              <Bar dataKey="profit" name="순이익" fill="var(--chart-clay-5)" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="clay-page-section p-5 md:p-6">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <div className="clay-page-eyebrow mb-3">Cost Mix</div>
              <h2 className="text-xl font-bold text-[color:var(--color-text)]">비용 구조 분석</h2>
            </div>
            <div className="text-right text-xs text-[color:var(--color-text-muted)]">
              {hasExpenseData ? `${costStructure.length}개 카테고리` : '실데이터 없음'}
            </div>
          </div>

          {costStructure.length > 0 ? (
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={costStructure} cx="50%" cy="50%" innerRadius={62} outerRadius={92} paddingAngle={4} dataKey="value">
                    {costStructure.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => `${formatMoney(value)}원`}
                    contentStyle={{
                      borderRadius: 18,
                      border: '1px solid var(--color-surface-stroke)',
                      boxShadow: 'var(--shadow-md)',
                      background: 'var(--surface-gradient)',
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="clay-inset flex h-[280px] items-center justify-center rounded-[24px] px-6 text-center text-sm text-[color:var(--color-text-muted)]">
              비용 데이터가 아직 충분히 쌓이지 않았습니다.
            </div>
          )}
        </section>

        <section className="clay-page-section p-5 md:p-6">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <div className="clay-page-eyebrow mb-3">Top Sales</div>
              <h2 className="text-xl font-bold text-[color:var(--color-text)]">최고가 판매 이력</h2>
            </div>
            <div className="text-right text-xs text-[color:var(--color-text-muted)]">상위 5건</div>
          </div>

          <div className="grid gap-3">
            {topSales.length > 0 ? (
              topSales.map((sale, index) => (
                <div key={sale.id} className="clay-inset flex items-center justify-between gap-3 rounded-[22px] p-4">
                  <div className="flex min-w-0 items-center gap-3">
                    <div
                      className="flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold text-white"
                      style={{ background: RANK_COLORS[index] || 'var(--color-primary-custom)' }}
                    >
                      {index + 1}
                    </div>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold text-[color:var(--color-text)]">
                        {sale.cattleName || '이름 없음'}
                      </div>
                      <div className="truncate text-xs text-[color:var(--color-text-muted)]">{sale.buyerName}</div>
                    </div>
                  </div>
                  <div className="text-right text-sm font-bold text-[color:var(--color-text)]">{formatMoney(sale.price)}원</div>
                </div>
              ))
            ) : (
              <div className="clay-inset rounded-[24px] px-6 py-12 text-center text-sm text-[color:var(--color-text-muted)]">
                판매 기록이 아직 없습니다.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function KpiCard({ title, value, icon, accent }) {
  return (
    <div className="clay-page-section p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="text-xs font-semibold tracking-[0.08em] text-[color:var(--color-text-muted)]">{title}</span>
        {icon ? (
          <span
            className="inline-flex h-9 w-9 items-center justify-center rounded-full"
            style={{
              color: accent,
              background: `color-mix(in srgb, ${accent} 16%, white 84%)`,
            }}
          >
            {icon}
          </span>
        ) : null}
      </div>
      <div className="text-3xl font-bold text-[color:var(--color-text)]" style={{ fontFamily: 'var(--font-display-custom)' }}>
        {typeof value === 'number' ? `${formatMoney(value)}원` : value}
      </div>
    </div>
  );
}
