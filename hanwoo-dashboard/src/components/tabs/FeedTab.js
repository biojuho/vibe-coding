import { useState, useMemo } from 'react';
import { BREED_STATUS_OPTIONS, STATUS_COLORS, BUILDINGS } from '@/lib/constants';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function FeedTab({ cattle, feedStandards = [], feedHistory = [], onRecordFeed }) {
  const [selectedBuilding, setSelectedBuilding] = useState(null);
  const [recordForm, setRecordForm] = useState({
    date: new Date().toISOString().split('T')[0],
    roughage: '',
    concentrate: '',
    note: ''
  });

  // Calculate Feed Standards
  const standardsMap = useMemo(() => {
    const map = {};
    if (feedStandards) {
      feedStandards.forEach(s => {
        map[s.status] = s;
      });
    }
    return map;
  }, [feedStandards]);

  const feedSummary = useMemo(() => {
    const summary = {};
    BREED_STATUS_OPTIONS.forEach(st => {
      const count = cattle.filter(c => c.status === st).length;
      const std = standardsMap[st];
      if (count > 0 && std) summary[st] = {
        count,
        roughageTotal: (std.roughageKg * count).toFixed(1),
        concentrateTotal: (std.concentrateKg * count).toFixed(1),
        roughage: std.roughage,
        roughageKg: std.roughageKg,
        concentrate: std.concentrate,
        concentrateKg: std.concentrateKg,
        note: std.note
      };
    });
    return summary;
  }, [cattle, standardsMap]);

  const totalStandardRoughage = Object.values(feedSummary).reduce((s, v) => s + parseFloat(v.roughageTotal), 0).toFixed(1);
  const totalStandardConcentrate = Object.values(feedSummary).reduce((s, v) => s + parseFloat(v.concentrateTotal), 0).toFixed(1);

  // Filter cattle by building if selected
  const filteredCattle = useMemo(() => {
    if (!selectedBuilding) return cattle;
    return cattle.filter(c => c.buildingId === selectedBuilding);
  }, [cattle, selectedBuilding]);

  const handleSubmit = () => {
    if (!recordForm.roughage || !recordForm.concentrate) return alert("급여량을 입력하세요.");
    if (!selectedBuilding) {
        if(!confirm("전체 축사에 일괄 기록하시겠습니까?")) return;
    }

    if(!selectedBuilding) return alert("축사를 선택해주세요.");

    onRecordFeed({
      ...recordForm,
      buildingId: selectedBuilding,
    });

    setRecordForm(prev => ({ ...prev, roughage: '', concentrate: '', note: '' }));
  };

  // Prepare Chart Data
  const chartData = useMemo(() => {
    const grouped = {};
    const sorted = [...feedHistory].sort((a,b) => new Date(a.date) - new Date(b.date));

    sorted.forEach(rec => {
        const d = new Date(rec.date).toLocaleDateString('ko-KR', {month:'short', day:'numeric'});
        if(!grouped[d]) grouped[d] = { date: d, roughage: 0, concentrate: 0 };
        grouped[d].roughage += rec.roughage;
        grouped[d].concentrate += rec.concentrate;
    });
    return Object.values(grouped);
  }, [feedHistory]);

  return (
    <div>
      <div style={{ fontSize: "16px", fontWeight: 800, color: "var(--color-text)", marginBottom: "14px" }}>🌾 사료 급여 모니터링</div>

      {/* Building Selection */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "12px", overflowX:"auto", paddingBottom:"4px" }}>
        <button
            onClick={() => setSelectedBuilding(null)}
            style={{ padding: "8px 16px", borderRadius: "20px", border: "1px solid var(--color-border)", background: !selectedBuilding ? "var(--color-primary)" : "var(--color-bg-card)", color: !selectedBuilding ? "var(--color-bg)" : "var(--color-text)", fontWeight: 700, fontSize:"13px", cursor:"pointer" }}
        >
            전체
        </button>
        {BUILDINGS.map(b => (
          <button
            key={b.id}
            onClick={() => setSelectedBuilding(b.id)}
            style={{ padding: "8px 16px", borderRadius: "20px", border: "1px solid var(--color-border)", background: selectedBuilding === b.id ? "var(--color-primary)" : "var(--color-bg-card)", color: selectedBuilding === b.id ? "var(--color-bg)" : "var(--color-text)", fontWeight: 700, fontSize:"13px", cursor: "pointer", whiteSpace:"nowrap" }}
          >
            {b.name}
          </button>
        ))}
      </div>

      {/* Standard Calculation (Guide) */}
      <div style={{ background: "linear-gradient(135deg,#8BC34A,#558B2F)", borderRadius: "16px", padding: "18px", color: "white", marginBottom: "20px" }}>
        <div style={{ fontSize: "13px", opacity: 0.9, marginBottom: "8px", display:"flex", justifyContent:"space-between" }}>
            <span>📊 표준 급여 가이드 ({selectedBuilding ? BUILDINGS.find(b=>b.id===selectedBuilding).name : "전체"})</span>
            <span>{filteredCattle.length}두</span>
        </div>
        <div style={{ display: "flex", gap: "20px" }}>
          <div>
            <div style={{ fontSize: "24px", fontWeight: 800, fontFamily: "'Outfit',sans-serif" }}>
                {selectedBuilding
                    ? filteredCattle.reduce((s,c)=>s+(standardsMap[c.status]?.roughageKg||0),0).toFixed(1)
                    : totalStandardRoughage}kg
            </div>
            <div style={{ fontSize: "11px", opacity: 0.8 }}>조사료 권장량</div>
          </div>
          <div>
            <div style={{ fontSize: "24px", fontWeight: 800, fontFamily: "'Outfit',sans-serif" }}>
                {selectedBuilding
                    ? filteredCattle.reduce((s,c)=>s+(standardsMap[c.status]?.concentrateKg||0),0).toFixed(1)
                    : totalStandardConcentrate}kg
            </div>
            <div style={{ fontSize: "11px", opacity: 0.8 }}>농후사료 권장량</div>
          </div>
        </div>
      </div>

      {/* Input Form */}
      {selectedBuilding && (
          <div style={{ background: "var(--color-bg-card)", borderRadius: "20px", padding: "24px", marginBottom: "20px", border:"1px solid var(--color-border)", boxShadow:"var(--shadow-sm)" }}>
            <div style={{fontSize:"16px", fontWeight:700, marginBottom:"16px", color:"var(--color-text)", display:"flex", alignItems:"center", gap:"8px"}}>
                <span style={{background:"var(--color-border-light)", padding:"4px 8px", borderRadius:"6px", fontSize:"18px"}}>📝</span>
                실 급여량 기록 <span style={{fontSize:"13px", fontWeight:400, color:"var(--color-text-muted)"}}>({BUILDINGS.find(b=>b.id===selectedBuilding).name})</span>
            </div>

            <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:"16px", marginBottom:"16px"}}>
                <div style={{position:"relative"}}>
                    <label style={{fontSize:"12px", color:"var(--color-text-secondary)", fontWeight:600, marginBottom:"6px", display:"block"}}>조사료 (Roughage)</label>
                    <div style={{position:"relative"}}>
                        <input
                            type="number"
                            value={recordForm.roughage}
                            onChange={e=>setRecordForm({...recordForm, roughage:e.target.value})}
                            style={{width:"100%", padding:"14px", borderRadius:"12px", border:"2px solid var(--color-border)", fontSize:"16px", fontWeight:700, fontFamily:"'Outfit', sans-serif", color:"var(--color-text)", background:"var(--color-bg)", outline:"none", transition:"all 0.2s"}}
                            placeholder="0.0"
                        />
                        <span style={{position:"absolute", right:"14px", top:"50%", transform:"translateY(-50%)", fontSize:"12px", color:"var(--color-text-muted)", fontWeight:600}}>kg</span>
                    </div>
                </div>
                <div style={{position:"relative"}}>
                    <label style={{fontSize:"12px", color:"var(--color-text-secondary)", fontWeight:600, marginBottom:"6px", display:"block"}}>농후사료 (Concentrate)</label>
                    <div style={{position:"relative"}}>
                        <input
                            type="number"
                            value={recordForm.concentrate}
                            onChange={e=>setRecordForm({...recordForm, concentrate:e.target.value})}
                            style={{width:"100%", padding:"14px", borderRadius:"12px", border:"2px solid var(--color-border)", fontSize:"16px", fontWeight:700, fontFamily:"'Outfit', sans-serif", color:"var(--color-text)", background:"var(--color-bg)", outline:"none", transition:"all 0.2s"}}
                            placeholder="0.0"
                        />
                        <span style={{position:"absolute", right:"14px", top:"50%", transform:"translateY(-50%)", fontSize:"12px", color:"var(--color-text-muted)", fontWeight:600}}>kg</span>
                    </div>
                </div>
            </div>

            <div style={{marginBottom:"16px"}}>
                 <label style={{fontSize:"12px", color:"var(--color-text-secondary)", fontWeight:600, marginBottom:"6px", display:"block"}}>특이사항 메모</label>
                 <textarea
                    placeholder="오늘 소들의 상태나 특이사항이 있다면 기록해주세요."
                    value={recordForm.note} onChange={e=>setRecordForm({...recordForm, note:e.target.value})}
                    style={{width:"100%", padding:"14px", borderRadius:"12px", border:"2px solid var(--color-border)", fontFamily:"inherit", fontSize:"14px", resize:"none", height:"80px", outline:"none", transition:"all 0.2s", background:"var(--color-bg)", color:"var(--color-text)"}}
                />
            </div>

            <button
                onClick={handleSubmit}
                style={{
                    width:"100%",
                    background:"linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-light) 100%)",
                    color:"var(--color-bg)",
                    padding:"16px",
                    borderRadius:"14px",
                    fontWeight:700,
                    fontSize:"15px",
                    border:"none",
                    cursor:"pointer",
                    boxShadow:"var(--shadow-md)",
                    transition:"transform 0.1s"
                }}
                onMouseDown={e => e.target.style.transform = "scale(0.98)"}
                onMouseUp={e => e.target.style.transform = "scale(1)"}
                onMouseLeave={e => e.target.style.transform = "scale(1)"}
            >
                기록 저장하기
            </button>
          </div>
      )}

      {/* Chart */}
      <div style={{ background: "var(--color-bg-card)", borderRadius: "16px", padding: "16px", border:"1px solid var(--color-border)", height:"300px" }}>
        <div style={{fontSize:"14px", fontWeight:700, marginBottom:"16px", color:"var(--color-text)"}}>📈 최근 섭취량 추이</div>
        <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" />
                <XAxis dataKey="date" tick={{fontSize:11, fill:'var(--color-text-muted)'}} axisLine={false} tickLine={false} />
                <YAxis tick={{fontSize:11, fill:'var(--color-text-muted)'}} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{borderRadius:'8px', border:'none', boxShadow:'var(--shadow-md)', background:'var(--color-bg-card)'}} />
                <Legend />
                <Line type="monotone" dataKey="roughage" name="조사료" stroke="#8BC34A" strokeWidth={3} dot={{r:3}} activeDot={{r:5}} />
                <Line type="monotone" dataKey="concentrate" name="농후사료" stroke="#FF9800" strokeWidth={3} dot={{r:3}} activeDot={{r:5}} />
            </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Recent History List */}
      <div style={{marginTop:"20px"}}>
         <div style={{fontSize:"14px", fontWeight:700, marginBottom:"10px", color:"var(--color-text)"}}>최근 기록</div>
         <div style={{display:"flex", flexDirection:"column", gap:"8px"}}>
            {feedHistory.slice(0, 5).map(rec => (
                <div key={rec.id} style={{background:"var(--color-bg-card)", borderRadius:"10px", padding:"12px", border:"1px solid var(--color-border)", display:"flex", justifyContent:"space-between", alignItems:"center"}}>
                    <div>
                        <div style={{fontSize:"13px", fontWeight:600, color:"var(--color-text)"}}>{new Date(rec.date).toLocaleDateString()} <span style={{fontSize:"11px", color:"var(--color-text-muted)", fontWeight:400}}>{BUILDINGS.find(b=>b.id===rec.buildingId)?.name}</span></div>
                        {rec.note && <div style={{fontSize:"11px", color:"var(--color-text-muted)", marginTop:"2px"}}>{rec.note}</div>}
                    </div>
                    <div style={{fontSize:"12px", fontWeight:600}}>
                        <span style={{color:"#558B2F"}}>조 {rec.roughage}</span> · <span style={{color:"#E65100"}}>농 {rec.concentrate}</span>
                    </div>
                </div>
            ))}
         </div>
      </div>
    </div>
  );
}
