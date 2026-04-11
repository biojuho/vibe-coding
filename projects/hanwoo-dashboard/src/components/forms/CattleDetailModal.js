import { useState, useEffect } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';
import { STATUS_COLORS } from '@/lib/constants';
import { formatDate, getMonthAge, toInputDate, getDaysUntilEstrus, formatMoney } from '@/lib/utils';
import { btnPrimary, btnSecondary, btnDanger, EditIcon, TrashIcon, BackIcon } from '@/components/ui/common';
import QRCodeWidget from '@/components/widgets/QRCodeWidget';
import { getCattleHistory } from '@/lib/actions';
import { extractWeightHistoryPoints } from '@/lib/cattle-history.mjs';

const HISTORY_ICONS = {
  status_change: "🔄",
  weight: "⚖️",
  calving: "🍼",
  movement: "🏠",
  purchase: "📥",
  sale: "💰",
};

export default function CattleDetailModal({ cattle, buildings = [], onClose, onEdit, onDelete, onUpdate }) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (!cattle?.id) return;
    let cancelled = false;
    getCattleHistory(cattle.id)
      .then((res) => {
        if (cancelled) return;
        const nextHistory = Array.isArray(res) ? res : res?.data;
        setHistory(Array.isArray(nextHistory) ? nextHistory : []);
      })
      .catch(() => {
        // API 실패 시 빈 이력으로 안전하게 폴백 — white screen 방지
        if (!cancelled) setHistory([]);
      });
    return () => { cancelled = true; };
  }, [cattle?.id]);

  if (!cattle) return null;

  const monthAge = getMonthAge(cattle.birthDate);
  const statusColor = STATUS_COLORS[cattle.status] || { bg: "#eee", text: "#333" };
  const buildingName = buildings.find((building) => building.id === cattle.buildingId)?.name || cattle.buildingId;

  // Build weight chart data from history or fallback to weightHistory field
  const weightChartData = (() => {
    const weightEvents = extractWeightHistoryPoints(history);
    if (weightEvents.length > 0) {
      return weightEvents.map((entry) => ({
        date: formatDate(entry.eventDate),
        weight: entry.weight,
      }));
    }
    if (Array.isArray(cattle.weightHistory)) return cattle.weightHistory;
    if (typeof cattle.weightHistory === 'string') {
      try { return JSON.parse(cattle.weightHistory); } catch { return []; }
    }
    return [];
  })();

  const handleAddEstrus = () => {
    const date = prompt("발정 관찰일을 입력하세요 (YYYY-MM-DD)", toInputDate(new Date()));
    if (date) {
      onUpdate({ ...cattle, lastEstrus: new Date(date).toISOString() });
    }
  };

  const handleAddPregnancy = () => {
    const date = prompt("수정(인공수정)일을 입력하세요 (YYYY-MM-DD)", toInputDate(new Date()));
    if (date) {
      onUpdate({ ...cattle, status: "임신우", pregnancyDate: new Date(date).toISOString() });
    }
  };

  return (
    <div className="modal-overlay" style={{alignItems:"flex-start"}}>
      <div
        className="animate-slideInUp"
        style={{
          background:"var(--color-bg-card)",
          width:"100%",
          maxWidth:"600px",
          minHeight:"100vh",
          overflowY:"auto",
          paddingBottom:"60px",
          boxShadow:"0 -8px 40px rgba(0,0,0,0.15)"
        }}
      >
        {/* Header Image Area — gradient with depth */}
        <div
          className="animate-fadeIn"
          style={{
            height:"240px",
            background:`linear-gradient(155deg, ${statusColor.bg}, ${statusColor.bg}dd, color-mix(in srgb, ${statusColor.bg} 80%, var(--color-bg-card)))`,
            position:"relative",
            display:"flex",
            alignItems:"flex-end",
            padding:"28px 24px",
            borderBottom:"1px solid color-mix(in srgb, var(--color-surface-stroke) 40%, transparent)"
          }}
        >
          <button
            onClick={onClose}
            className="btn btn-icon animate-scaleIn"
            style={{
              position:"absolute",
              top:"20px",
              left:"20px",
              background:"var(--color-bg-card)",
              boxShadow:"var(--shadow-md)"
            }}
          ><BackIcon/></button>
          <div style={{width:"100%"}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-end"}}>
              <div className="animate-fadeInUp">
                <div style={{
                  fontSize:"38px",
                  fontWeight:800,
                  marginBottom:"8px",
                  color:statusColor.text,
                  fontFamily:"var(--font-display)",
                  letterSpacing:"-0.02em",
                  lineHeight:1
                }}>{cattle.name}</div>
                <div style={{fontSize:"15px",opacity:0.8,fontWeight:600,color:statusColor.text,letterSpacing:"0.02em"}}>{cattle.tagNumber}</div>
              </div>
              <div
                className="animate-fadeInUp"
                style={{
                  background:"var(--color-bg-card)",
                  padding:"8px 16px",
                  borderRadius:"var(--radius-full)",
                  fontSize:"13px",
                  fontWeight:700,
                  color:statusColor.text,
                  boxShadow:"var(--shadow-sm)",
                  animationDelay:"100ms"
                }}
              >
                {cattle.gender} · {cattle.status} · {monthAge}개월
              </div>
            </div>
          </div>
        </div>

        <div style={{padding:"24px"}}>
          {/* Quick Actions */}
          <div className="animate-fadeInUp" style={{display:"flex",gap:"12px",marginBottom:"28px",animationDelay:"100ms"}}>
            <button
              onClick={onEdit}
              className="btn btn-secondary"
              style={{...btnSecondary,flex:1,display:"flex",alignItems:"center",justifyContent:"center",gap:"8px"}}
            ><EditIcon/> 수정</button>
            <button
              onClick={onDelete}
              className="btn btn-danger"
              style={{...btnDanger,flex:1,display:"flex",alignItems:"center",justifyContent:"center",gap:"8px"}}
            ><TrashIcon/> 삭제</button>
          </div>

          {/* Basic Info */}
          <div className="animate-fadeInUp" style={{marginBottom:"28px",animationDelay:"150ms"}}>
            <SectionTitle icon="📋" title="기본 정보" />
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"14px"}}>
              <InfoItem label="위치" value={`${buildingName} ${cattle.penNumber}번 칸`} delay={0} />
              <InfoItem label="생년월일" value={formatDate(cattle.birthDate)} delay={50} />
              <InfoItem label="현재체중" value={`${cattle.weight} kg`} highlight delay={100} />
              <InfoItem label="유전능력" value={`부:${cattle.geneticInfo?.father || '-'} / 모:${cattle.geneticInfo?.mother || '-'}`} delay={150} />
              {cattle.purchasePrice && <InfoItem label="구입가격" value={`${formatMoney(cattle.purchasePrice)}원`} delay={200} />}
              {cattle.purchaseDate && <InfoItem label="구입일자" value={formatDate(cattle.purchaseDate)} delay={250} />}
            </div>
          </div>

          {/* Reproduction Management */}
          {(cattle.status === "번식우" || cattle.status === "임신우" || cattle.gender === "암") &&
            <div
              className="animate-fadeInUp"
              style={{
                marginBottom:"28px",
                background:"linear-gradient(135deg, color-mix(in srgb, var(--color-warning-light) 78%, var(--color-surface-elevated)), var(--color-warning-light))",
                borderRadius:"var(--radius-lg)",
                padding:"20px",
                animationDelay:"200ms"
              }}
            >
              <SectionTitle icon="❤️" title="번식 관리" color="var(--color-warning)" />
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"14px",marginBottom:"16px"}}>
                <InfoItem label="최근 발정" value={cattle.lastEstrus ? formatDate(cattle.lastEstrus) : "-"} />
                <InfoItem label="다음 발정 예정" value={cattle.lastEstrus ? `D-${getDaysUntilEstrus(cattle.lastEstrus)}` : "-"} />
                <InfoItem label="수정일(임신)" value={cattle.pregnancyDate ? formatDate(cattle.pregnancyDate) : "-"} />
                <InfoItem label="분만 예정일" value={cattle.pregnancyDate ? "계산중..." : "-"} />
              </div>
              <div style={{display:"flex",gap:"10px"}}>
                <button
                  onClick={handleAddEstrus}
                  className="btn"
                  style={{
                    ...btnPrimary,
                    padding:"12px 16px",
                    fontSize:"13px",
                    background:"linear-gradient(135deg, var(--color-warning), color-mix(in srgb, var(--color-warning) 78%, #9b6e40 22%))",
                    flex:1
                  }}
                >+ 발정 기록</button>
                <button
                  onClick={handleAddPregnancy}
                  className="btn"
                  style={{
                    ...btnPrimary,
                    padding:"12px 16px",
                    fontSize:"13px",
                    background:"linear-gradient(135deg, var(--color-primary-custom), var(--color-primary-dark))",
                    flex:1
                  }}
                >+ 수정 기록</button>
              </div>
            </div>
          }

          {/* Weight Chart */}
          <div className="animate-fadeInUp" style={{marginBottom:"28px",animationDelay:"250ms"}}>
            <SectionTitle icon="📈" title="체중 변화" />
            <div style={{
              height:"220px",
              background:"var(--color-border-light)",
              borderRadius:"var(--radius-lg)",
              padding:"16px"
            }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weightChartData}>
                  <XAxis dataKey="date" tick={{fontSize:11}} tickFormatter={(v)=>v.substring(5)} stroke="#999" />
                  <YAxis domain={['auto','auto']} width={35} tick={{fontSize:11}} stroke="#999" />
                  <Tooltip
                    contentStyle={{
                      background:"var(--color-bg-card)",
                      border:"none",
                      borderRadius:"8px",
                      boxShadow:"var(--shadow-md)"
                    }}
                  />
                  <Line type="monotone" dataKey="weight" stroke="var(--color-primary)" strokeWidth={3} dot={{r:4,fill:"var(--color-primary)"}} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* History Timeline */}
          {history.length > 0 && (
            <div className="animate-fadeInUp" style={{marginBottom:"28px",animationDelay:"280ms"}}>
              <SectionTitle icon="📜" title="이력 타임라인" />
              <div style={{display:"flex",flexDirection:"column",gap:"0"}}>
                {history.map((h, idx) => (
                  <div key={h.id} style={{display:"flex",gap:"12px",position:"relative"}}>
                    {/* Timeline line */}
                    {idx < history.length - 1 && (
                      <div style={{position:"absolute",left:"15px",top:"32px",bottom:"-8px",width:"2px",background:"var(--color-border)"}} />
                    )}
                    {/* Icon — elevated with subtle shadow */}
                    <div style={{
                      width:"34px",height:"34px",borderRadius:"50%",
                      background:"var(--color-surface-elevated)",
                      border:"1px solid var(--color-surface-stroke)",
                      display:"flex",alignItems:"center",justifyContent:"center",
                      fontSize:"16px",flexShrink:0,zIndex:1,
                      boxShadow:"var(--shadow-sm)",
                      transition:"transform 0.2s ease"
                    }}>
                      {HISTORY_ICONS[h.eventType] || "📌"}
                    </div>
                    {/* Content */}
                    <div style={{paddingBottom:"18px",flex:1}}>
                      <div style={{fontSize:"13px",fontWeight:700,color:"var(--color-text)",letterSpacing:"-0.01em"}}>{h.description || h.eventType}</div>
                      <div style={{fontSize:"11px",color:"var(--color-text-muted)",marginTop:"3px"}}>{formatDate(h.eventDate)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Memo */}
          <div className="animate-fadeInUp" style={{marginBottom:"28px",animationDelay:"300ms"}}>
            <SectionTitle icon="📝" title="메모" />
            <div style={{
              background:"var(--color-border-light)",
              borderRadius:"var(--radius-md)",
              padding:"18px",
              fontSize:"14px",
              lineHeight:"1.7",
              color:"var(--color-text-secondary)",
              minHeight:"90px"
            }}>
              {cattle.memo || "등록된 메모가 없습니다."}
            </div>
          </div>

          {/* QR Code */}
          <div className="animate-fadeInUp" style={{animationDelay:"350ms"}}>
            <SectionTitle icon="📱" title="개체 식별 QR" />
            <div style={{
              background:"var(--color-border-light)",
              borderRadius:"var(--radius-md)",
              padding:"20px",
              display:"flex",
              justifyContent:"center"
            }}>
              <QRCodeWidget value={`https://joolife.kr/cattle/${cattle.id}`} label={`${cattle.name} (${cattle.tagNumber})`} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SectionTitle({icon, title, color = "var(--color-text)"}){
  return (
    <div style={{
      fontSize:"16px",
      fontWeight:800,
      marginBottom:"16px",
      paddingBottom:"10px",
      borderBottom:"1px solid color-mix(in srgb, var(--color-border-custom) 35%, transparent)",
      color,
      display:"flex",
      alignItems:"center",
      gap:"10px",
      letterSpacing:"-0.01em"
    }}>
      <span style={{fontSize:"18px",lineHeight:1}}>{icon}</span> {title}
    </div>
  );
}

function InfoItem({label,value,highlight=false,delay=0}){
  return (
    <div
      className="animate-fadeInUp"
      style={{
        background:"var(--color-bg-card)",
        border:"1px solid var(--color-border)",
        borderRadius:"var(--radius-md)",
        padding:"14px 16px",
        transition:"all 0.25s cubic-bezier(0.22,1,0.36,1)",
        animationDelay:`${delay}ms`,
        cursor:"default"
      }}
      onMouseEnter={e=>{e.currentTarget.style.transform="translateY(-2px)";e.currentTarget.style.boxShadow="var(--shadow-sm)";}}
      onMouseLeave={e=>{e.currentTarget.style.transform="translateY(0)";e.currentTarget.style.boxShadow="none";}}
    >
      <div style={{fontSize:"11px",color:"var(--color-text-muted)",marginBottom:"5px",fontWeight:600,letterSpacing:"0.03em",textTransform:"uppercase"}}>{label}</div>
      <div style={{
        fontSize:highlight ? "20px" : "14px",
        fontWeight:highlight ? 800 : 700,
        color:"var(--color-text)",
        fontFamily: highlight ? "var(--font-display)" : "inherit",
        letterSpacing: highlight ? "-0.02em" : "0"
      }}>{value}</div>
    </div>
  );
}
