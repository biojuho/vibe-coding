import { calcTHI, getTHILevel, getWeatherIcon, getWeatherDesc, getLivestockWeatherAlerts, isEstrusAlert, isEstrusToday, getDaysUntilEstrus, isCalvingAlert, getDaysUntilCalving, getCalvingDate, formatDate } from '@/lib/utils';
import { HeartIcon } from '@/components/ui/common';
import { PremiumCard, PremiumCardContent } from '@/components/ui/premium-card';

export function TabBar({ activeTab, onTabChange }) {
  const tabs = [
    { id: "home", label: "홈", icon: "🏠" },
    { id: "feed", label: "사료", icon: "🌾" },
    { id: "calving", label: "분만", icon: "🍼" },
    { id: "sales", label: "출하", icon: "💰" },
    { id: "inventory", label: "재고", icon: "📦" },
    { id: "schedule", label: "일정", icon: "🗓️" },
    { id: "settings", label: "설정", icon: "⚙️" },
  ];
  return (
    <nav className="tab-bar">
      {tabs.map((t, idx) => (
        <button
          key={t.id}
          onClick={() => onTabChange(t.id)}
          className={`tab-item ${activeTab === t.id ? 'active' : ''}`}
          style={{
            color: activeTab === t.id ? 'var(--color-primary)' : 'var(--color-text-muted)',
            animationDelay: `${idx * 30}ms`
          }}
        >
          <span className="tab-icon" style={{
            transform: activeTab === t.id ? 'scale(1.15) translateY(-2px)' : 'scale(1)',
            transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)'
          }}>{t.icon}</span>
          <span className="tab-label">{t.label}</span>
        </button>
      ))}
    </nav>
  );
}

