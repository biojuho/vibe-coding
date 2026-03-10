import { useState } from 'react';
import { STATUS_COLORS, BUILDINGS } from '@/lib/constants';
import { getCalvingDate, getDaysUntilCalving, isCalvingAlert, toInputDate, formatDate } from '@/lib/utils';
import { inputStyle, btnPrimary } from '@/components/ui/common';

export default function CalvingTab({cattle, onUpdateCattle, onCreateCattle}){
  const pregnantCows = cattle.filter(c=>c.status==="임신우").sort((a,b)=>new Date(a.pregnancyDate)-new Date(b.pregnancyDate));
  const [selectedCowId, setSelectedCowId] = useState(null);
  const [calvingDate, setCalvingDate] = useState("");
  const [calfGender, setCalfGender] = useState("수");

  const handleCalving = () => {
    if(!calvingDate) return alert("분만일자를 입력해주세요.");
    const cow = cattle.find(c=>c.id===selectedCowId);
    if(!cow) return;

    const updatedMother = { ...cow, status: "번식우", pregnancyDate: null, lastEstrus: null, memo: cow.memo ? cow.memo + `\n[분만] ${calvingDate} ${calfGender} 송아지 분만` : `[분만] ${calvingDate} ${calfGender} 송아지 분만` };
    onUpdateCattle(updatedMother);

    const newCalf = {
      tagNumber: `KR0000-${String(Math.floor(Math.random()*900000)+100000)}`,
      name: `${cow.name}의 송아지`,
      buildingId: cow.buildingId,
      penNumber: cow.penNumber,
      gender: calfGender,
      birthDate: new Date(calvingDate).toISOString(),
      weight: 25,
      status: "송아지",
      geneticInfo: { father: cow.geneticFather || "미상", mother: cow.tagNumber, grade: "-" },
      memo: `모: ${cow.tagNumber} (${cow.name})`
    };

    if(onCreateCattle) {
        onCreateCattle(newCalf);
    } else {
        console.error("onCreateCattle prop missing");
        alert("시스템 오류: 송아지 등록 기능을 찾을 수 없습니다.");
    }

    setSelectedCowId(null);
  };

  return <div>
    <div style={{fontSize:"16px",fontWeight:800,color:"var(--color-text)",marginBottom:"14px"}}>🍼 분만 예정우 관리</div>

    <div style={{display:"flex",flexDirection:"column",gap:"10px"}}>
      {pregnantCows.length === 0 ? <div style={{textAlign:"center",padding:"40px",color:"var(--color-text-muted)",fontSize:"14px"}}>임신우가 없습니다.</div> :
      pregnantCows.map(c=>{
        const d = getDaysUntilCalving(c.pregnancyDate);
        const alert = isCalvingAlert(c.pregnancyDate);
        const buildingName = BUILDINGS.find(b=>b.id===c.buildingId)?.name;
        const isSelected = selectedCowId === c.id;

        return <div key={c.id} style={{background:alert?"linear-gradient(135deg, var(--color-warning-light) 0%, var(--color-warning-light) 100%)":"var(--color-bg-card)",borderRadius:"16px",padding:"20px",border:alert?"2px solid var(--color-warning)":"1px solid var(--color-border)", boxShadow: isSelected ? "var(--shadow-md)" : "none", transition: "all 0.3s ease"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:"12px"}}>
            <div>
              <div style={{display:"flex",alignItems:"center",gap:"8px",marginBottom:"6px"}}>
                <span style={{fontWeight:800,fontSize:"18px",color:"var(--color-text)"}}>{c.name}</span>
                <span style={{fontSize:"12px",background:"#F3E5F5",color:"#7B1FA2",padding:"2px 8px",borderRadius:"6px",fontWeight:700}}>임신우</span>
                {alert && <span style={{fontSize:"12px",background:"var(--color-warning)",color:"white",padding:"2px 8px",borderRadius:"6px",fontWeight:700, animation: "pulse 2s infinite"}}>임박 D-{d}</span>}
              </div>
              <div style={{fontSize:"13px",color:"var(--color-text-secondary)"}}>{buildingName} {c.penNumber}번 · {c.tagNumber}</div>
            </div>
            <div style={{textAlign:"right"}}>
              <div style={{fontSize:"12px",color:"var(--color-text-muted)",marginBottom:"2px"}}>분만예정일</div>
              <div style={{fontSize:"16px",fontWeight:700,fontFamily:"'Outfit',sans-serif",color:alert?"#E65100":"var(--color-text)"}}>{formatDate(getCalvingDate(c.pregnancyDate))}</div>
            </div>
          </div>

          {isSelected ? (
            <div style={{background:"var(--color-bg)",borderRadius:"12px",padding:"16px",marginTop:"16px",border:"1px solid var(--color-border)"}}>
              <div style={{fontSize:"14px",fontWeight:700,marginBottom:"12px",color:"var(--color-text)"}}>🎉 분만 처리</div>
              <div style={{display:"grid", gridTemplateColumns: "1fr 1fr", gap:"12px",marginBottom:"16px"}}>
                <div>
                    <label style={{fontSize:"12px",color:"var(--color-text-secondary)",display:"block",marginBottom:"4px"}}>분만일자</label>
                    <input type="date" value={calvingDate} onChange={(e)=>setCalvingDate(e.target.value)} style={{...inputStyle, width: "100%"}} />
                </div>
                <div>
                    <label style={{fontSize:"12px",color:"var(--color-text-secondary)",display:"block",marginBottom:"4px"}}>송아지 성별</label>
                    <select value={calfGender} onChange={(e)=>setCalfGender(e.target.value)} style={{...inputStyle, width: "100%"}}>
                        <option value="수">수송아지 ♂</option>
                        <option value="암">암송아지 ♀</option>
                    </select>
                </div>
              </div>
              <div style={{display:"flex",gap:"8px"}}>
                <button onClick={handleCalving} style={{...btnPrimary, flex: 1, padding: "12px"}}>분만 완료 및 송아지 등록</button>
                <button onClick={()=>setSelectedCowId(null)} style={{...btnPrimary, background:"var(--color-border)", color: "var(--color-text)", flex: 0.4}}>취소</button>
              </div>
            </div>
          ) : (
            <button onClick={()=>{setSelectedCowId(c.id); setCalvingDate(toInputDate(new Date()));}} style={{width:"100%",padding:"12px",borderRadius:"10px",border:"1px solid var(--color-border)",background:"var(--color-bg-card)",color:"var(--color-text-secondary)",fontSize:"14px",fontWeight: 600, cursor:"pointer", transition: "all 0.2s hover", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px"}}>
              <span>🍼 분만 보고하기</span>
            </button>
          )}
        </div>;
      })}
    </div>
    <style jsx>{`
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
    `}</style>
  </div>;
}
