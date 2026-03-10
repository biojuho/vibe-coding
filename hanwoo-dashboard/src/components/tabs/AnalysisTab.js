
'use client';

import { useMemo } from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid, PieChart, Pie, Cell } from 'recharts';
import { formatMoney } from '@/lib/utils';
import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react';

const CATEGORY_CONFIG = {
  feed: { name: "사료비", color: "#FFBB28" },
  medicine: { name: "약품/진료", color: "#FF8042" },
  labor: { name: "인건비", color: "#00C49F" },
  other: { name: "기타", color: "#0088FE" },
};

export default function AnalysisTab({ saleRecords = [], feedHistory = [], cattleList = [], expenseRecords = [] }) {

  const hasExpenseData = expenseRecords.length > 0;

  // 1. Calculate Monthly Financials (Last 12 Months)
  const monthlyData = useMemo(() => {
    const data = {};
    const today = new Date();

    // Initialize last 12 months
    for(let i=11; i>=0; i--) {
        const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
        const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
        data[key] = { name: key, revenue: 0, cost: 0, profit: 0 };
    }

    // Add Revenue
    saleRecords.forEach(r => {
        const d = new Date(r.saleDate);
        const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
        if(data[key]) data[key].revenue += r.price;
    });

    // Add Costs from ExpenseRecords (real data)
    expenseRecords.forEach(e => {
        const d = new Date(e.date);
        const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
        if(data[key]) data[key].cost += e.amount;
    });

    // Calculate Profit
    Object.keys(data).forEach(key => {
        data[key].profit = data[key].revenue - data[key].cost;
    });

    return Object.values(data);
  }, [saleRecords, expenseRecords]);

  // 2. Cost Structure from real expense data
  const costStructure = useMemo(() => {
    if (!hasExpenseData) return [];
    const totals = {};
    expenseRecords.forEach(e => {
      const cat = e.category || 'other';
      totals[cat] = (totals[cat] || 0) + e.amount;
    });
    return Object.entries(totals).map(([cat, amount]) => ({
      name: CATEGORY_CONFIG[cat]?.name || cat,
      value: amount,
      color: CATEGORY_CONFIG[cat]?.color || "var(--color-text-muted)"
    }));
  }, [expenseRecords, hasExpenseData]);

  // 3. Top Sales
  const topSales = useMemo(() => {
    return [...saleRecords].sort((a,b) => b.price - a.price).slice(0, 5);
  }, [saleRecords]);

  // 4. KPI Cards
  const totalRevenue = monthlyData.reduce((acc, cur) => acc + cur.revenue, 0);
  const totalCost = monthlyData.reduce((acc, cur) => acc + cur.cost, 0);
  const totalProfit = totalRevenue - totalCost;
  const margin = totalRevenue > 0 ? (totalProfit / totalRevenue * 100).toFixed(1) : 0;

  return (
    <div className="animate-fadeIn">
        <div style={{fontSize:"20px", fontWeight:800, marginBottom:"20px", display:"flex", alignItems:"center", gap:"8px"}}>
            <span style={{fontSize:"24px"}}>📊</span> 경영 분석 (Financial Analysis)
        </div>

        {/* KPI Cards */}
        <div style={{display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(150px, 1fr))", gap:"12px", marginBottom:"24px"}}>
            <KPICard title="연간 총 매출" value={totalRevenue} icon={<DollarSign size={20}/>} color="blue" />
            <KPICard title="연간 총 비용" value={totalCost} icon={<TrendingDown size={20}/>} color="orange" />
            <KPICard title="연간 순수익" value={totalProfit} icon={<TrendingUp size={20}/>} color="green" />
            <div style={{background:"var(--color-bg-card)", padding:"16px", borderRadius:"12px", border:"1px solid var(--color-border)"}}>
                <div style={{fontSize:"13px", color:"var(--color-text-muted)", marginBottom:"4px"}}>순이익률 (Margin)</div>
                <div style={{fontSize:"24px", fontWeight:800, color: margin > 0 ? "var(--color-success)" : "var(--color-danger)"}}>{margin}%</div>
            </div>
        </div>

        {/* Main Chart */}
        <div style={{background:"var(--color-bg-card)", padding:"20px", borderRadius:"16px", marginBottom:"24px", boxShadow:"0 2px 10px rgba(0,0,0,0.03)"}}>
             <div style={{fontSize:"16px", fontWeight:700, marginBottom:"20px", color:"var(--color-text)"}}>월별 매출 및 손익 추이</div>
             <div style={{height:"300px", fontSize:"12px"}}>
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={monthlyData}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" axisLine={false} tickLine={false} />
                        <YAxis axisLine={false} tickLine={false} tickFormatter={(v)=>`${v/10000}만`} />
                        <Tooltip formatter={(value) => formatMoney(value)+"원"} />
                        <Legend />
                        <Bar dataKey="revenue" name="매출" fill="#4CAF50" radius={[4,4,0,0]} />
                        <Bar dataKey="cost" name="비용" fill="#FF9800" radius={[4,4,0,0]} />
                        <Bar dataKey="profit" name="순이익" fill="#2196F3" radius={[4,4,0,0]} />
                    </BarChart>
                </ResponsiveContainer>
             </div>
        </div>

        <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:"20px", marginBottom:"40px"}}>
            {/* Cost Breakdown */}
            <div style={{background:"var(--color-bg-card)", padding:"20px", borderRadius:"16px", boxShadow:"0 2px 10px rgba(0,0,0,0.03)"}}>
                <div style={{fontSize:"16px", fontWeight:700, marginBottom:"20px", color:"var(--color-text)"}}>비용 구조 분석</div>
                {costStructure.length > 0 ? (
                  <div style={{height:"250px"}}>
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie data={costStructure} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                                {costStructure.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip formatter={(v) => formatMoney(v)+"원"} />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div style={{height:"250px", display:"flex", alignItems:"center", justifyContent:"center", color:"var(--color-text-muted)", fontSize:"14px"}}>
                    비용 데이터가 등록되지 않았습니다.
                  </div>
                )}
            </div>

            {/* Top Sales */}
            <div style={{background:"var(--color-bg-card)", padding:"20px", borderRadius:"16px", boxShadow:"0 2px 10px rgba(0,0,0,0.03)"}}>
                <div style={{fontSize:"16px", fontWeight:700, marginBottom:"12px", color:"var(--color-text)"}}>🏆 최고가 판매 내역</div>
                <div style={{display:"flex", flexDirection:"column", gap:"8px"}}>
                    {topSales.map((sale, idx) => (
                        <div key={sale.id} style={{display:"flex", alignItems:"center", justifyContent:"space-between", padding:"10px", background:"var(--color-border-light)", borderRadius:"8px"}}>
                           <div style={{display:"flex", alignItems:"center", gap:"8px"}}>
                                <div style={{width:"24px", height:"24px", background: idx===0?"#FFD700":idx===1?"#C0C0C0":"#CD7F32", borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", color:"white", fontWeight:"bold", fontSize:"12px"}}>{idx+1}</div>
                                <div>
                                    <div style={{fontWeight:700, fontSize:"14px"}}>{sale.cattleName || '알 수 없음'}</div>
                                    <div style={{fontSize:"11px", color:"var(--color-text-muted)"}}>{sale.buyerName}</div>
                                </div>
                           </div>
                           <div style={{fontWeight:800, color:"var(--color-text)"}}>{formatMoney(sale.price)}원</div>
                        </div>
                    ))}
                    {topSales.length === 0 && <div style={{textAlign:"center", padding:"20px", color:"var(--color-text-muted)"}}>판매 기록이 없습니다.</div>}
                </div>
            </div>
        </div>
    </div>
  );
}

function KPICard({ title, value, icon, color }) {
    const colors = {
        blue: { bg: "#E3F2FD", text: "#1976D2" },
        orange: { bg: "#FFF3E0", text: "#F57C00" },
        green: { bg: "#E8F5E9", text: "#388E3C" }
    };
    const style = colors[color] || colors.blue;

    return (
        <div style={{background:"var(--color-bg-card)", padding:"16px", borderRadius:"12px", border:"1px solid var(--color-border)"}}>
            <div style={{display:"flex", justifyContent:"space-between", marginBottom:"8px"}}>
                <span style={{fontSize:"13px", color:"var(--color-text-muted)"}}>{title}</span>
                <div style={{padding:"4px", background: style.bg, color: style.text, borderRadius:"50%"}}>{icon}</div>
            </div>
            <div style={{fontSize:"18px", fontWeight:800, color:"var(--color-text)"}}>{formatMoney(value)}원</div>
        </div>
    );
}
