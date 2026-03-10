'use client';
import { useState, useEffect } from 'react';
import { Settings, MapPin } from 'lucide-react';

export default function SettingsTab({ buildings, onCreateBuilding, onDeleteBuilding, farmSettings, onUpdateFarmSettings, theme, onToggleTheme, widgetRegistry = [], widgetVisible = {}, onToggleWidget }) {
    const [isAdding, setIsAdding] = useState(false);
    const [formData, setFormData] = useState({ name: "", penCount: 32 });
    
    // Farm Settings State
    const [farmData, setFarmData] = useState({
        name: "",
        location: "",
        latitude: 35.446,
        longitude: 127.344
    });

    useEffect(() => {
        if (farmSettings) {
            setFarmData({
                name: farmSettings.name || "",
                location: farmSettings.location || "",
                latitude: farmSettings.latitude || 35.446,
                longitude: farmSettings.longitude || 127.344
            });
        }
    }, [farmSettings]);

    const handleSubmitBuilding = () => {
        if (!formData.name) return alert("동 이름을 입력하세요.");
        onCreateBuilding(formData);
        setIsAdding(false);
        setFormData({ name: "", penCount: 32 });
    };

    const handleSaveFarmSettings = () => {
        onUpdateFarmSettings(farmData);
    };

    const KOREAN_LOCATIONS = [
        { name: "서울", lat: 37.566, lng: 126.978 },
        { name: "부산", lat: 35.179, lng: 129.075 },
        { name: "대구", lat: 35.871, lng: 128.601 },
        { name: "인천", lat: 37.456, lng: 126.705 },
        { name: "광주", lat: 35.160, lng: 126.851 },
        { name: "대전", lat: 36.350, lng: 127.384 },
        { name: "울산", lat: 35.538, lng: 129.311 },
        { name: "세종", lat: 36.480, lng: 127.289 },
        { name: "경기 수원", lat: 37.263, lng: 127.028 },
        { name: "강원 춘천", lat: 37.881, lng: 127.729 },
        { name: "충북 청주", lat: 36.642, lng: 127.489 },
        { name: "충남 홍성", lat: 36.601, lng: 126.660 },
        { name: "전북 전주", lat: 35.824, lng: 127.147 },
        { name: "전북 남원", lat: 35.416, lng: 127.390 },
        { name: "전북 남원 대산", lat: 35.446, lng: 127.344 },
        { name: "전남 무안", lat: 34.990, lng: 126.471 },
        { name: "경북 안동", lat: 36.568, lng: 128.729 },
        { name: "경남 창원", lat: 35.227, lng: 128.681 },
        { name: "제주", lat: 33.499, lng: 126.531 },
    ];

    const handleLocationSelect = (e) => {
        const selected = KOREAN_LOCATIONS.find(l => l.name === e.target.value);
        if (selected) {
            setFarmData({
                ...farmData,
                location: selected.name,
                latitude: selected.lat,
                longitude: selected.lng
            });
        }
    };

    const isDark = theme === 'dark';

    return (
        <div>
            <div style={{ fontSize: "18px", fontWeight: 800, color: "var(--color-text)", display:"flex", alignItems:"center", gap:"8px", marginBottom: "20px" }}>
                <Settings size={20} /> 환경 설정
            </div>

            {/* Dark Mode Toggle */}
            <div style={{ background: "var(--color-bg-card)", padding: "18px 20px", borderRadius: "16px", boxShadow: "var(--shadow-sm)", marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span style={{ fontSize: "20px" }}>{isDark ? "🌙" : "☀️"}</span>
                    <div>
                        <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-text)" }}>다크모드</div>
                        <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>{isDark ? "어두운 테마 사용 중" : "밝은 테마 사용 중"}</div>
                    </div>
                </div>
                <button
                    onClick={onToggleTheme}
                    style={{
                        width: "52px",
                        height: "28px",
                        borderRadius: "14px",
                        border: "none",
                        cursor: "pointer",
                        position: "relative",
                        background: isDark ? "var(--color-primary)" : "var(--color-border)",
                        transition: "background 0.3s ease"
                    }}
                >
                    <div style={{
                        width: "22px",
                        height: "22px",
                        borderRadius: "50%",
                        background: "var(--color-bg-card)",
                        position: "absolute",
                        top: "3px",
                        left: isDark ? "27px" : "3px",
                        transition: "left 0.3s ease",
                        boxShadow: "0 1px 4px rgba(0,0,0,0.2)"
                    }} />
                </button>
            </div>

            {/* Widget Customization */}
            {widgetRegistry.length > 0 && (
            <div style={{ background: "var(--color-bg-card)", padding: "18px 20px", borderRadius: "16px", boxShadow: "var(--shadow-sm)", marginBottom: "20px" }}>
                <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-text)", marginBottom: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "18px" }}>🧩</span> 대시보드 위젯
                </div>
                <div style={{ fontSize: "11px", color: "var(--color-text-muted)", marginBottom: "12px" }}>
                    홈 화면에 표시할 위젯을 선택하세요.
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {widgetRegistry.map(w => {
                        const isOn = widgetVisible[w.id] !== false;
                        return (
                            <div key={w.id} style={{
                                display: "flex", justifyContent: "space-between", alignItems: "center",
                                padding: "10px 12px", borderRadius: "10px",
                                background: "var(--color-bg)", border: "1px solid var(--color-border)",
                                transition: "all 0.2s ease"
                            }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                    <span style={{ fontSize: "16px" }}>{w.icon}</span>
                                    <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text)" }}>{w.label}</span>
                                </div>
                                <button
                                    onClick={() => onToggleWidget(w.id)}
                                    style={{
                                        width: "44px", height: "24px", borderRadius: "12px",
                                        border: "none", cursor: "pointer", position: "relative",
                                        background: isOn ? "var(--color-success)" : "var(--color-border)",
                                        transition: "background 0.3s ease"
                                    }}
                                >
                                    <div style={{
                                        width: "18px", height: "18px", borderRadius: "50%",
                                        background: "var(--color-bg-card)", position: "absolute",
                                        top: "3px", left: isOn ? "23px" : "3px",
                                        transition: "left 0.3s ease",
                                        boxShadow: "0 1px 3px rgba(0,0,0,0.2)"
                                    }} />
                                </button>
                            </div>
                        );
                    })}
                </div>
            </div>
            )}

            {/* Farm Info Settings */}
            <div style={{ background: "var(--color-bg-card)", padding: "20px", borderRadius: "16px", boxShadow: "var(--shadow-sm)", marginBottom: "30px" }}>
                <div style={{ fontSize: "15px", fontWeight: 700, marginBottom: "16px", color: "var(--color-text)", display:"flex", alignItems:"center", gap:"6px" }}>
                    <MapPin size={16} /> 농장 정보 설정
                </div>
                <div style={{ display: "grid", gap: "16px" }}>
                    <div>
                        <label style={{ display: "block", fontSize: "12px", color: "var(--color-text-secondary)", marginBottom: "6px" }}>농장 이름</label>
                        <input
                            value={farmData.name}
                            onChange={e => setFarmData({ ...farmData, name: e.target.value })}
                            placeholder="예: 행복한 한우 농장"
                            style={{ width: "100%", padding: "12px", borderRadius: "8px", border: "1px solid var(--color-border)", fontSize:"14px", background:"var(--color-bg)", color:"var(--color-text)" }}
                        />
                    </div>
                    <div>
                        <label style={{ display: "block", fontSize: "12px", color: "var(--color-text-secondary)", marginBottom: "6px" }}>지역 선택 (자동 입력)</label>
                        <select onChange={handleLocationSelect} style={{ width: "100%", padding: "12px", borderRadius: "8px", border: "1px solid var(--color-border)", fontSize:"14px", marginBottom:"10px", background:"var(--color-bg)", color:"var(--color-text)" }}>
                            <option value="">주요 지역 선택...</option>
                            {KOREAN_LOCATIONS.map(l => (
                                <option key={l.name} value={l.name}>{l.name}</option>
                            ))}
                        </select>
                        <input
                            value={farmData.location}
                            onChange={e => setFarmData({ ...farmData, location: e.target.value })}
                            placeholder="지역명 직접 입력 (예: 남원시 대산면)"
                            style={{ width: "100%", padding: "12px", borderRadius: "8px", border: "1px solid var(--color-border)", fontSize:"14px", background:"var(--color-bg)", color:"var(--color-text)" }}
                        />
                    </div>
                    <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:"10px"}}>
                         <div>
                            <label style={{ display: "block", fontSize: "12px", color: "var(--color-text-secondary)", marginBottom: "6px" }}>위도 (Latitude)</label>
                            <input
                                type="number"
                                step="0.001"
                                value={farmData.latitude}
                                onChange={e => setFarmData({ ...farmData, latitude: e.target.value })}
                                placeholder="35.446"
                                style={{ width: "100%", padding: "12px", borderRadius: "8px", border: "1px solid var(--color-border)", fontSize:"14px", background:"var(--color-bg)", color:"var(--color-text)" }}
                            />
                        </div>
                        <div>
                            <label style={{ display: "block", fontSize: "12px", color: "var(--color-text-secondary)", marginBottom: "6px" }}>경도 (Longitude)</label>
                            <input
                                type="number"
                                step="0.001"
                                value={farmData.longitude}
                                onChange={e => setFarmData({ ...farmData, longitude: e.target.value })}
                                placeholder="127.344"
                                style={{ width: "100%", padding: "12px", borderRadius: "8px", border: "1px solid var(--color-border)", fontSize:"14px", background:"var(--color-bg)", color:"var(--color-text)" }}
                            />
                        </div>
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--color-text-muted)", marginBottom: "4px" }}>
                        * 지역을 선택하거나 구글 지도 등에서 좌표를 확인하여 입력해주세요. 정확한 날씨 정보를 위해 필요합니다.
                    </div>
                    <button onClick={handleSaveFarmSettings} style={{ width: "100%", padding: "14px", background: "var(--color-primary)", color: "var(--color-bg)", borderRadius: "10px", border: "none", fontWeight: 700, cursor: "pointer", marginTop:"4px" }}>
                        저장하기
                    </button>
                    <div style={{marginTop:"10px", borderTop:"1px dashed var(--color-border)", paddingTop:"10px", textAlign:"center"}}>
                        <a href="/admin/diagnostics" style={{fontSize:"12px", color:"var(--color-text-muted)", textDecoration:"none"}}>🛠️ 시스템 진단 도구</a>
                    </div>
                </div>
            </div>

            {/* Building Settings */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--color-text-secondary)" }}>축사 동 관리</div>
                <button onClick={() => setIsAdding(!isAdding)} style={{ fontSize: "12px", fontWeight: 700, color: "var(--color-text)", background: "var(--color-border-light)", borderRadius: "8px", padding: "6px 12px", border: "none", cursor: "pointer" }}>
                    {isAdding ? "취소" : "+ 동 추가"}
                </button>
            </div>

            {isAdding && (
                <div style={{ background: "var(--color-bg-card)", padding: "20px", borderRadius: "12px", boxShadow: "var(--shadow-sm)", marginBottom: "20px" }}>
                    <div style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px", color: "var(--color-text)" }}>새로운 축사 동 등록</div>
                    <div style={{ display: "grid", gap: "12px" }}>
                        <div>
                            <label style={{ display: "block", fontSize: "12px", color: "var(--color-text-secondary)", marginBottom: "4px" }}>동 이름 (예: 4동, 격리사)</label>
                            <input
                                value={formData.name}
                                onChange={e => setFormData({ ...formData, name: e.target.value })}
                                placeholder="동 이름을 입력하세요"
                                style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid var(--color-border)", background: "var(--color-bg)", color: "var(--color-text)" }}
                            />
                        </div>
                        <div>
                            <label style={{ display: "block", fontSize: "12px", color: "var(--color-text-secondary)", marginBottom: "4px" }}>칸 수 (Pen Count)</label>
                            <input
                                type="number"
                                value={formData.penCount}
                                onChange={e => setFormData({ ...formData, penCount: e.target.value })}
                                style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid var(--color-border)", background: "var(--color-bg)", color: "var(--color-text)" }}
                            />
                        </div>
                        <button onClick={handleSubmitBuilding} style={{ width: "100%", padding: "12px", background: "var(--color-success)", color: "white", borderRadius: "8px", border: "none", fontWeight: 700, cursor: "pointer" }}>
                            동 등록하기
                        </button>
                    </div>
                </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {buildings.map(b => (
                    <div key={b.id} style={{ background: "var(--color-bg-card)", padding: "16px", borderRadius: "12px", border: "1px solid var(--color-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div>
                            <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--color-text)" }}>{b.name}</div>
                            <div style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>총 {b.penCount}칸</div>
                        </div>
                        <button
                            onClick={() => { if(confirm("정말 삭제하시겠습니까?")) onDeleteBuilding(b.id); }}
                            style={{ fontSize: "12px", color: "var(--color-danger)", background: "none", border: "1px solid var(--color-danger)", padding: "4px 8px", borderRadius: "4px", cursor: "pointer" }}
                        >
                            삭제
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}
