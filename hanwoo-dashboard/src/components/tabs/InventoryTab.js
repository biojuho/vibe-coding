'use client';
import { useState } from 'react';

export default function InventoryTab({ inventory, onAddItem, onUpdateQuantity }) {
    const [isAdding, setIsAdding] = useState(false);
    const [formData, setFormData] = useState({ name: "", category: "Feed", quantity: "", unit: "kg", threshold: "" });
    const [editId, setEditId] = useState(null);
    const [editQty, setEditQty] = useState("");

    const handleSubmit = () => {
        if(!formData.name || !formData.quantity) return alert("필수 항목을 입력하세요.");
        onAddItem(formData);
        setIsAdding(false);
        setFormData({ name: "", category: "Feed", quantity: "", unit: "kg", threshold: "" });
    };

    const handleUpdate = (id) => {
        if(!editQty) return;
        onUpdateQuantity(id, editQty);
        setEditId(null);
        setEditQty("");
    };

    const categories = { "Feed": "사료", "Medicine": "약품", "Equipment": "기자재", "Other": "기타" };

    return <div>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"14px"}}>
            <div style={{fontSize:"16px",fontWeight:800,color:"var(--color-text)"}}>📦 자재 재고 관리</div>
            <button onClick={()=>setIsAdding(!isAdding)} style={{fontSize:"13px",fontWeight:700,color:"var(--color-success)",background:"var(--color-bg-card)",border:"1px solid var(--color-success)",borderRadius:"8px",padding:"6px 12px",cursor:"pointer"}}>
                {isAdding ? "취소" : "+자재 등록"}
            </button>
        </div>

        {isAdding && <div style={{background:"var(--color-bg)",borderRadius:"14px",padding:"16px",marginBottom:"16px",border:"1px solid var(--color-border)"}}>
            <div style={{fontSize:"14px",fontWeight:700,marginBottom:"12px",color:"var(--color-text)"}}>새 자재 등록</div>
            <div style={{display:"grid",gap:"10px"}}>
                <input placeholder="자재명 (예: 볏짚)" value={formData.name} onChange={e=>setFormData({...formData,name:e.target.value})} style={{padding:"10px",borderRadius:"8px",border:"1px solid var(--color-border)",background:"var(--color-bg-card)",color:"var(--color-text)"}} />
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"10px"}}>
                    <select value={formData.category} onChange={e=>setFormData({...formData,category:e.target.value})} style={{padding:"10px",borderRadius:"8px",border:"1px solid var(--color-border)",background:"var(--color-bg-card)",color:"var(--color-text)"}}>
                        <option value="Feed">사료/조사료</option><option value="Medicine">약품/영양제</option><option value="Equipment">기자재</option><option value="Other">기타</option>
                    </select>
                    <input type="number" placeholder="수량" value={formData.quantity} onChange={e=>setFormData({...formData,quantity:e.target.value})} style={{padding:"10px",borderRadius:"8px",border:"1px solid var(--color-border)",background:"var(--color-bg-card)",color:"var(--color-text)"}} />
                </div>
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"10px"}}>
                     <input placeholder="단위 (예: kg, 포, 박스)" value={formData.unit} onChange={e=>setFormData({...formData,unit:e.target.value})} style={{padding:"10px",borderRadius:"8px",border:"1px solid var(--color-border)",background:"var(--color-bg-card)",color:"var(--color-text)"}} />
                     <input type="number" placeholder="경고 기준값 (선택)" value={formData.threshold} onChange={e=>setFormData({...formData,threshold:e.target.value})} style={{padding:"10px",borderRadius:"8px",border:"1px solid var(--color-border)",background:"var(--color-bg-card)",color:"var(--color-text)"}} />
                </div>
                <button onClick={handleSubmit} style={{width:"100%",padding:"12px",background:"var(--color-success)",color:"white",borderRadius:"8px",border:"none",fontWeight:700,marginTop:"8px",cursor:"pointer"}}>등록하기</button>
            </div>
        </div>}

        <div style={{display:"flex",flexDirection:"column",gap:"10px"}}>
            {inventory.map(item => {
                const isLow = item.threshold && item.quantity <= item.threshold;
                return <div key={item.id} style={{background:"var(--color-bg-card)",borderRadius:"14px",padding:"14px",border:isLow?"2px solid var(--color-danger)":"1px solid var(--color-border)",position:"relative"}}>
                    {isLow && <div style={{position:"absolute",top:"-8px",right:"10px",background:"var(--color-danger)",color:"white",fontSize:"10px",padding:"2px 8px",borderRadius:"10px",fontWeight:700}}>부족 경고</div>}
                    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                        <div>
                            <div style={{fontSize:"11px",color:"var(--color-text-muted)",marginBottom:"2px"}}>{categories[item.category] || item.category}</div>
                            <div style={{fontWeight:700,fontSize:"15px",color:"var(--color-text)"}}>{item.name}</div>
                        </div>
                        <div style={{textAlign:"right"}}>
                            {editId === item.id ?
                                <div style={{display:"flex",alignItems:"center",gap:"4px"}}>
                                    <input type="number" value={editQty} onChange={e=>setEditQty(e.target.value)} style={{width:"60px",padding:"4px",fontSize:"14px",background:"var(--color-bg)",color:"var(--color-text)",border:"1px solid var(--color-border)",borderRadius:"4px"}} autoFocus />
                                    <button onClick={()=>handleUpdate(item.id)} style={{background:"var(--color-success)",color:"white",border:"none",borderRadius:"4px",padding:"4px 8px"}}>OK</button>
                                </div>
                            :
                                <div onClick={()=>{setEditId(item.id); setEditQty(item.quantity);}} style={{fontSize:"16px",fontWeight:800,color:isLow?"var(--color-danger)":"var(--color-text)",cursor:"pointer"}}>
                                    {item.quantity} <span style={{fontSize:"12px",fontWeight:400}}>{item.unit}</span>
                                </div>
                            }
                        </div>
                    </div>
                </div>;
            })}
            {inventory.length === 0 && <div style={{textAlign:"center",padding:"30px",color:"var(--color-text-muted)"}}>등록된 자재가 없습니다.</div>}
        </div>
    </div>;
}