export function WeatherWidget({weather}){
  if(!weather) return (
    <div className="weather-card animate-fadeInUp" style={{marginBottom:"16px",textAlign:"center"}}>
      <div className="skeleton" style={{height:"120px",width:"100%"}}></div>
    </div>
  );
  const thi=calcTHI(weather.temp,weather.humidity);
  const thiLevel=getTHILevel(thi);
  const icon=getWeatherIcon(weather.weatherCode);
  const desc=getWeatherDesc(weather.weatherCode);

  return (
    <div style={{marginBottom:"16px"}} className="animate-fadeInUp">
      <PremiumCard className="overflow-visible bg-slate-800/60">
        <PremiumCardContent className="p-5">
        <div className="weather-icon-bg">{icon}</div>
        <div style={{fontSize:"12px",opacity:0.8,marginBottom:"8px",position:"relative"}}>
          📍 {weather.locationName} · {new Date().toLocaleTimeString('ko-KR', {hour:'2-digit', minute:'2-digit'})} 기준
        </div>
        <div style={{display:"flex",alignItems:"flex-end",gap:"14px",marginBottom:"16px",position:"relative"}}>
          <span style={{fontSize:"52px",fontWeight:800,fontFamily:"var(--font-display)",lineHeight:1,textShadow:"0 4px 12px rgba(0,0,0,0.2)"}}>{Math.round(weather.temp)}°</span>
          <div style={{paddingBottom:"6px"}}>
            <div style={{fontSize:"22px",marginBottom:"2px"}}>{icon} {desc}</div>
            <div style={{fontSize:"13px",opacity:0.75}}>체감 {Math.round(weather.apparentTemp)}°C</div>
          </div>
        </div>
        <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:"10px"}}>
          {[
            {i:"💧",l:"습도",v:`${weather.humidity}%`},
            {i:"🌬️",l:"풍속",v:`${weather.windSpeed}m/s`},
            {i:"🌡️",l:"최고/최저",v:`${Math.round(weather.tempMax)}°/${Math.round(weather.tempMin)}°`},
            {i:"🌧️",l:"강수",v:`${weather.precipitation}%`}
          ].map((item,idx)=>
            <div key={idx} className="weather-stat" style={{animationDelay:`${idx*50}ms`}}>
              <div style={{fontSize:"16px",marginBottom:"2px"}}>{item.i}</div>
              <div style={{fontSize:"9px",opacity:0.7,marginBottom:"2px"}}>{item.l}</div>
              <div style={{fontSize:"14px",fontWeight:700,fontFamily:"var(--font-display)"}}>{item.v}</div>
            </div>
          )}
        </div>
        </PremiumCardContent>
      </PremiumCard>
      <div style={{
        background:thiLevel.bg,
        borderRadius:"var(--radius-lg)",
        padding:"14px 18px",
        marginTop:"12px",
        border:`2px solid ${thiLevel.color}`,
        display:"flex",
        alignItems:"center",
        gap:"14px",
        transition:"all var(--transition-normal)"
      }}>
        <div style={{
          width:"52px",height:"52px",borderRadius:"50%",
          background:`linear-gradient(135deg, ${thiLevel.color}, ${thiLevel.color}dd)`,
          display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",
          color:"white",flexShrink:0,boxShadow:`0 4px 12px ${thiLevel.color}40`
        }}>
          <span style={{fontSize:"16px",fontWeight:800,fontFamily:"var(--font-display)",lineHeight:1}}>{Math.round(thi)}</span>
          <span style={{fontSize:"8px",fontWeight:600,opacity:0.9}}>THI</span>
        </div>
        <div>
          <div style={{fontWeight:700,fontSize:"15px",color:thiLevel.color}}>🐂 온열지수: {thiLevel.label}</div>
          <div style={{fontSize:"12px",color:"var(--color-text-secondary)",marginTop:"2px"}}>{thiLevel.desc}</div>
        </div>
      </div>

      {/* 3-Day Forecast */}
      {weather.forecast && weather.forecast.length > 0 && (
        <div style={{
          background:"var(--color-bg-card)",
          borderRadius:"var(--radius-lg)",
          padding:"14px 18px",
          marginTop:"12px",
          border:"1px solid var(--color-border)"
        }}>
          <div style={{fontSize:"13px",fontWeight:700,color:"var(--color-text)",marginBottom:"10px"}}>📅 3일 예보</div>
          <div style={{display:"grid",gridTemplateColumns:`repeat(${weather.forecast.length},1fr)`,gap:"10px"}}>
            {weather.forecast.map((day, idx) => {
              const dayLabel = idx === 0 ? "오늘" : new Date(day.date).toLocaleDateString('ko-KR', { weekday: 'short', month: 'short', day: 'numeric' });
              return (
                <div key={day.date} style={{
                  textAlign:"center",
                  padding:"10px 6px",
                  background:"var(--color-border-light)",
                  borderRadius:"var(--radius-md)",
                  transition:"all var(--transition-fast)"
                }}>
                  <div style={{fontSize:"11px",color:"var(--color-text-muted)",marginBottom:"4px"}}>{dayLabel}</div>
                  <div style={{fontSize:"24px",marginBottom:"4px"}}>{getWeatherIcon(day.weatherCode)}</div>
                  <div style={{fontSize:"13px",fontWeight:700,fontFamily:"var(--font-display)",color:"var(--color-text)"}}>
                    {Math.round(day.tempMax)}° / {Math.round(day.tempMin)}°
                  </div>
                  {day.precipProb > 0 && (
                    <div style={{fontSize:"10px",color:"var(--color-info)",marginTop:"2px"}}>🌧 {day.precipProb}%</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Livestock Weather Alerts */}
      {(() => {
        const alerts = getLivestockWeatherAlerts(weather.forecast || []);
        if (alerts.length === 0) return null;
        return (
          <div style={{
            background:"var(--color-warning-light)",
            border:"1px solid var(--color-warning)",
            borderRadius:"var(--radius-lg)",
            padding:"12px 16px",
            marginTop:"10px"
          }}>
            <div style={{fontSize:"12px",fontWeight:700,color:"var(--color-warning)",marginBottom:"6px"}}>🐄 가축 기상 경고</div>
            {alerts.map((a, i) => (
              <div key={i} style={{fontSize:"12px",color:"var(--color-text)",padding:"3px 0"}}>
                {a.icon} {a.msg}
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}

export function EstrusAlertBanner({cattle, buildings = []}){
  const ac=cattle.filter(c=>c.lastEstrus&&isEstrusAlert(c.lastEstrus));
  if(ac.length===0)return null;
  const tc=ac.filter(c=>isEstrusToday(c.lastEstrus)).length;

  return (
    <PremiumCard className="animate-fadeInUp mb-4 bg-pink-900/10 border-pink-500/20" style={{animationDelay:"100ms"}}>
      <PremiumCardContent className="p-4">
      <div style={{display:"flex",alignItems:"center",gap:"10px",marginBottom:"10px"}}>
        <span className="alert-icon"><HeartIcon/></span>
        <span style={{fontWeight:700,fontSize:"15px",letterSpacing:"-0.3px"}}>
          🔔 발정 알림 — {tc>0?`오늘 ${tc}두`:`${ac.length}두 임박`}
        </span>
      </div>
      <div style={{display:"flex",flexWrap:"wrap",gap:"8px"}}>
        {ac.map((c,idx)=>{
          const d=getDaysUntilEstrus(c.lastEstrus);
          const bl=buildings.find(b=>b.id===c.buildingId);
          return (
            <div
              key={c.id}
              className="animate-fadeInUp"
              style={{
                background:"rgba(255,255,255,0.05)",
                borderRadius:"var(--radius-md)",
                padding:"8px 14px",
                fontSize:"13px",
                border:"1px solid rgba(255,255,255,0.1)",
                transition:"all var(--transition-fast)",
                animationDelay:`${150 + idx*50}ms`
              }}
              onMouseEnter={e=>e.currentTarget.style.background="rgba(255,255,255,0.1)"}
              onMouseLeave={e=>e.currentTarget.style.background="rgba(255,255,255,0.05)"}
            >
              <strong className="text-pink-300">{c.name}</strong> · <span className="text-slate-300">{bl?.name || '미지정'} {c.penNumber}번</span> ·
              <span style={{fontWeight:700}} className="text-pink-400">{d===0?" ⚡오늘!":` D-${d}`}</span>
            </div>
          );
        })}
      </div>
      </PremiumCardContent>
    </PremiumCard>
  );
}

export function CalvingAlertBanner({cattle, buildings = []}){
  const ac=cattle.filter(c=>c.status==="임신우"&&c.pregnancyDate&&isCalvingAlert(c.pregnancyDate));
  if(ac.length===0)return null;

  return (
    <PremiumCard className="animate-fadeInUp mb-4 bg-indigo-900/10 border-indigo-500/20" style={{animationDelay:"150ms"}}>
      <PremiumCardContent className="p-4">
      <div style={{display:"flex",alignItems:"center",gap:"10px",marginBottom:"10px"}}>
        <span style={{fontSize:"18px"}} className="animate-bounce">🍼</span>
        <span style={{fontWeight:700,fontSize:"15px",letterSpacing:"-0.3px"}}>
          분만 알림 — {ac.length}두 분만 임박 (14일 이내)
        </span>
      </div>
      <div style={{display:"flex",flexWrap:"wrap",gap:"8px"}}>
        {ac.map((c,idx)=>{
          const d=getDaysUntilCalving(c.pregnancyDate);
          const bl=buildings.find(b=>b.id===c.buildingId);
          return (
            <div
              key={c.id}
              className="animate-fadeInUp"
              style={{
                background:"rgba(255,255,255,0.05)",
                borderRadius:"var(--radius-md)",
                padding:"8px 14px",
                fontSize:"13px",
                border:"1px solid rgba(255,255,255,0.1)",
                transition:"all var(--transition-fast)",
                animationDelay:`${200 + idx*50}ms`
              }}
              onMouseEnter={e=>e.currentTarget.style.background="rgba(255,255,255,0.1)"}
              onMouseLeave={e=>e.currentTarget.style.background="rgba(255,255,255,0.05)"}
            >
              <strong className="text-indigo-300">{c.name}</strong> · <span className="text-slate-300">{bl?.name || '미지정'} {c.penNumber}번</span> ·
              <span style={{fontWeight:700}} className="text-indigo-400"> D-{d}</span> <span className="text-slate-400">· 예정 {formatDate(getCalvingDate(c.pregnancyDate))}</span>
            </div>
          );
        })}
      </div>
      </PremiumCardContent>
    </PremiumCard>
  );
}
