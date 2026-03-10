'use client';

import { useState, useEffect } from 'react';
import { createCattle, updateCattle, deleteCattle, createSalesRecord, addInventoryItem, updateInventoryQuantity, createScheduleEvent, toggleEventCompletion, recordFeed, createBuilding, deleteBuilding, updateFarmSettings, getNotifications } from '@/lib/actions';
import { BUILDINGS, NAMWON_LAT, NAMWON_LNG } from '@/lib/constants';
import { formatMoney } from '@/lib/utils';
import { PlusIcon } from '@/components/ui/common';
import { TabBar, WeatherWidget, EstrusAlertBanner, CalvingAlertBanner } from '@/components/widgets/widgets';
import { StatCard, PenCard, CattleRow } from '@/components/ui/cards';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Bell, Plus, ArrowLeft, WifiOff } from 'lucide-react';
import FeedTab from '@/components/tabs/FeedTab';
import CalvingTab from '@/components/tabs/CalvingTab';
import SalesTab from '@/components/tabs/SalesTab';
import InventoryTab from '@/components/tabs/InventoryTab';
import ScheduleTab from '@/components/tabs/ScheduleTab';
import SettingsTab from '@/components/tabs/SettingsTab';
import AnalysisTab from '@/components/tabs/AnalysisTab';
import CattleForm from '@/components/forms/CattleForm';
import CattleDetailModal from '@/components/forms/CattleDetailModal';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/lib/useTheme';
import { useOnlineStatus } from '@/lib/useOnlineStatus';
import { enqueue, queueSize } from '@/lib/offlineQueue';
import { syncOfflineQueue } from '@/lib/syncManager';

import NotificationModal from '@/components/ui/NotificationModal';
import FinancialChartWidget from '@/components/widgets/FinancialChartWidget';
import ExcelExportButton from '@/components/widgets/ExcelExportButton';
import AIChatWidget from '@/components/widgets/AIChatWidget';
import NotificationWidget from '@/components/widgets/NotificationWidget';
import MarketPriceWidget from '@/components/widgets/MarketPriceWidget';

const WIDGET_REGISTRY = [
  { id: "weather", label: "날씨 / THI", icon: "🌤️", defaultOn: true },
  { id: "market", label: "시세 정보", icon: "💰", defaultOn: true },
  { id: "notification", label: "알림 (발정/분만)", icon: "🔔", defaultOn: true },
  { id: "financial", label: "경영 분석 차트", icon: "📊", defaultOn: true },
  { id: "estrus", label: "발정 알림 배너", icon: "💕", defaultOn: true },
  { id: "calving", label: "분만 알림 배너", icon: "🍼", defaultOn: true },
  { id: "stats", label: "핵심 통계", icon: "📈", defaultOn: true },
];

const WIDGETS_STORAGE_KEY = "joolife-widgets";

