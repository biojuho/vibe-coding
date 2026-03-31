'use client';

import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { formatMoney } from '@/lib/utils';

export default function FinancialChartWidget({ saleRecords = [], feedHistory = [], expenseRecords = [] }) {
  // 1. Group Sales by Month (Revenue)
  const salesByMonth = {};
  saleRecords.forEach(r => {
      const d = new Date(r.saleDate);
      const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
      if(!salesByMonth[key]) salesByMonth[key] = 0;
      salesByMonth[key] += r.price;
  });

  // 2. Group Expenses by Month (from real ExpenseRecords)
  const expensesByMonth = {};
  expenseRecords.forEach(e => {
      const d = new Date(e.date);
      const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
      if(!expensesByMonth[key]) expensesByMonth[key] = 0;
      expensesByMonth[key] += e.amount;
  });

  // 3. Merge Data — last 6 months
  const today = new Date();
  const recentKeys = [];
  for(let i=5; i>=0; i--){
      const d = new Date(today.getFullYear(), today.getMonth()-i, 1);
      recentKeys.push(`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`);
  }

  const chartData = recentKeys.map(key => ({
      name: key,
      매출: salesByMonth[key] || 0,
      비용: Math.floor(expensesByMonth[key] || 0),
      수익: (salesByMonth[key]||0) - (expensesByMonth[key]||0)
  }));

  return (
    <div
      className="card animate-fadeInUp"
      style={{
        marginBottom: "20px",
        padding: "22px",
        animationDelay: "50ms"
      }}
    >
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "22px"
      }}>
        <div style={{display: "flex", alignItems: "center", gap: "10px"}}>
          <span style={{fontSize: "20px"}}>📈</span>
          <div>
            <div style={{fontWeight: 800, fontSize: "16px", color: "var(--color-text)"}}>농장 경영 분석</div>
            <div style={{fontSize: "12px", color: "var(--color-text-muted)", marginTop: "2px"}}>최근 6개월 매출/비용/수익</div>
          </div>
        </div>
        <div style={{
          fontSize: "11px",
          color: "var(--color-text-secondary)",
          background: "var(--color-border-light)",
          padding: "6px 10px",
          borderRadius: "var(--radius-sm)",
          fontWeight: 500
        }}>단위: 원</div>
      </div>

      <div style={{height: "260px", fontSize: "11px"}}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{top: 10, right: 0, left: -20, bottom: 0}}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" />
            <XAxis
              dataKey="name"
              tickLine={false}
              axisLine={false}
              tick={{fill: 'var(--color-text-muted)', fontSize: 11}}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${(v/10000).toLocaleString()}만`}
              tick={{fill: 'var(--color-text-muted)', fontSize: 11}}
            />
            <Tooltip
              contentStyle={{
                borderRadius: "var(--radius-md)",
                border: "none",
                boxShadow: "var(--shadow-lg)",
                background: "var(--color-bg-card)",
                padding: "12px 16px"
              }}
              formatter={(value, name) => [formatMoney(value) + "원", name]}
              labelStyle={{color: "var(--color-text-muted)", marginBottom: "10px", fontWeight: 600}}
              cursor={{fill: 'rgba(0,0,0,0.03)'}}
            />
            <Legend
              wrapperStyle={{paddingTop: "14px"}}
              iconType="circle"
              iconSize={8}
            />
            <Bar
              dataKey="매출"
              fill="var(--color-success)"
              radius={[6, 6, 0, 0]}
              barSize={14}
              name="매출 (Revenue)"
            />
            <Bar
              dataKey="비용"
              fill="var(--color-warning)"
              radius={[6, 6, 0, 0]}
              barSize={14}
              name="비용 (Expense)"
            />
            <Bar
              dataKey="수익"
              fill="var(--color-primary)"
              radius={[6, 6, 0, 0]}
              barSize={14}
              name="순수익 (Profit)"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
