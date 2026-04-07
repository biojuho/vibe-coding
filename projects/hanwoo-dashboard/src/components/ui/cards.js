import { STATUS_COLORS, BUILDINGS } from '@/lib/constants';
import { isEstrusAlert, getDaysUntilEstrus, getMonthAge, isCalvingAlert, getDaysUntilCalving } from '@/lib/utils';
import { HeartIcon } from './common';

export function StatCard({label,value,sub,color,delay=0}){
  return (
    <div
      className="stat-card animate-fadeInUp"
      style={{
        '--stat-color': color,
        flex:"1 1 140px",
        minWidth:"140px",
        animationDelay:`${delay}ms`,
        scrollSnapAlign:"start"
      }}
    >
      <div style={{fontSize:"12px",color:"var(--color-text-muted)",marginBottom:"6px",fontWeight:600,letterSpacing:"0.03em",textTransform:"uppercase"}}>{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div style={{fontSize:"12px",color:"var(--color-text-secondary)",marginTop:"6px",lineHeight:"1.4"}}>{sub}</div>}
    </div>
  );
}

export function PenCard({penNumber,cattle,buildingId,onSelect,delay=0,onDrop}){
  const hasAlert=cattle.some(c=>c.lastEstrus&&isEstrusAlert(c.lastEstrus));
  const isEmpty=cattle.length===0;

  const handleDragOver = (e) => {
    e.preventDefault();
    e.currentTarget.classList.add('pen-drop-hover');
  };
  const handleDragLeave = (e) => {
    e.currentTarget.classList.remove('pen-drop-hover');
  };
  const handleDrop = (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('pen-drop-hover');
    if (onDrop) {
      try {
        const data = JSON.parse(e.dataTransfer.getData('text/plain'));
        onDrop(data.cattleId, buildingId, penNumber);
      } catch {}
    }
  };

  return (
    <div
      onClick={()=>onSelect(buildingId,penNumber)}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`pen-card animate-fadeInUp ${isEmpty?'empty':''} ${hasAlert?'alert':''}`}
      style={{animationDelay:`${delay}ms`}}
    >
      {hasAlert && <div className="pen-alert-badge">❤️</div>}
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"8px"}}>
        <span style={{
          fontFamily:"var(--font-display)",
          fontWeight:700,
          fontSize:"14px",
          color:isEmpty?"var(--color-text-muted)":"var(--color-primary-light)"
        }}>#{penNumber}</span>
        <span style={{
          fontSize:"11px",
          background:isEmpty?"var(--color-border)":"var(--color-border-light)",
          padding:"3px 8px",
          borderRadius:"8px",
          color:isEmpty?"var(--color-text-muted)":"var(--color-text-secondary)",
          fontWeight:500
        }}>{cattle.length}/5</span>
      </div>
      {isEmpty ? (
        <div style={{color:"var(--color-text-muted)",fontSize:"12px",textAlign:"center",paddingTop:"8px"}}>비어있음</div>
      ) : (
        <div style={{display:"flex",gap:"4px",flexWrap:"wrap"}}>
          {cattle.map((c,idx)=>{
            const sc=STATUS_COLORS[c.status]||{dot:"#888"};
            const al=c.lastEstrus&&isEstrusAlert(c.lastEstrus);
            return (
              <div
                key={c.id}
                title={`${c.name}`}
                className="animate-scaleIn"
                style={{
                  width:"28px",
                  height:"28px",
                  borderRadius:"50%",
                  background:al ? "linear-gradient(135deg,#FF1744,#D50000)" : `linear-gradient(135deg,${sc.dot},${sc.dot}dd)`,
                  display:"flex",
                  alignItems:"center",
                  justifyContent:"center",
                  color:"white",
                  fontSize:"10px",
                  fontWeight:700,
                  boxShadow:al ? "0 2px 10px rgba(255,23,68,0.45)" : "0 2px 8px rgba(0,0,0,0.15)",
                  animationDelay:`${delay + idx*30}ms`,
                  transition:"transform 0.25s cubic-bezier(0.22,1,0.36,1), box-shadow 0.25s ease",
                  cursor:"pointer"
                }}
                onMouseEnter={e=>{e.currentTarget.style.transform="scale(1.18)";e.currentTarget.style.boxShadow=al?"0 4px 14px rgba(255,23,68,0.55)":`0 4px 14px ${sc.dot}55`;}}
                onMouseLeave={e=>{e.currentTarget.style.transform="scale(1)";e.currentTarget.style.boxShadow=al?"0 2px 10px rgba(255,23,68,0.45)":"0 2px 8px rgba(0,0,0,0.15)";}}
              >{c.gender==="암"?"♀":"♂"}</div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function CattleRow({cow,onClick,delay=0,draggable=false}){
  const sc=STATUS_COLORS[cow.status]||{bg:"var(--color-border-light)",text:"var(--color-text)",dot:"var(--color-text-muted)"};
  const hasEstrusAlert=cow.lastEstrus&&isEstrusAlert(cow.lastEstrus);
  const estrusD=getDaysUntilEstrus(cow.lastEstrus);
  const monthAge=getMonthAge(cow.birthDate);
  const hasCalvingAlert = cow.status==="임신우"&&cow.pregnancyDate&&isCalvingAlert(cow.pregnancyDate);
  const calvingDays = getDaysUntilCalving(cow.pregnancyDate);

  const handleDragStart = (e) => {
    e.dataTransfer.setData('text/plain', JSON.stringify({ cattleId: cow.id, name: cow.name }));
    e.dataTransfer.effectAllowed = 'move';
    e.currentTarget.classList.add('cattle-dragging');
  };
  const handleDragEnd = (e) => {
    e.currentTarget.classList.remove('cattle-dragging');
  };

  return (
    <div
      onClick={()=>onClick(cow)}
      draggable={draggable}
      onDragStart={draggable ? handleDragStart : undefined}
      onDragEnd={draggable ? handleDragEnd : undefined}
      className={`cattle-row animate-fadeInUp ${hasEstrusAlert?'estrus-alert':''} ${hasCalvingAlert?'calving-alert':''}`}
      style={{animationDelay:`${delay}ms`, cursor: draggable ? 'grab' : 'pointer'}}
    >
      <div
        className="cattle-avatar"
        style={{
          background:`linear-gradient(135deg,${sc.dot},${sc.dot}cc)`,
          boxShadow:`0 4px 12px ${sc.dot}40`
        }}
      >
        {cow.gender==="암"?"♀":"♂"}
      </div>
      <div style={{flex:1,minWidth:0}}>
        <div style={{display:"flex",alignItems:"center",gap:"6px",flexWrap:"wrap",marginBottom:"5px"}}>
          <span style={{fontWeight:700,fontSize:"15px",color:"var(--color-text)",letterSpacing:"-0.01em"}}>{cow.name}</span>
          <span className="badge" style={{background:sc.bg,color:sc.text}}>{cow.status}</span>
          {hasEstrusAlert && (
            <span className="badge badge-estrus" style={{animation:estrusD===0?"shake 0.5s ease-in-out":"none"}}>
              {estrusD===0?"🔥오늘!":"발정D-"+estrusD}
            </span>
          )}
          {hasCalvingAlert && (
            <span className="badge badge-calving">🍼분만D-{calvingDays}</span>
          )}
        </div>
        <div style={{fontSize:"12px",color:"var(--color-text-secondary)",lineHeight:"1.5"}}>
          {cow.tagNumber} · {monthAge}개월 · {cow.weight}kg · {cow.geneticInfo?.grade||"-"}
        </div>
      </div>
      {/* Animated chevron — slides right on row hover */}
      <div className="cattle-chevron">›</div>
    </div>
  );
}
