'use client';

import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';

import { formatMoney } from '@/lib/utils';

const REVENUE_KEY = 'revenue';
const EXPENSE_KEY = 'expense';
const PROFIT_KEY = 'profit';

export default function FinancialChartWidget({
  saleRecords = [],
  expenseRecords = [],
  seriesData = null,
}) {
  const salesByMonth = {};
  saleRecords.forEach((record) => {
    const date = new Date(record.saleDate);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    salesByMonth[key] = (salesByMonth[key] || 0) + (record.price || 0);
  });

  const expensesByMonth = {};
  expenseRecords.forEach((record) => {
    const date = new Date(record.date);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    expensesByMonth[key] = (expensesByMonth[key] || 0) + (record.amount || 0);
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
          [REVENUE_KEY]: row.revenue || 0,
          [EXPENSE_KEY]: Math.floor(row.expense || 0),
          [PROFIT_KEY]: row.profit || 0,
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
          <span style={{ fontSize: '22px', lineHeight: 1 }}>?</span>
          <div>
            <div
              style={{
                fontWeight: 800,
                fontSize: '17px',
                color: 'var(--color-text)',
                letterSpacing: '-0.01em',
              }}
            >
              Farm Financial Overview
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', marginTop: '3px' }}>
              Recent 6-month revenue, expense, and profit
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
          Unit: KRW
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
            <Bar dataKey={REVENUE_KEY} fill="var(--color-success)" radius={[6, 6, 0, 0]} barSize={14} name="Revenue" />
            <Bar dataKey={EXPENSE_KEY} fill="var(--color-warning)" radius={[6, 6, 0, 0]} barSize={14} name="Expense" />
            <Bar dataKey={PROFIT_KEY} fill="var(--color-primary)" radius={[6, 6, 0, 0]} barSize={14} name="Profit" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