function useWidgetSettings() {
  const [visible, setVisible] = useState(() => {
    if (typeof window === "undefined") return {};
    try {
      const saved = localStorage.getItem(WIDGETS_STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {}
    return Object.fromEntries(WIDGET_REGISTRY.map(w => [w.id, w.defaultOn]));
  });

  useEffect(() => {
    // Ensure new widgets have defaults
    setVisible(prev => {
      const merged = { ...Object.fromEntries(WIDGET_REGISTRY.map(w => [w.id, w.defaultOn])), ...prev };
      return merged;
    });
  }, []);

  const toggle = (id) => {
    setVisible(prev => {
      const next = { ...prev, [id]: !prev[id] };
      localStorage.setItem(WIDGETS_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

  return { visible, toggle };
}

export default function DashboardClient({ initialCattle, initialSales, initialFeedStandards, initialInventory, initialSchedule, initialFeedHistory, initialBuildings, initialFarmSettings, initialExpenses }) {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const widgetSettings = useWidgetSettings();
  const isOnline = useOnlineStatus();
  const [activeTab, setActiveTab] = useState("home");
  const [cattleList, setCattleList] = useState(initialCattle);
  const [saleRecords, setSaleRecords] = useState(initialSales);
  const [feedStandards, setFeedStandards] = useState(initialFeedStandards);
  const [inventoryList, setInventoryList] = useState(initialInventory);
  const [scheduleEvents, setScheduleEvents] = useState(initialSchedule);
  const [feedHistory, setFeedHistory] = useState(initialFeedHistory);
  const [buildings, setBuildings] = useState(initialBuildings);
  const [farmSettings, setFarmSettings] = useState(initialFarmSettings);
  const [expenseRecords, setExpenseRecords] = useState(initialExpenses || []);
  
  const [weather, setWeather] = useState({ temp: 20, condition: "Clear", humidity: 50, wind: 2, locationName: initialFarmSettings.location || "Seoul" });
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedCow, setSelectedCow] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  
  const [selectedBuildingId, setSelectedBuildingId] = useState(null); // Filter by Building
  const [selectedPenId, setSelectedPenId] = useState(null); // Filter by Pen

  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([]);
  
  // Weather Fetch
  useEffect(() => {
    const fetchWeather = async (lat, lng) => {
      try {
        const params = [
          `latitude=${lat}`,
          `longitude=${lng}`,
          `current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature`,
          `daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max`,
          `forecast_days=3`,
          `timezone=Asia/Seoul`
        ].join("&");
        const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
        const data = await res.json();
        const current = data.current;
        const daily = data.daily;

        const forecast = daily?.time?.map((date, i) => ({
          date,
          weatherCode: daily.weather_code[i],
          tempMax: daily.temperature_2m_max[i],
          tempMin: daily.temperature_2m_min[i],
          precipProb: daily.precipitation_probability_max?.[i] || 0
        })) || [];

        setWeather({
          temp: current.temperature_2m,
          humidity: current.relative_humidity_2m,
          windSpeed: current.wind_speed_10m,
          apparentTemp: current.apparent_temperature,
          weatherCode: current.weather_code,
          tempMax: forecast[0]?.tempMax ?? current.temperature_2m + 3,
          tempMin: forecast[0]?.tempMin ?? current.temperature_2m - 3,
          precipitation: forecast[0]?.precipProb ?? 0,
          locationName: farmSettings.location || "Seoul",
          forecast
        });
      } catch (e) {
        console.error("Weather fetch error", e);
      }
    };

    // Use farm settings lat/lng first, fallback to geolocation
    if (farmSettings.latitude && farmSettings.longitude) {
      fetchWeather(farmSettings.latitude, farmSettings.longitude);
    } else if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => fetchWeather(pos.coords.latitude, pos.coords.longitude),
        () => fetchWeather(35.446, 127.344) // fallback: Namwon
      );
    } else {
      fetchWeather(35.446, 127.344);
    }
  }, [farmSettings.latitude, farmSettings.longitude, farmSettings.location]);

  // Check for Notifications on Load
  useEffect(() => {
    const loadNotes = async () => {
        try {
            const data = await getNotifications();
            setNotifications(data);
        } catch(e) {
            console.error(e);
        }
    };
    loadNotes();
  }, [initialCattle]);

  // Auto-sync when coming back online
  useEffect(() => {
    if (isOnline && queueSize() > 0) {
      syncOfflineQueue().then(({ synced, failed }) => {
        if (synced > 0) {
          alert(`오프라인 작업 ${synced}건 동기화 완료${failed > 0 ? ` (${failed}건 실패)` : ''}`);
          router.refresh();
        }
      });
    }
  }, [isOnline, router]);

  const handleTestSMS = () => {
      alert("✅ [테스트] 등록된 번호로 SMS가 발송되었습니다.\n'Joolife: 분만 임박 알림 - 순심이(0001) 예정일 3일 전입니다.'");
  };

  const handleUpdateFarmSettings = async (data) => {
    const res = await updateFarmSettings(data);
    if (!res.success) alert(res.message);
    else {
        setFarmSettings(res.data);
        alert("농장 정보가 저장되었습니다.");
        router.refresh();
    }
  };

  const handleAddCattle = async (newCattle) => {
    if (!isOnline) {
      enqueue('createCattle', [newCattle]);
      setCattleList(prev => [newCattle, ...prev]);
      setShowAddModal(false);
      return alert("오프라인: 등록이 대기열에 저장되었습니다.");
    }
    try {
      const result = await createCattle(newCattle);
      if (result.success) {
        setCattleList(prev => [newCattle, ...prev]);
        setShowAddModal(false);
        alert("등록되었습니다.");
        router.refresh();
      } else {
        alert("등록 실패: " + result.message);
      }
    } catch (e) {
      alert("오류 발생: " + e.message);
    }
  };
  
  const handleUpdateCattle = async (updated) => {
    if (!isOnline) {
      enqueue('updateCattle', [updated.id, updated]);
      setCattleList(prev => prev.map(c => c.id === updated.id ? updated : c));
      setIsEditing(false);
      if (selectedCow && selectedCow.id === updated.id) setSelectedCow(updated);
      return alert("오프라인: 수정이 대기열에 저장되었습니다.");
    }
    try {
      const result = await updateCattle(updated.id, updated);
      if (result.success) {
        setCattleList(prev => prev.map(c => c.id === updated.id ? updated : c));
        setIsEditing(false);
        if (selectedCow && selectedCow.id === updated.id) setSelectedCow(updated);
        router.refresh();
      } else {
        alert("수정 실패: " + result.message);
      }
    } catch (e) {
      alert("오류 발생: " + e.message);
    }
  };

  const handleDeleteCattle = async (id) => {
    if(confirm("정말 삭제하시겠습니까?")){
        try {
            const result = await deleteCattle(id);
            if(result.success) {
                setCattleList(prev => prev.filter(c => c.id !== id));
                setSelectedCow(null);
                router.refresh();
            } else {
                alert("삭제 실패: " + result.message);
            }
        } catch(e) {
            alert("삭제 중 오류가 발생했습니다.");
        }
    }
  };

  const handleAddItem = async (data) => {
    const res = await addInventoryItem(data);
    if(!res.success) alert(res.message); else router.refresh();
  };

  const handleUpdateQuantity = async (id, qty) => {
    const res = await updateInventoryQuantity(id, qty);
    if(!res.success) alert(res.message); else router.refresh();
  };

  const handleCreateEvent = async (data) => {
    const res = await createScheduleEvent(data);
    if(!res.success) alert(res.message); else router.refresh();
  };

  const handleToggleEvent = async (id, isCompleted) => {
    const res = await toggleEventCompletion(id, isCompleted);
    if(!res.success) alert(res.message); else router.refresh();
  };

  const handleCreateSale = async (data) => {
    if (!isOnline) {
      enqueue('createSalesRecord', [data]);
      return alert("오프라인: 판매 기록이 대기열에 저장되었습니다.");
    }
    const res = await createSalesRecord(data);
    if(!res.success) alert(res.message); else {
        alert("판매 기록이 등록되었습니다.");
        router.refresh();
    }
  };

  const handleRecordFeed = async (data) => {
    if (!isOnline) {
      enqueue('recordFeed', [data]);
      return alert("오프라인: 급여 기록이 대기열에 저장되었습니다.");
    }
    const res = await recordFeed(data);
    if (!res.success) alert(res.message);
    else {
      alert("급여 기록이 완료되었습니다.");
      router.refresh();
    }
  };

  const handleCreateBuilding = async (data) => {
    const res = await createBuilding(data);
    if (!res.success) alert(res.message); else router.refresh();
  };

  const handleDeleteBuilding = async (id) => {
    const res = await deleteBuilding(id);
    if (!res.success) alert(res.message); else router.refresh();
  };

  const handleDragDrop = async (cattleId, toBuildingId, toPenNumber) => {
    const cow = cattleList.find(c => c.id === cattleId);
    if (!cow) return;
    if (cow.buildingId === toBuildingId && cow.penNumber === toPenNumber) return;
    const penCattle = cattleList.filter(c => c.buildingId === toBuildingId && c.penNumber === toPenNumber);
    if (penCattle.length >= 5) return alert("이 칸은 이미 가득 찼습니다 (최대 5두).");
    if (!confirm(`${cow.name}을(를) ${buildings.find(b=>b.id===toBuildingId)?.name || toBuildingId} ${toPenNumber}번 칸으로 이동하시겠습니까?`)) return;
    const updated = { ...cow, buildingId: toBuildingId, penNumber: toPenNumber };
    await handleUpdateCattle(updated);
  };

  // Render Content based on Tab
  const renderContent = () => {
    if (activeTab === "feed") return <FeedTab cattle={cattleList} feedStandards={feedStandards} feedHistory={feedHistory} onRecordFeed={handleRecordFeed} buildings={buildings} />;
    if (activeTab === "calving") return <CalvingTab cattle={cattleList} onUpdateCattle={handleUpdateCattle} onCreateCattle={handleAddCattle} />;
    if (activeTab === "sales") return <SalesTab saleRecords={saleRecords} cattleList={cattleList} onCreateSale={handleCreateSale} expenseRecords={expenseRecords} />;
    
    if (activeTab === "inventory") return <InventoryTab inventory={inventoryList} onAddItem={handleAddItem} onUpdateQuantity={handleUpdateQuantity} />;
    if (activeTab === "schedule") return <ScheduleTab events={scheduleEvents} onCreateEvent={handleCreateEvent} onToggleEvent={handleToggleEvent} />;
    if (activeTab === "analysis") return <AnalysisTab saleRecords={saleRecords} feedHistory={feedHistory} cattleList={cattleList} expenseRecords={expenseRecords} />;
    if (activeTab === "settings") return <SettingsTab buildings={buildings} onCreateBuilding={handleCreateBuilding} onDeleteBuilding={handleDeleteBuilding} farmSettings={farmSettings} onUpdateFarmSettings={handleUpdateFarmSettings} theme={theme} onToggleTheme={toggleTheme} widgetRegistry={WIDGET_REGISTRY} widgetVisible={widgetSettings.visible} onToggleWidget={widgetSettings.toggle} />;
    
    // Default: Home Tab
    return (
      <>
        {/* Header Section */}
        <div className="animate-fadeInDown flex justify-between items-center mb-5 py-1">
          <div>
            <h1 className="text-2xl font-extrabold text-foreground tracking-tight mb-1">
              {farmSettings.name || "Joolife Dashboard"}
            </h1>
            <p className="text-sm text-muted-foreground">오늘도 힘찬 하루 되세요! 🐮</p>
          </div>
          <div className="flex gap-2.5">
            <ExcelExportButton cattleList={cattleList} />
            <Button
              variant="outline"
              size="icon"
              onClick={()=>setShowNotifications(true)}
              className="relative shadow-md"
            >
              <Bell className="h-5 w-5" />
              {notifications.some(n=>n.type==='urgent') && (
                <span className="absolute top-1.5 right-1.5 h-2.5 w-2.5 rounded-full bg-destructive border-2 border-background animate-pulse shadow-[0_0_8px_hsl(var(--destructive))]" />
              )}
            </Button>
            <Button
              size="icon"
              onClick={()=>setShowAddModal(true)}
              className="shadow-[0_4px_16px_rgba(62,47,28,0.35)]"
            >
              <Plus className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {showNotifications && <NotificationModal notifications={notifications} onClose={()=>setShowNotifications(false)} onTestSMS={handleTestSMS} />}

        {widgetSettings.visible.weather && <WeatherWidget weather={weather} />}
        {widgetSettings.visible.market && <MarketPriceWidget />}
        {widgetSettings.visible.notification && <NotificationWidget />}
        {widgetSettings.visible.financial && <FinancialChartWidget saleRecords={saleRecords} feedHistory={feedHistory} expenseRecords={expenseRecords} />}
        {widgetSettings.visible.estrus && <EstrusAlertBanner cattle={cattleList} buildings={buildings} />}
        {widgetSettings.visible.calving && <CalvingAlertBanner cattle={cattleList} buildings={buildings} />}

        {/* Key Stats */}
        {widgetSettings.visible.stats && (
        <div style={{
          display:"flex",
          gap:"12px",
          overflowX:"auto",
          paddingBottom:"12px",
          marginBottom:"24px",
          scrollSnapType:"x mandatory"
        }}>
          <StatCard label="총 사육두수" value={`${cattleList.length}두`} sub="전월 대비 +0" color="var(--color-primary-light)" delay={0} />
          <StatCard label="이번달 출하" value={`${saleRecords.filter(r=>new Date(r.saleDate).getMonth()===new Date().getMonth()).length}두`} sub={`매출 ${formatMoney(saleRecords.filter(r=>new Date(r.saleDate).getMonth()===new Date().getMonth()).reduce((s,c)=>s+c.price,0)/10000)}만`} color="var(--color-success)" delay={50} />
          <StatCard label="평균 체중" value={`${Math.floor(cattleList.reduce((s,c)=>s+c.weight,0)/cattleList.length||0)}kg`} sub="전체 평균" color="var(--color-warning)" delay={100} />
        </div>
        )}

        {/* Building/Pen Selection */}
        {!selectedBuildingId ? (
          <div className="animate-fadeInUp" style={{animationDelay:"200ms"}}>
            <h2 className="text-[17px] font-extrabold text-foreground mb-3.5 flex items-center gap-2">
              <span>🏠</span> 축사 현황
            </h2>
            <div className="grid gap-3">
              {buildings.map((b, idx) => (
                <Card
                  key={b.id}
                  onClick={() => setSelectedBuildingId(b.id)}
                  className="animate-fadeInUp cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all"
                  style={{animationDelay:`${250 + idx*50}ms`}}
                >
                  <CardContent className="flex justify-between items-center p-4">
                    <div>
                      <div className="font-bold text-base mb-1">{b.name}</div>
                      <p className="text-sm text-muted-foreground">
                        {b.description || `총 ${b.penCount}칸`} · <strong>{cattleList.filter(c=>c.buildingId===b.id).length}두</strong>
                      </p>
                    </div>
                    <span className="text-xl text-muted-foreground transition-transform">›</span>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ) : !selectedPenId ? (
          <div className="animate-fadeIn">
            <div className="flex items-center gap-3 mb-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={()=>setSelectedBuildingId(null)}
                className="h-9 w-9"
              >
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <h2 className="text-lg font-extrabold text-foreground">
                {buildings.find(b=>b.id===selectedBuildingId)?.name}
              </h2>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:"12px"}}>
              {[...Array(buildings.find(b=>b.id===selectedBuildingId)?.penCount || 32)].map((_, i) => {
                const penNum = i + 1;
                const penCattle = cattleList.filter(c => c.buildingId === selectedBuildingId && c.penNumber === penNum);
                return <PenCard key={penNum} penNumber={penNum} cattle={penCattle} buildingId={selectedBuildingId} onSelect={(bid, pid) => setSelectedPenId(pid)} onDrop={handleDragDrop} delay={i*20} />;
              })}
            </div>
          </div>
        ) : (
          <div className="animate-fadeIn">
            <div className="flex items-center gap-3 mb-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={()=>setSelectedPenId(null)}
                className="h-9 w-9"
              >
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <h2 className="text-lg font-extrabold text-foreground">{selectedPenId}번 칸 상세</h2>
            </div>
            <div className="flex flex-col gap-3">
              {cattleList.filter(c => c.buildingId === selectedBuildingId && c.penNumber === selectedPenId).map((cow, idx) => (
                <CattleRow key={cow.id} cow={cow} onClick={setSelectedCow} delay={idx*50} draggable={true} />
              ))}
              {cattleList.filter(c => c.buildingId === selectedBuildingId && c.penNumber === selectedPenId).length === 0 && (
                <Card className="animate-fadeIn border-2 border-dashed">
                  <CardContent className="text-center py-12 px-5">
                    <div className="text-3xl mb-2">🐄</div>
                    <p className="text-muted-foreground">이 칸은 비어있습니다.</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}
        
        <AIChatWidget />
      </>
    );
  };

  return (
    <div className="dashboard-container">
      <div className="max-w-[600px] mx-auto p-4 relative">
        {!isOnline && (
          <div className="bg-amber-500 text-white rounded-lg mb-3 flex items-center gap-2.5 px-4 py-2.5 text-sm font-bold shadow-md">
            <WifiOff className="h-5 w-5 flex-shrink-0" />
            오프라인 모드 — 작업은 저장되어 연결 복구 시 자동 동기화됩니다
            {queueSize() > 0 && (
              <Badge variant="secondary" className="ml-auto bg-white/30 text-white border-0 text-xs">
                {queueSize()}건 대기
              </Badge>
            )}
          </div>
        )}
        {renderContent()}
      </div>
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
      
      {/* Modals */}
      {showAddModal && <CattleForm onSubmit={handleAddCattle} onCancel={()=>setShowAddModal(false)} />}
      
      {isEditing && selectedCow && (
        <CattleForm cattle={selectedCow} onSubmit={(updated)=>{handleUpdateCattle(updated); setIsEditing(false);}} onCancel={()=>setIsEditing(false)} />
      )}
      
      {selectedCow && !isEditing && (
        <CattleDetailModal 
            cattle={selectedCow} 
            onClose={()=>setSelectedCow(null)} 
            onEdit={()=>setIsEditing(true)} 
            onDelete={()=>handleDeleteCattle(selectedCow.id)} 
            onUpdate={handleUpdateCattle} 
        />
      )}
      {/* Footer */}
      <footer className="mt-12 px-5 pt-6 pb-4 text-center text-xs text-muted-foreground leading-relaxed">
        <Separator className="mb-6" />
        <div className="font-bold text-sm text-primary mb-2 flex items-center justify-center gap-1.5">
          🐄 Joolife (쥬라프)
        </div>
        <p>대표: 박주호 | Business License: 000-00-00000</p>
        <p>Contact: 010-3159-3708 | joolife@joolife.io.kr</p>
        <p className="text-[11px] text-muted-foreground/70">
          Address: 경기 안양시 동안구 관평로212번길 21 공작부영아파트 309동 1312호
        </p>
        <div className="mt-3 flex justify-center gap-4 flex-wrap">
          <a href="/terms" className="no-underline text-muted-foreground hover:text-foreground transition-colors py-1">이용약관</a>
          <a href="/privacy" className="no-underline text-muted-foreground hover:text-foreground transition-colors py-1">개인정보처리방침</a>
          <a href="/subscription" className="no-underline text-amber-600 dark:text-amber-400 font-semibold hover:text-amber-500 transition-colors py-1">⭐ 프리미엄 구독</a>
        </div>
        <p className="mt-3.5 text-[11px] text-muted-foreground/60">
          Copyright © 2026 Joolife. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
