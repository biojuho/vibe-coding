'use client';

import { BarChart3 } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';

import { formatMoney, toFiniteNumber } from '@/lib/utils';

const REVENUE_KEY = 'revenue';
const EXPENSE_KEY = 'expense';
const PROFIT_KEY = 'profit';

function toMonthKey(value) {
  const date = value instanceof Date ? new Date(value.getTime()) : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  if (typeof value === 'string') {
    const dateKey = value.trim().slice(0, 10);
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) {
      const strictDate = new Date(`${dateKey}T00:00:00.000Z`);
      if (Number.isNaN(strictDate.getTime()) || strictDate.toISOString().slice(0, 10) !== dateKey) {
        return null;
      }
    }
  }

  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
}

export default function FinancialChartWidget({
  saleRecords = [],
  expenseRecords = [],
  seriesData = null,
}) {
  const salesByMonth = {};
  saleRecords.forEach((record) => {
    const key = toMonthKey(record.saleDate);
    if (!key) return;
    salesByMonth[key] = (salesByMonth[key] || 0) + toFiniteNumber(record.price);
  });

  const expensesByMonth = {};
  expenseRecords.forEach((record) => {
    const key = toMonthKey(record.date);
    if (!key) return;
    expensesByMonth[key] = (expensesByMonth[key] || 0) + toFiniteNumber(record.amount);
  });

  const today = new Date();
  const recentKeys = [];
  for (let index = 5; index >= 0; index -= 1) {
    const date = new Date(today.getFullYear(), today.getMonth() - index, 1);
    recentKeys.push(`${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`);
  }

  const fallbackChartData = recentKeys.map((key) => ({
    name: key,
    [REVENUE_KEY]: salesByMonth[key] || 0,
    [EXPENSE_KEY]: Math.floor(expensesByMonth[key] || 0),
    [PROFIT_KEY]: (salesByMonth[key] || 0) - (expensesByMonth[key] || 0),
  }));

  const chartData =
    Array.isArray(seriesData) && seriesData.length > 0
      ? seriesData.map((row) => ({
          name: row.month,
          [REVENUE_KEY]: toFiniteNumber(row.revenue),
          [EXPENSE_KEY]: Math.floor(toFiniteNumber(row.expense)),
          [PROFIT_KEY]: toFiniteNumber(row.profit),
        }))
      : fallbackChartData;

  return (
    <div
      className="card animate-fadeInUp"
      style={{
        marginBottom: '22px',
        padding: '24px',
        animationDelay: '50ms',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '24px',
          paddingBottom: '16px',
          borderBottom: '1px solid color-mix(in srgb, var(--color-border-custom) 30%, transparent)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <BarChart3 size={22} aria-hidden="true" style={{ color: 'var(--chart-clay-1)', flexShrink: 0 }} />
          <div>
            <div
              style={{
                fontWeight: 800,
                fontSize: '17px',
                color: 'var(--color-text)',
                letterSpacing: '-0.01em',
              }}
            >
              농장 재무 흐름
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginTop: '3px' }}>
              최근 6개월 매출, 비용, 이익 추이
            </div>
          </div>
        </div>
        <div
          style={{
            fontSize: '11px',
            color: 'var(--color-text-secondary)',
            background: 'var(--color-border-light)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-sm)',
            fontWeight: 600,
            letterSpacing: '0.02em',
          }}
        >
          단위: 원
        </div>
      </div>

      <div style={{ height: '260px', fontSize: '11px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" />
            <XAxis
              dataKey="name"
              tickLine={false}
              axisLine={false}
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${(value / 10000).toLocaleString()}만`}
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 'var(--radius-md)',
                border: 'none',
                boxShadow: 'var(--shadow-lg)',
                background: 'var(--color-bg-card)',
                padding: '12px 16px',
              }}
              formatter={(value, name) => [formatMoney(value) + '원', name]}
              labelStyle={{ color: 'var(--color-text-muted)', marginBottom: '10px', fontWeight: 600 }}
              cursor={{ fill: 'rgba(0,0,0,0.03)' }}
            />
            <Legend wrapperStyle={{ paddingTop: '14px' }} iconType="circle" iconSize={8} />
            <Bar dataKey={REVENUE_KEY} fill="var(--color-success)" radius={[6, 6, 0, 0]} barSize={14} name="매출" />
            <Bar dataKey={EXPENSE_KEY} fill="var(--color-warning)" radius={[6, 6, 0, 0]} barSize={14} name="비용" />
            <Bar dataKey={PROFIT_KEY} fill="var(--color-primary)" radius={[6, 6, 0, 0]} barSize={14} name="이익" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
