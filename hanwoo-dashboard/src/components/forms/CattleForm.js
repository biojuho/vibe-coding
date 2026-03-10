import { useState, useEffect } from 'react';
import { BUILDINGS, BREED_STATUS_OPTIONS } from '@/lib/constants';
import { toInputDate } from '@/lib/utils';
import { inputStyle, labelStyle, btnPrimary, btnSecondary, BackIcon } from '@/components/ui/common';
import { lookupCattleTag } from '@/lib/actions';

export default function CattleForm({ cattle, onSubmit, onCancel }) {
  const [formData, setFormData] = useState({
    name: "", tagNumber: "", buildingId: BUILDINGS[0].id, penNumber: 1, gender: "암",
    birthDate: "", status: "송아지", weight: "",
    geneticInfo: { father: "", mother: "", grade: "-" }, memo: "",
    purchasePrice: "", purchaseDate: ""
  });
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupMsg, setLookupMsg] = useState(null);

  useEffect(() => {
    if (cattle) {
      setFormData({
        ...cattle,
        birthDate: toInputDate(cattle.birthDate),
        geneticInfo: cattle.geneticInfo || { father: "", mother: "", grade: "-" },
        purchasePrice: cattle.purchasePrice || "",
        purchaseDate: cattle.purchaseDate ? toInputDate(cattle.purchaseDate) : ""
      });
    }
  }, [cattle]);

  const handleLookup = async () => {
    if (!formData.tagNumber) return setLookupMsg({ ok: false, text: "이력번호를 입력하세요." });
    setLookupLoading(true);
    setLookupMsg(null);
    try {
      const res = await lookupCattleTag(formData.tagNumber);
      if (res.success && res.data) {
        const d = res.data;
        const updates = {};
        if (d.birthDate) {
          const raw = d.birthDate.replace(/[-\/]/g, "");
          if (raw.length === 8) updates.birthDate = `${raw.slice(0,4)}-${raw.slice(4,6)}-${raw.slice(6,8)}`;
        }
        if (d.gender) updates.gender = d.gender;
        setFormData(prev => ({ ...prev, ...updates }));
        setLookupMsg({ ok: true, text: `조회 완료 (${d.breed || "한우"})` });
      } else {
        setLookupMsg({ ok: false, text: res.message || "조회 실패" });
      }
    } catch {
      setLookupMsg({ ok: false, text: "조회 중 오류 발생" });
    } finally {
      setLookupLoading(false);
    }
  };

  const handleSubmit = () => {
    if (!formData.name || !formData.tagNumber) return alert("이름과 이력번호는 필수입니다.");
    
    // Validate Pen Capacity (Simple logic)
    const penLimit = 5; // Example limit
    // In a real app, we'd check against existing cattle in that pen, passed as prop
    
    onSubmit({
      ...formData,
      id: cattle ? cattle.id : `new_${Date.now()}`,
      birthDate: new Date(formData.birthDate).toISOString(),
      weight: Number(formData.weight),
      weightHistory: cattle ? cattle.weightHistory : [],
      purchasePrice: formData.purchasePrice ? Number(formData.purchasePrice) : null,
      purchaseDate: formData.purchaseDate ? new Date(formData.purchaseDate).toISOString() : null
    });
  };

  return (
    <div className="modal-overlay" style={{alignItems:"flex-start",paddingTop:"20px"}}>
      <div
        className="animate-slideInUp"
        style={{
          background:"var(--color-bg)",
          width:"100%",
          maxWidth:"500px",
          minHeight:"100vh",
          padding:"20px",
          overflowY:"auto"
        }}
      >
        {/* Header */}
        <div style={{
          display:"flex",
          alignItems:"center",
          marginBottom:"24px",
          gap:"14px"
        }}>
          <button
            onClick={onCancel}
            className="btn btn-ghost btn-icon"
            style={{width:"40px",height:"40px"}}
          ><BackIcon/></button>
          <div style={{fontSize:"20px",fontWeight:800,color:"var(--color-text)"}}>
            {cattle ? "개체 정보 수정" : "새 개체 등록"}
          </div>
        </div>

        {/* Form Card */}
        <div className="card animate-fadeInUp" style={{
          display:"flex",
          flexDirection:"column",
          gap:"18px",
          padding:"24px"
        }}>
          <div>
            <label style={labelStyle}>이름 (애칭)</label>
            <input
              className="input"
              style={inputStyle}
              value={formData.name}
              onChange={e=>setFormData({...formData,name:e.target.value})}
              placeholder="예: 누렁이"
            />
          </div>
          <div>
            <label style={labelStyle}>이력번호</label>
            <div style={{display:"flex",gap:"8px",alignItems:"center"}}>
              <input
                className="input"
                style={{...inputStyle,flex:1}}
                value={formData.tagNumber}
                onChange={e=>setFormData({...formData,tagNumber:e.target.value})}
                placeholder="002082037849"
              />
              <button
                type="button"
                onClick={handleLookup}
                disabled={lookupLoading}
                style={{
                  padding:"10px 14px",
                  borderRadius:"var(--radius-md)",
                  border:"1px solid var(--color-primary)",
                  background:"var(--color-primary)",
                  color:"white",
                  fontSize:"13px",
                  fontWeight:700,
                  cursor:lookupLoading?"wait":"pointer",
                  whiteSpace:"nowrap",
                  opacity:lookupLoading?0.7:1,
                  transition:"all var(--transition-fast)"
                }}
              >{lookupLoading ? "조회중..." : "🔍 조회"}</button>
            </div>
            {lookupMsg && (
              <div style={{
                fontSize:"12px",
                marginTop:"6px",
                color:lookupMsg.ok ? "var(--color-success)" : "var(--color-danger)",
                fontWeight:600
              }}>{lookupMsg.text}</div>
            )}
          </div>

          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"14px"}}>
            <div>
              <label style={labelStyle}>축사 (동)</label>
              <select className="input" style={inputStyle} value={formData.buildingId} onChange={e=>setFormData({...formData,buildingId:e.target.value})}>
                {BUILDINGS.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>축사 (칸)</label>
              <select className="input" style={inputStyle} value={formData.penNumber} onChange={e=>setFormData({...formData,penNumber:Number(e.target.value)})}>
                {[...Array(12)].map((_,i)=><option key={i+1} value={i+1}>{i+1}번 칸</option>)}
              </select>
            </div>
          </div>

          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"14px"}}>
            <div>
              <label style={labelStyle}>성별</label>
              <select className="input" style={inputStyle} value={formData.gender} onChange={e=>setFormData({...formData,gender:e.target.value})}>
                <option value="암">암컷 ♀</option><option value="수">수컷 ♂</option>
              </select>
            </div>
            <div>
              <label style={labelStyle}>상태</label>
              <select className="input" style={inputStyle} value={formData.status} onChange={e=>setFormData({...formData,status:e.target.value})}>
                {BREED_STATUS_OPTIONS.map(o=><option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label style={labelStyle}>생년월일</label>
            <input type="date" className="input" style={inputStyle} value={formData.birthDate} onChange={e=>setFormData({...formData,birthDate:e.target.value})} />
          </div>
          <div>
            <label style={labelStyle}>현재 체중 (kg)</label>
            <input type="number" className="input" style={inputStyle} value={formData.weight} onChange={e=>setFormData({...formData,weight:e.target.value})} />
          </div>

          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"14px"}}>
            <div>
              <label style={labelStyle}>구입가격 (원)</label>
              <input type="number" className="input" style={inputStyle} value={formData.purchasePrice} onChange={e=>setFormData({...formData,purchasePrice:e.target.value})} placeholder="예: 3500000" />
            </div>
            <div>
              <label style={labelStyle}>구입일자</label>
              <input type="date" className="input" style={inputStyle} value={formData.purchaseDate} onChange={e=>setFormData({...formData,purchaseDate:e.target.value})} />
            </div>
          </div>

          {/* Genetic Info Section */}
          <div style={{
            background:"var(--color-border-light)",
            padding:"18px",
            borderRadius:"var(--radius-md)",
            marginTop:"6px"
          }}>
            <div style={{
              fontSize:"14px",
              fontWeight:700,
              marginBottom:"14px",
              color:"var(--color-primary-light)",
              display:"flex",
              alignItems:"center",
              gap:"6px"
            }}>🧬 유전 정보 (혈통)</div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"12px"}}>
              <div>
                <label style={labelStyle}>부 (KPN)</label>
                <input className="input" style={{...inputStyle,padding:"10px 12px"}} value={formData.geneticInfo.father} onChange={e=>setFormData({...formData,geneticInfo:{...formData.geneticInfo,father:e.target.value}})} />
              </div>
              <div>
                <label style={labelStyle}>모 (이력)</label>
                <input className="input" style={{...inputStyle,padding:"10px 12px"}} value={formData.geneticInfo.mother} onChange={e=>setFormData({...formData,geneticInfo:{...formData.geneticInfo,mother:e.target.value}})} />
              </div>
            </div>
          </div>

          <div>
            <label style={labelStyle}>메모</label>
            <textarea className="input" style={{...inputStyle,height:"90px",resize:"none"}} value={formData.memo} onChange={e=>setFormData({...formData,memo:e.target.value})} />
          </div>

          {/* Action Buttons */}
          <div style={{display:"flex",gap:"12px",marginTop:"24px"}}>
            <button onClick={onCancel} className="btn btn-secondary" style={btnSecondary}>취소</button>
            <button onClick={handleSubmit} className="btn btn-primary" style={btnPrimary}>저장하기</button>
          </div>
        </div>
      </div>
    </div>
  );
}
