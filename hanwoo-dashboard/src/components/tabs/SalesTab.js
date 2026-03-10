import { useState, useEffect } from 'react';
import { formatMoney } from '@/lib/utils';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';
import MarketPriceWidget from '@/components/widgets/MarketPriceWidget';

export default function SalesTab({saleRecords, cattleList, onCreateSale, expenseRecords = []}){
  const [isAdding, setIsAdding] = useState(false);
  const [formData, setFormData] = useState({saleDate:"", price:"", cattleId:"", purchaser:"", grade:"1", notes:""});

  const [processedRecords, setProcessedRecords] = useState([]);
  const [safeTotalSales, setSafeTotalSales] = useState(0);
  const [safeTotalProfit, setSafeTotalProfit] = useState(0);
  const [safeChartData, setSafeChartData] = useState([]);

  useEffect(() => {
    if(!saleRecords) return;
    
    // Process records to calculate profit
    // Mock logic for cost: purchase price + feed cost (200,000 * monthAge)
    const processed = saleRecords.map(r => {
        const cow = cattleList?.find(c => c.id === r.cattleId) || {};

        // 실제 비용 데이터 조회
        const cattleExpenses = expenseRecords.filter(e => e.cattleId === r.cattleId);
        const purchaseCost = cow.purchasePrice || 0;
        const feedCost = cattleExpenses.filter(e => e.category === 'feed').reduce((s, e) => s + e.amount, 0);
        const medicalCost = cattleExpenses.filter(e => e.category === 'medicine').reduce((s, e) => s + e.amount, 0);
        const otherCost = cattleExpenses.filter(e => e.category !== 'feed' && e.category !== 'medicine').reduce((s, e) => s + e.amount, 0);
        const totalCost = purchaseCost + feedCost + medicalCost + otherCost;
        const hasExpenseData = cattleExpenses.length > 0 || purchaseCost > 0;

        return {
            ...r,
            name: cow.name || "Unknown",
            tagNumber: cow.tagNumber || "000-0000-0000",
            costs: { purchase: purchaseCost, feed: feedCost, medical: medicalCost, other: otherCost, total: totalCost },
            profit: hasExpenseData ? r.price - totalCost : null,
            hasExpenseData
        };
    }).sort((a,b) => new Date(b.saleDate) - new Date(a.saleDate));

    setProcessedRecords(processed);
    setSafeTotalSales(processed.reduce((sum, r) => sum + r.price, 0));
    const withProfit = processed.filter(r => r.profit !== null);
    setSafeTotalProfit(withProfit.reduce((sum, r) => sum + r.profit, 0));

    setSafeChartData(processed.slice(0, 5).reverse().map(r => ({
        name: r.name,
        판매금액: r.price,
        순이익: r.profit ?? 0
    })));

  }, [saleRecords, cattleList, expenseRecords]);

  const handleSubmit = () => {
      if(!formData.saleDate || !formData.price || !formData.cattleId) return alert("필수 정보를 입력해주세요.");
      onCreateSale({...formData, price: Number(formData.price)});
      setIsAdding(false);
      setFormData({saleDate:"", price:"", cattleId:"", purchaser:"", grade:"1", notes:""});
  };

  return (
    <div>
    <MarketPriceWidget />
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"14px"}}>
        <div style={{fontSize:"16px",fontWeight:800,color:"var(--color-text)"}}>💰 출하 및 매출 분석</div>
        <button onClick={()=>setIsAdding(!isAdding)} style={{fontSize:"13px",fontWeight:700,color:"var(--color-success)",background:"var(--color-bg-card)",border:"1px solid var(--color-success)",borderRadius:"8px",padding:"6px 12px",cursor:"pointer"}}>
            {isAdding ? "취소" : "+매출 등록"}
        </button>
    </div>

    {isAdding && (
      <div style={{background:"var(--color-bg)",borderRadius:"14px",padding:"16px",marginBottom:"16px",border:"1px solid var(--color-border)"}}>
        <div style={{fontSize:"14px",fontWeight:700,marginBottom:"12px"}}>새 매출 기록 등록</div>
        <div style={{display:"grid",gap:"10px"}}>
             <div>
                <label style={{fontSize:"12px",color:"var(--color-text-secondary)"}}>출하일자</label>
                <input type="date" value={formData.saleDate} onChange={e=>setFormData({...formData,saleDate:e.target.value})} style={{width:"100%",padding:"10px",borderRadius:"8px",border:"1px solid var(--color-border)"}} />
             </div>
             <div>
                <label style={{fontSize:"12px",color:"var(--color-text-secondary)"}}>판매가격 (원)</label>
                <input type="number" value={formData.price} onChange={e=>setFormData({...formData,price:e.target.value})} placeholder="예: 8500000" style={{width:"100%",padding:"10px",borderRadius:"8px",border:"1px solid var(--color-border)"}} />
             </div>
             <div>
                <label style={{fontSize:"12px",color:"var(--color-text-secondary)"}}>출하 개체</label>
                <select value={formData.cattleId} onChange={e=>setFormData({...formData,cattleId:e.target.value})} style={{width:"100%",padding:"10px",borderRadius:"8px",border:"1px solid var(--color-border)"}}>
                    <option value="">선택해주세요</option>
                    {cattleList && cattleList.map(c=>(
                        <option key={c.id} value={c.id}>{c.name} ({c.tagNumber})</option>
                    ))}
                </select>
             </div>
             <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"10px"}}>
                 <div>
                    <label style={{fontSize:"12px",color:"var(--color-text-secondary)"}}>등급</label>
                    <select value={formData.grade} onChange={e=>setFormData({...formData,grade:e.target.value})} style={{width:"100%",padding:"10px",borderRadius:"8px",border:"1px solid var(--color-border)"}}>
                        <option>1++</option><option>1+</option><option>1</option><option>2</option><option>3</option>
                    </select>
                 </div>
                 <div>
                    <label style={{fontSize:"12px",color:"var(--color-text-secondary)"}}>구매자</label>
                    <input value={formData.purchaser} onChange={e=>setFormData({...formData,purchaser:e.target.value})} placeholder="예: 남원축협" style={{width:"100%",padding:"10px",borderRadius:"8px",border:"1px solid var(--color-border)"}} />
                 </div>
             </div>
             <button onClick={handleSubmit} style={{width:"100%",padding:"12px",background:"var(--color-success)",color:"white",borderRadius:"8px",border:"none",fontWeight:700,marginTop:"8px",cursor:"pointer"}}>등록하기</button>
        </div>
      </div>
    )}

    {/* Summary Cards */}
    <div style={{display:"flex",gap:"10px",overflowX:"auto",paddingBottom:"10px",marginBottom:"10px"}}>
      <div style={{background:"linear-gradient(135deg, var(--color-primary), var(--color-primary-dark))",borderRadius:"14px",padding:"16px",flex:"1 0 140px",color:"white"}}>
        <div style={{fontSize:"11px",opacity:0.7}}>총 누적 매출</div>
        <div style={{fontSize:"20px",fontWeight:800,fontFamily:"'Outfit',sans-serif"}}>{formatMoney(safeTotalSales/10000)}만</div>
      </div>
      <div style={{background:"var(--color-bg-card)",borderRadius:"14px",padding:"16px",flex:"1 0 140px",border:"1px solid var(--color-border)"}}>
        <div style={{fontSize:"11px",color:"var(--color-text-muted)"}}>평균 순이익률</div>
        <div style={{fontSize:"20px",fontWeight:800,color: safeTotalProfit >= 0 ? "var(--color-success)" : "var(--color-danger)",fontFamily:"'Outfit',sans-serif"}}>{safeTotalSales > 0 ? (safeTotalProfit/safeTotalSales*100).toFixed(1) : 0}%</div>
      </div>
    </div>

    {/* Chart */}
    <div style={{background:"var(--color-bg-card)",borderRadius:"16px",padding:"20px",marginBottom:"16px",boxShadow:"0 2px 12px rgba(0,0,0,0.04)"}}>
      <div style={{fontSize:"13px",fontWeight:700,marginBottom:"16px",color:"var(--color-text)"}}>최근 5건 수익성 분석</div>
      <div style={{height:"200px",fontSize:"10px"}}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={safeChartData} margin={{top:5,right:5,left:-20,bottom:0}}>
            <XAxis dataKey="name" tickLine={false} axisLine={false} />
            <YAxis tickLine={false} axisLine={false} tickFormatter={(v)=>`${v/10000}`} />
            <Tooltip contentStyle={{borderRadius:"8px",border:"none",boxShadow:"0 4px 12px rgba(0,0,0,0.1)"}} formatter={(v)=>`${formatMoney(v)}원`} />
            <Legend />
            <Bar dataKey="판매금액" fill="#BCAAA4" radius={[4,4,0,0]} barSize={20} />
            <Bar dataKey="순이익" fill="var(--color-primary-light)" radius={[4,4,0,0]} barSize={20} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>

    {/* Record List */}
    <div style={{fontSize:"14px",fontWeight:700,marginBottom:"10px",color:"var(--color-text)"}}>출하 이력</div>
    <div style={{display:"flex",flexDirection:"column",gap:"10px"}}>
      {processedRecords.length === 0 ? <div style={{textAlign:"center",padding:"20px",color:"var(--color-text-muted)"}}>출하 내역이 없습니다.</div> :
      processedRecords.map((r, i)=>(
        <div key={r.id || i} style={{background:"var(--color-bg-card)",borderRadius:"14px",padding:"14px",border:"1px solid var(--color-border)"}}>
          <div style={{display:"flex",justifyContent:"space-between",marginBottom:"8px"}}>
            <div><div style={{fontWeight:700,fontSize:"14px"}}>{r.name} ({r.grade})</div><div style={{fontSize:"11px",color:"var(--color-text-muted)"}}>{r.tagNumber}</div></div>
            <div style={{textAlign:"right"}}><div style={{fontWeight:800,fontSize:"15px",color:"var(--color-primary-light)"}}>{formatMoney(r.salePrice)}원</div><div style={{fontSize:"11px",color:"var(--color-text-muted)"}}>{r.auctionLocation || r.purchaser}</div></div>
          </div>
          <div style={{background:"var(--color-bg)",borderRadius:"8px",padding:"8px 12px",display:"flex",justifyContent:"space-between",fontSize:"12px"}}>
            {r.hasExpenseData ? (
              <>
                <span style={{color:"var(--color-text-secondary)"}}>총 비용: {formatMoney(r.costs.total)}원</span>
                <span style={{fontWeight:700,color:r.profit >= 0 ? "var(--color-success)" : "var(--color-danger)"}}>순수익: {r.profit >= 0 ? "+" : ""}{formatMoney(r.profit)}원</span>
              </>
            ) : (
              <>
                <span style={{color:"var(--color-text-muted)",fontStyle:"italic"}}>비용 미등록</span>
                <span style={{color:"var(--color-text-muted)"}}>순수익 산출 불가</span>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
    </div>
  );
}
