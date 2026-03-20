'use client';

import { useState, useEffect } from 'react';
import { createCattle, updateCattle, deleteCattle, recordCalving, createSalesRecord, addInventoryItem, updateInventoryQuantity, createScheduleEvent, toggleEventCompletion, recordFeed, createBuilding, deleteBuilding, updateFarmSettings, getNotifications } from '@/lib/actions';
import { useAppFeedback } from '@/components/feedback/FeedbackProvider';
import { formatMoney } from '@/lib/utils';
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
    const defaults = Object.fromEntries(WIDGET_REGISTRY.map(w => [w.id, w.defaultOn]));
    if (typeof window === "undefined") return defaults;
    try {
      const saved = localStorage.getItem(WIDGETS_STORAGE_KEY);
      if (saved) return { ...defaults, ...JSON.parse(saved) };
    } catch {}
    return defaults;
  });

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
  const { notify, confirm } = useAppFeedback();
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

  const showSuccess = (title, description = '') => {
    notify({ title, description, variant: 'success' });
  };

  const showWarning = (title, description = '') => {
    notify({ title, description, variant: 'warning' });
  };

  const showError = (title, description = '') => {
    notify({ title, description, variant: 'error' });
  };

  
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
          notify({
            title: failed > 0 ? '오프라인 작업을 일부 동기화했습니다.' : '오프라인 작업 동기화가 완료되었습니다.',
            description:
              failed > 0
                ? `${synced}건은 반영되었고 ${failed}건은 다시 시도해 주세요.`
                : `${synced}건이 서버에 반영되었습니다.`,
            variant: failed > 0 ? 'warning' : 'success',
          });
          router.refresh();
        }
      });
    }
  }, [isOnline, notify, router]);

  const handleTestSMS = () => {
      showSuccess(
        '테스트 SMS를 발송했습니다.',
        "Joolife: 분만 임박 알림 - 순심이(0001) 예정일 3일 전입니다.",
      );
  };

  const handleUpdateFarmSettings = async (data) => {
    const res = await updateFarmSettings(data);
    if (!res.success) {
      showError('농장 정보를 저장하지 못했습니다.', res.message);
      return false;
    }

    setFarmSettings(res.data);
    showSuccess('농장 정보가 저장되었습니다.');
    router.refresh();
    return true;
  };

  const handleAddCattle = async (newCattle, feedbackOptions = {}) => {
    const {
      successTitle = '개체가 등록되었습니다.',
      successDescription = '',
      errorTitle = '개체 등록에 실패했습니다.',
      offlineTitle = '오프라인 상태입니다.',
      offlineDescription = '등록 요청이 대기열에 저장되었습니다.',
      skipSuccessFeedback = false,
    } = feedbackOptions;

    if (!isOnline) {
      enqueue('createCattle', [newCattle]);
      setCattleList(prev => [newCattle, ...prev]);
      setShowAddModal(false);
      showWarning(offlineTitle, offlineDescription);
      return true;
    }

    try {
      const result = await createCattle(newCattle);
      if (result.success) {
        const savedCattle = result.data || newCattle;
        setCattleList(prev => [savedCattle, ...prev]);
        setShowAddModal(false);
        if (!skipSuccessFeedback) {
          showSuccess(successTitle, successDescription);
        }
        router.refresh();
        return true;
      } else {
        showError(errorTitle, result.message);
        return false;
      }
    } catch (e) {
      showError(errorTitle, e.message);
      return false;
    }
  };
  
  const handleUpdateCattle = async (updated, feedbackOptions = {}) => {
    const {
      successTitle = '개체 정보를 수정했습니다.',
      successDescription = '',
      errorTitle = '개체 수정에 실패했습니다.',
      offlineTitle = '오프라인 상태입니다.',
      offlineDescription = '수정 요청이 대기열에 저장되었습니다.',
      skipSuccessFeedback = false,
    } = feedbackOptions;

    if (!isOnline) {
      enqueue('updateCattle', [updated.id, updated]);
      setCattleList(prev => prev.map(c => c.id === updated.id ? updated : c));
      setIsEditing(false);
      if (selectedCow && selectedCow.id === updated.id) setSelectedCow(updated);
      showWarning(offlineTitle, offlineDescription);
      return true;
    }

    try {
      const result = await updateCattle(updated.id, updated);
      if (result.success) {
        const savedCattle = result.data || updated;
        setCattleList(prev => prev.map(c => c.id === savedCattle.id ? savedCattle : c));
        setIsEditing(false);
        if (selectedCow && selectedCow.id === savedCattle.id) setSelectedCow(savedCattle);
        if (!skipSuccessFeedback) {
          showSuccess(successTitle, successDescription);
        }
        router.refresh();
        return true;
      } else {
        showError(errorTitle, result.message);
        return false;
      }
    } catch (e) {
      showError(errorTitle, e.message);
      return false;
    }
  };

  const handleDeleteCattle = async (id) => {
    const targetCattle = cattleList.find((cow) => cow.id === id);
    const shouldDelete = await confirm({
      title: '개체를 삭제할까요?',
      description: targetCattle
        ? `${targetCattle.name} (${targetCattle.tagNumber}) 정보가 목록에서 제거됩니다.`
        : '삭제한 데이터는 되돌릴 수 없습니다.',
      confirmLabel: '삭제',
      cancelLabel: '취소',
      variant: 'destructive',
    });

    if (!shouldDelete) {
      return false;
    }

    try {
      const result = await deleteCattle(id);
      if(result.success) {
        setCattleList(prev => prev.filter(c => c.id !== id));
        setSelectedCow(null);
        showSuccess('개체를 삭제했습니다.');
        router.refresh();
        return true;
      }

      showError('개체 삭제에 실패했습니다.', result.message);
      return false;
    } catch(e) {
      showError('개체 삭제 중 오류가 발생했습니다.');
      return false;
    }
  };

  const handleAddItem = async (data) => {
    const res = await addInventoryItem(data);
    if (!res.success) {
      showError('재고 항목을 추가하지 못했습니다.', res.message);
      return false;
    }

    showSuccess('재고 항목이 추가되었습니다.');
    router.refresh();
    return true;
  };

  const handleUpdateQuantity = async (id, qty) => {
    const res = await updateInventoryQuantity(id, qty);
    if (!res.success) {
      showError('재고 수량을 수정하지 못했습니다.', res.message);
      return false;
    }

    showSuccess('재고 수량을 업데이트했습니다.');
    router.refresh();
    return true;
  };

  const handleCreateEvent = async (data) => {
    const res = await createScheduleEvent(data);
    if (!res.success) {
      showError('일정을 등록하지 못했습니다.', res.message);
      return false;
    }

    showSuccess('일정을 등록했습니다.');
    router.refresh();
    return true;
  };

  const handleToggleEvent = async (id, isCompleted) => {
    const res = await toggleEventCompletion(id, isCompleted);
    if (!res.success) {
      showError('일정 상태를 변경하지 못했습니다.', res.message);
      return false;
    }

    showSuccess(isCompleted ? '일정을 완료 처리했습니다.' : '일정을 다시 진행 중으로 변경했습니다.');
    router.refresh();
    return true;
  };

  const handleCreateSale = async (data) => {
    if (!isOnline) {
      enqueue('createSalesRecord', [data]);
      showWarning('오프라인 상태입니다.', '판매 기록이 대기열에 저장되었습니다.');
      return true;
    }

    const res = await createSalesRecord(data);
    if (!res.success) {
      showError('판매 기록을 등록하지 못했습니다.', res.message);
      return false;
    }

    showSuccess('판매 기록이 등록되었습니다.');
    router.refresh();
    return true;
  };

  const handleRecordFeed = async (data) => {
    if (!isOnline) {
      enqueue('recordFeed', [data]);
      showWarning('오프라인 상태입니다.', '급여 기록이 대기열에 저장되었습니다.');
      return true;
    }

    const res = await recordFeed(data);
    if (!res.success) {
      showError('급여 기록을 저장하지 못했습니다.', res.message);
      return false;
    }

    showSuccess('급여 기록이 완료되었습니다.');
    router.refresh();
    return true;
  };

  const handleCreateBuilding = async (data) => {
    const res = await createBuilding(data);
    if (!res.success) {
      showError('축사 정보를 추가하지 못했습니다.', res.message);
      return false;
    }

    showSuccess('축사를 추가했습니다.');
    router.refresh();
    return true;
  };

  const handleDeleteBuilding = async (id) => {
    const res = await deleteBuilding(id);
    if (!res.success) {
      showError('축사를 삭제하지 못했습니다.', res.message);
      return false;
    }

    showSuccess('축사를 삭제했습니다.');
    router.refresh();
    return true;
  };

  const handleRecordCalving = async ({ motherId, calvingDate, calfGender }) => {
    const mother = cattleList.find((cow) => cow.id === motherId);

    if (!mother) {
      showError('분만 대상 개체를 찾지 못했습니다.');
      return false;
    }

    const calfTagNumber = `KR0000-${String(Math.floor(Math.random() * 900000) + 100000)}`;
    const updatedMother = {
      ...mother,
      status: '번식우',
      pregnancyDate: null,
      lastEstrus: null,
      memo: mother.memo
        ? `${mother.memo}\n[분만] ${calvingDate} ${calfGender} 송아지 분만`
        : `[분만] ${calvingDate} ${calfGender} 송아지 분만`,
    };
    const calfDraft = {
      id: `new_${Date.now()}`,
      tagNumber: calfTagNumber,
      name: `${mother.name}의 송아지`,
      buildingId: mother.buildingId,
      penNumber: mother.penNumber,
      gender: calfGender,
      birthDate: new Date(calvingDate).toISOString(),
      weight: 25,
      status: '송아지',
      memo: `모체 ${mother.tagNumber} (${mother.name})`,
      geneticInfo: {
        father: mother.geneticFather || '미상',
        mother: mother.tagNumber,
        grade: '-',
      },
    };

    if (!isOnline) {
      enqueue('recordCalving', [{ motherId, calvingDate, calfGender, calfTagNumber }]);
      setCattleList((prev) => [calfDraft, ...prev.map((cow) => (cow.id === motherId ? updatedMother : cow))]);
      showWarning('오프라인 상태입니다.', '분만 처리 요청이 대기열에 저장되었습니다.');
      return true;
    }

    const res = await recordCalving({ motherId, calvingDate, calfGender, calfTagNumber });

    if (!res.success) {
      showError('분만 처리를 완료하지 못했습니다.', res.message);
      return false;
    }

    const savedMother = res.data?.mother || updatedMother;
    const savedCalf = res.data?.calf || calfDraft;

    setCattleList((prev) => [savedCalf, ...prev.map((cow) => (cow.id === motherId ? savedMother : cow))]);
    showSuccess('분만 처리가 완료되었습니다.', `${mother.name}의 상태와 송아지 등록이 함께 반영되었습니다.`);
    router.refresh();
    return true;
  };

  const handleDragDrop = async (cattleId, toBuildingId, toPenNumber) => {
    const cow = cattleList.find(c => c.id === cattleId);
    if (!cow) return;
    if (cow.buildingId === toBuildingId && cow.penNumber === toPenNumber) return;
    const penCattle = cattleList.filter(c => c.buildingId === toBuildingId && c.penNumber === toPenNumber);
    const targetBuilding = buildings.find((building) => building.id === toBuildingId);
    const targetLabel = `${targetBuilding?.name || toBuildingId} ${toPenNumber}번 칸`;

    if (penCattle.length >= 5) {
      showWarning('이 칸은 이미 가득 찼습니다.', '한 칸에는 최대 5두까지만 배치할 수 있습니다.');
      return false;
    }

    const shouldMove = await confirm({
      title: '개체를 이동할까요?',
      description: `${cow.name}을(를) ${targetLabel}(으)로 이동합니다.`,
      confirmLabel: '이동',
      cancelLabel: '취소',
    });

    if (!shouldMove) {
      return false;
    }

    const updated = { ...cow, buildingId: toBuildingId, penNumber: toPenNumber };
    return handleUpdateCattle(updated, {
      successTitle: '개체를 이동했습니다.',
      successDescription: `${cow.name}을(를) ${targetLabel}(으)로 옮겼습니다.`,
      offlineTitle: '오프라인 상태입니다.',
      offlineDescription: `${cow.name} 이동 요청이 대기열에 저장되었습니다.`,
    });
  };

  // Render Content based on Tab
  const renderContent = () => {
    if (activeTab === "feed") return <FeedTab cattle={cattleList} feedStandards={feedStandards} feedHistory={feedHistory} onRecordFeed={handleRecordFeed} buildings={buildings} />;
    if (activeTab === "calving") return <CalvingTab cattle={cattleList} onRecordCalving={handleRecordCalving} />;
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
            <h1 className="text-2xl font-extrabold text-foreground tracking-[0.04em] mb-1">
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
              className="relative shadow-[var(--shadow-sm)]"
            >
              <Bell className="h-5 w-5" />
              {notifications.some(n=>n.type==='urgent') && (
                <span className="absolute top-1.5 right-1.5 h-2.5 w-2.5 rounded-full bg-destructive border-2 border-background animate-pulse shadow-[0_0_8px_hsl(var(--destructive))]" />
              )}
            </Button>
            <Button
              size="icon"
              onClick={()=>setShowAddModal(true)}
              className="shadow-[var(--shadow-button-primary)]"
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
                  className="animate-fadeInUp cursor-pointer hover:-translate-y-1 transition-all"
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
          <div className="mb-3 flex items-center gap-2.5 rounded-[20px] px-4 py-3 text-sm font-bold text-white shadow-[var(--shadow-md)]" style={{ background: "linear-gradient(145deg, color-mix(in srgb, var(--color-warning) 72%, white 28%), var(--color-warning))", border: "1px solid rgba(255,255,255,0.2)" }}>
            <WifiOff className="h-5 w-5 flex-shrink-0" />
            오프라인 모드 — 작업은 저장되어 연결 복구 시 자동 동기화됩니다
            {queueSize() > 0 && (
              <Badge variant="secondary" className="ml-auto border-white/15 bg-white/25 text-white text-xs shadow-none">
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
          <a href="/subscription" className="no-underline text-primary font-semibold hover:text-foreground transition-colors py-1">⭐ 프리미엄 구독</a>
        </div>
        <p className="mt-3.5 text-[11px] text-muted-foreground/60">
          Copyright © 2026 Joolife. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
