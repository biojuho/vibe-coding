'use client';

import { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  createCattle,
  updateCattle,
  deleteCattle,
  recordCalving,
  createSalesRecord,
  addInventoryItem,
  updateInventoryQuantity,
  createScheduleEvent,
  toggleEventCompletion,
  recordFeed,
  createBuilding,
  deleteBuilding,
  updateFarmSettings,
} from '@/lib/actions';
import { useAppFeedback } from '@/components/feedback/FeedbackProvider';
import { formatMoney } from '@/lib/utils';
import { buildNotifications } from '@/lib/notifications';
import { TabBar, WeatherWidget, EstrusAlertBanner, CalvingAlertBanner } from '@/components/widgets/widgets';
import { StatCard, PenCard, CattleRow } from '@/components/ui/cards';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { PremiumInfoCard } from '@/components/ui/premium-card';
import { PremiumButton } from '@/components/ui/premium-button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Bell, Plus, ArrowLeft, WifiOff } from 'lucide-react';
import CalvingTab from '@/components/tabs/CalvingTab';
import InventoryTab from '@/components/tabs/InventoryTab';
import ScheduleTab from '@/components/tabs/ScheduleTab';
import SettingsTab from '@/components/tabs/SettingsTab';
import CattleForm from '@/components/forms/CattleForm';
import CattleDetailModal from '@/components/forms/CattleDetailModal';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/lib/useTheme';
import { useOnlineStatus } from '@/lib/useOnlineStatus';
import { enqueue, queueSize } from '@/lib/offlineQueue';
import { syncOfflineQueue } from '@/lib/syncManager';

import NotificationModal from '@/components/ui/NotificationModal';
import ExcelExportButton from '@/components/widgets/ExcelExportButton';
import MarketPriceWidget from '@/components/widgets/MarketPriceWidget';

const FeedTab = dynamic(() => import('@/components/tabs/FeedTab'), { ssr: false });
const SalesTab = dynamic(() => import('@/components/tabs/SalesTab'), { ssr: false });
const AnalysisTab = dynamic(() => import('@/components/tabs/AnalysisTab'), { ssr: false });
const FinancialChartWidget = dynamic(() => import('@/components/widgets/FinancialChartWidget'), { ssr: false });
const AIChatWidget = dynamic(() => import('@/components/widgets/AIChatWidget'), { ssr: false });
const NotificationWidget = dynamic(() => import('@/components/widgets/NotificationWidget'), { ssr: false });

const WIDGET_REGISTRY = [
  { id: 'weather', label: '날씨 / THI', icon: '🌤️', defaultOn: true },
  { id: 'market', label: '시세 정보', icon: '💰', defaultOn: true },
  { id: 'notification', label: '알림 (발정/분만)', icon: '🔔', defaultOn: true },
  { id: 'financial', label: '경영 분석 차트', icon: '📊', defaultOn: true },
  { id: 'estrus', label: '발정 알림 배너', icon: '💕', defaultOn: true },
  { id: 'calving', label: '분만 알림 배너', icon: '🍼', defaultOn: true },
  { id: 'stats', label: '핵심 통계', icon: '📈', defaultOn: true },
];

const WIDGETS_STORAGE_KEY = 'joolife-widgets';

function useWidgetSettings() {
  const [visible, setVisible] = useState(() => {
    const defaults = Object.fromEntries(WIDGET_REGISTRY.map((widget) => [widget.id, widget.defaultOn]));
    if (typeof window === 'undefined') return defaults;
    try {
      const saved = localStorage.getItem(WIDGETS_STORAGE_KEY);
      if (saved) return { ...defaults, ...JSON.parse(saved) };
    } catch {}
    return defaults;
  });

  const toggle = (id) => {
    setVisible((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      localStorage.setItem(WIDGETS_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

  return { visible, toggle };
}

export default function DashboardClient({
  initialCattleRegistry,
  initialSalesLedger,
  initialSummary,
  initialFeedStandards,
  initialInventory,
  initialSchedule,
  initialFeedHistory,
  initialBuildings,
  initialFarmSettings,
  initialExpenses,
  initialMarketPrice,
}) {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const { notify, confirm } = useAppFeedback();
  const widgetSettings = useWidgetSettings();
  const isOnline = useOnlineStatus();
  const [activeTab, setActiveTab] = useState('home');

  // Pagination hooks — these are the PRIMARY data sources for cattle and sales

  // Summary data from SSR (headcount, monthly rollup, building occupancy)
  const [summary, setSummary] = useState(initialSummary);

  const [feedStandards, setFeedStandards] = useState(initialFeedStandards);
  const [inventoryList, setInventoryList] = useState(initialInventory);
  const [scheduleEvents, setScheduleEvents] = useState(initialSchedule);
  const [feedHistory, setFeedHistory] = useState(initialFeedHistory);
  const [buildings, setBuildings] = useState(initialBuildings);
  const [farmSettings, setFarmSettings] = useState(initialFarmSettings);
  const [expenseRecords, setExpenseRecords] = useState(initialExpenses || []);

  const [weather, setWeather] = useState({
    temp: 20,
    condition: 'Clear',
    humidity: 50,
    wind: 2,
    locationName: initialFarmSettings.location || 'Seoul',
  });
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedCow, setSelectedCow] = useState(null);
  const [isEditing, setIsEditing] = useState(false);

  const [selectedBuildingId, setSelectedBuildingId] = useState(null);
  const [selectedPenId, setSelectedPenId] = useState(null);

  const [showNotifications, setShowNotifications] = useState(false);
  const [cattleRegistry, setCattleRegistry] = useState(initialCattleRegistry || []);
  const [salesLedger, setSalesLedger] = useState(initialSalesLedger || []);

  // Full registries power alerts, analytics, forms, and pen occupancy.
  const cattleList = cattleRegistry;
  const saleRecords = salesLedger;

  // Notifications must consider the full active herd.
  const notifications = buildNotifications(cattleList);

  // Helper to refresh summary from API (after mutations)
  const refreshSummary = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/summary?fresh=1');
      if (res.ok) {
        const json = await res.json();
        if (json.success) {
          setSummary(json.data);
        }
      }
    } catch (err) {
      console.error('Failed to refresh summary:', err);
    }
  }, []);

  const showSuccess = (title, description = '') => {
    notify({ title, description, variant: 'success' });
  };

  const showWarning = (title, description = '') => {
    notify({ title, description, variant: 'warning' });
  };

  const showError = (title, description = '') => {
    notify({ title, description, variant: 'error' });
  };

  const sortByName = (items) => [...items].sort((left, right) => left.name.localeCompare(right.name));
  const sortInventoryItems = (items) =>
    [...items].sort(
      (left, right) =>
        (left.category || '').localeCompare(right.category || '') || left.name.localeCompare(right.name),
    );
  const sortByDateAsc = (items, key) => [...items].sort((left, right) => new Date(left[key]) - new Date(right[key]));
  const sortByDateDesc = (items, key) => [...items].sort((left, right) => new Date(right[key]) - new Date(left[key]));

  useEffect(() => {
    const fetchWeather = async (lat, lng) => {
      try {
        const params = [
          `latitude=${lat}`,
          `longitude=${lng}`,
          'current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature',
          'daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
          'forecast_days=3',
          'timezone=Asia/Seoul',
        ].join('&');
        const res = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
        const data = await res.json();
        const current = data.current;
        const daily = data.daily;

        const forecast =
          daily?.time?.map((date, index) => ({
            date,
            weatherCode: daily.weather_code[index],
            tempMax: daily.temperature_2m_max[index],
            tempMin: daily.temperature_2m_min[index],
            precipProb: daily.precipitation_probability_max?.[index] || 0,
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
          locationName: farmSettings.location || 'Seoul',
          forecast,
        });
      } catch (error) {
        console.error('Weather fetch error', error);
      }
    };

    if (farmSettings.latitude && farmSettings.longitude) {
      fetchWeather(farmSettings.latitude, farmSettings.longitude);
    } else if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => fetchWeather(position.coords.latitude, position.coords.longitude),
        () => fetchWeather(35.446, 127.344),
      );
    } else {
      fetchWeather(35.446, 127.344);
    }
  }, [farmSettings.latitude, farmSettings.longitude, farmSettings.location]);

  useEffect(() => {
    if (!isOnline || queueSize() === 0) {
      return undefined;
    }

    let cancelled = false;

    void (async () => {
      try {
        const { synced, failed, reused } = await syncOfflineQueue();
        if (cancelled || reused || synced === 0) {
          return;
        }
        notify({
            title: failed > 0 ? '오프라인 작업을 일부 동기화했습니다.' : '오프라인 작업 동기화가 완료되었습니다.',
            description:
              failed > 0
                ? `${synced}건은 반영되었고 ${failed}건은 다시 시도해 주세요.`
                : `${synced}건이 서버에 반영되었습니다.`,
            variant: failed > 0 ? 'warning' : 'success',
          });
        router.refresh();
      } catch (error) {
        if (cancelled) {
          return;
        }

        console.error('Offline queue sync failed:', error);
        notify({
          title: '?ㅽ봽?쇱씤 ?묒뾽 ?숆린?붿뿉 ?ㅽ뙣?덉뒿?덈떎.',
          description: '?좎떆 ???ㅼ떆 ?쒕룄?댁＜?몄슂.',
          variant: 'warning',
        });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isOnline, notify, router]);

  const handleTestSMS = () => {
    showSuccess('테스트 SMS를 발송했습니다.', 'Joolife: 분만 임박 알림 - 순심이(0001) 예정일 3일 전입니다.');
  };

  const handleUpdateFarmSettings = async (data) => {
    const res = await updateFarmSettings(data);
    if (!res.success) {
      showError('농장 정보를 저장하지 못했습니다.', res.message);
      return false;
    }

    setFarmSettings(res.data);
    showSuccess('농장 정보가 저장되었습니다.');
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
      setCattleRegistry((prev) => [newCattle, ...prev]);
      setShowAddModal(false);
      showWarning(offlineTitle, offlineDescription);
      return true;
    }

    try {
      const result = await createCattle(newCattle);
      if (result.success) {
        const savedCattle = result.data || newCattle;
        setCattleRegistry((prev) => [savedCattle, ...prev]);
        setShowAddModal(false);
        refreshSummary();
        if (!skipSuccessFeedback) {
          showSuccess(successTitle, successDescription);
        }
        return true;
      }

      showError(errorTitle, result.message);
      return false;
    } catch (error) {
      showError(errorTitle, error.message);
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
      setCattleRegistry((prev) => prev.map((cow) => (cow.id === updated.id ? updated : cow)));
      setIsEditing(false);
      if (selectedCow && selectedCow.id === updated.id) setSelectedCow(updated);
      showWarning(offlineTitle, offlineDescription);
      return true;
    }

    try {
      const result = await updateCattle(updated.id, updated);
      if (result.success) {
        const savedCattle = result.data || updated;
        setCattleRegistry((prev) => prev.map((cow) => (cow.id === savedCattle.id ? savedCattle : cow)));
        setIsEditing(false);
        if (selectedCow && selectedCow.id === savedCattle.id) setSelectedCow(savedCattle);
        refreshSummary();
        if (!skipSuccessFeedback) {
          showSuccess(successTitle, successDescription);
        }
        return true;
      }

      showError(errorTitle, result.message);
      return false;
    } catch (error) {
      showError(errorTitle, error.message);
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
      if (result.success) {
        setCattleRegistry((prev) => prev.filter((cow) => cow.id !== id));
        setSelectedCow(null);
        refreshSummary();
        showSuccess('개체를 삭제했습니다.');
        return true;
      }

      showError('개체 삭제에 실패했습니다.', result.message);
      return false;
    } catch {
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

    setInventoryList((prev) => sortInventoryItems([res.data, ...prev]));
    showSuccess('재고 항목이 추가되었습니다.');
    return true;
  };

  const handleUpdateQuantity = async (id, qty) => {
    const res = await updateInventoryQuantity(id, qty);
    if (!res.success) {
      showError('재고 수량을 수정하지 못했습니다.', res.message);
      return false;
    }

    setInventoryList((prev) => prev.map((item) => (item.id === res.data.id ? res.data : item)));
    showSuccess('재고 수량을 업데이트했습니다.');
    return true;
  };

  const handleCreateEvent = async (data) => {
    const res = await createScheduleEvent(data);
    if (!res.success) {
      showError('일정을 등록하지 못했습니다.', res.message);
      return false;
    }

    setScheduleEvents((prev) => sortByDateAsc([res.data, ...prev], 'date'));
    showSuccess('일정을 등록했습니다.');
    return true;
  };

  const handleToggleEvent = async (id, isCompleted) => {
    const res = await toggleEventCompletion(id, isCompleted);
    if (!res.success) {
      showError('일정 상태를 변경하지 못했습니다.', res.message);
      return false;
    }

    setScheduleEvents((prev) => prev.map((event) => (event.id === res.data.id ? res.data : event)));
    showSuccess(isCompleted ? '일정을 완료 처리했습니다.' : '일정을 다시 진행 중으로 변경했습니다.');
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

    setSalesLedger((prev) => sortByDateDesc([res.data, ...prev], 'saleDate'));
    refreshSummary();
    showSuccess('판매 기록이 등록되었습니다.');
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

    setFeedHistory((prev) => sortByDateDesc([res.data, ...prev], 'date').slice(0, 20));
    showSuccess('급여 기록이 완료되었습니다.');
    return true;
  };

  const handleCreateBuilding = async (data) => {
    const res = await createBuilding(data);
    if (!res.success) {
      showError('축사 정보를 추가하지 못했습니다.', res.message);
      return false;
    }

    setBuildings((prev) => sortByName([res.data, ...prev]));
    showSuccess('축사를 추가했습니다.');
    return true;
  };

  const handleDeleteBuilding = async (id) => {
    const res = await deleteBuilding(id);
    if (!res.success) {
      showError('축사를 삭제하지 못했습니다.', res.message);
      return false;
    }

    setBuildings((prev) => prev.filter((building) => building.id !== id));
    if (selectedBuildingId === id) {
      setSelectedBuildingId(null);
      setSelectedPenId(null);
    }
    showSuccess('축사를 삭제했습니다.');
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
      setCattleRegistry((prev) => [calfDraft, ...prev.map((cow) => (cow.id === motherId ? updatedMother : cow))]);
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

    setCattleRegistry((prev) => [savedCalf, ...prev.map((cow) => (cow.id === motherId ? savedMother : cow))]);
    refreshSummary();
    showSuccess('분만 처리가 완료되었습니다.', `${mother.name}의 상태와 송아지 등록이 함께 반영되었습니다.`);
    return true;
  };

  const handleDragDrop = async (cattleId, toBuildingId, toPenNumber) => {
    const cow = cattleList.find((item) => item.id === cattleId);
    if (!cow) return;
    if (cow.buildingId === toBuildingId && cow.penNumber === toPenNumber) return;

    const penCattle = cattleList.filter((item) => item.buildingId === toBuildingId && item.penNumber === toPenNumber);
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

  // Stats from summary (SSR-snapshot, refreshed after mutations)
  const totalHeadcount = summary?.headcount?.totalActive ?? cattleList.length;
  const monthlySalesTotal = summary?.monthlyRollup?.salesTotal ?? 0;
  const monthlySalesCount = saleRecords.filter((record) => {
    const saleMonth = new Date(record.saleDate).getMonth();
    return saleMonth === new Date().getMonth();
  }).length;
  const avgWeight = cattleList.length > 0
    ? Math.floor(cattleList.reduce((sum, cow) => sum + (cow.weight || 0), 0) / cattleList.length)
    : 0;

  const renderContent = () => {
    if (activeTab === 'feed') {
      return (
        <FeedTab
          cattle={cattleList}
          feedStandards={feedStandards}
          feedHistory={feedHistory}
          onRecordFeed={handleRecordFeed}
          buildings={buildings}
        />
      );
    }
    if (activeTab === 'calving') return <CalvingTab cattle={cattleList} onRecordCalving={handleRecordCalving} />;
    if (activeTab === 'sales') {
      return (
        <SalesTab
          saleRecords={saleRecords}
          cattleList={cattleList}
          onCreateSale={handleCreateSale}
          expenseRecords={expenseRecords}
          initialMarketPrice={initialMarketPrice}
        />
      );
    }
    if (activeTab === 'inventory') {
      return <InventoryTab inventory={inventoryList} onAddItem={handleAddItem} onUpdateQuantity={handleUpdateQuantity} />;
    }
    if (activeTab === 'schedule') {
      return <ScheduleTab events={scheduleEvents} onCreateEvent={handleCreateEvent} onToggleEvent={handleToggleEvent} />;
    }
    if (activeTab === 'analysis') {
      return <AnalysisTab saleRecords={saleRecords} feedHistory={feedHistory} cattleList={cattleList} expenseRecords={expenseRecords} />;
    }
    if (activeTab === 'settings') {
      return (
        <SettingsTab
          buildings={buildings}
          onCreateBuilding={handleCreateBuilding}
          onDeleteBuilding={handleDeleteBuilding}
          farmSettings={farmSettings}
          onUpdateFarmSettings={handleUpdateFarmSettings}
          theme={theme}
          onToggleTheme={toggleTheme}
          widgetRegistry={WIDGET_REGISTRY}
          widgetVisible={widgetSettings.visible}
          onToggleWidget={widgetSettings.toggle}
        />
      );
    }

    return (
      <>
        {/* Header — generous breathing room for visual hierarchy */}
        <div className="animate-fadeInDown flex justify-between items-start mb-7 pt-2 pb-1">
          <div>
            <h1 className="text-[26px] font-extrabold text-foreground tracking-[-0.02em] mb-1.5 leading-tight">
              {farmSettings.name || 'Joolife Dashboard'}
            </h1>
            <p className="text-[13px] text-muted-foreground leading-relaxed">오늘도 힘찬 하루 되세요! 🐮</p>
          </div>
          <div className="flex gap-2.5 pt-0.5">
            <ExcelExportButton cattleList={cattleList} />
            <PremiumButton variant="outline" size="icon" onClick={() => setShowNotifications(true)} className="relative shadow-[var(--shadow-sm)]">
              <Bell className="h-5 w-5" />
              {notifications.some((notification) => notification.level === 'critical') && (
                <span className="absolute top-1.5 right-1.5 h-2.5 w-2.5 rounded-full bg-destructive border-2 border-background animate-pulse shadow-[0_0_10px_hsl(var(--destructive))]" />
              )}
            </PremiumButton>
            <PremiumButton size="icon" onClick={() => setShowAddModal(true)} className="shadow-[var(--shadow-button-primary)]">
              <Plus className="h-5 w-5" />
            </PremiumButton>
          </div>
        </div>

        {showNotifications && <NotificationModal notifications={notifications} onClose={() => setShowNotifications(false)} onTestSMS={handleTestSMS} />}

        {widgetSettings.visible.weather && <WeatherWidget weather={weather} />}
        {widgetSettings.visible.market && <MarketPriceWidget initialData={initialMarketPrice} />}
        {widgetSettings.visible.notification && <NotificationWidget notifications={notifications} />}
        {widgetSettings.visible.financial && <FinancialChartWidget saleRecords={saleRecords} feedHistory={feedHistory} expenseRecords={expenseRecords} />}
        {widgetSettings.visible.estrus && <EstrusAlertBanner cattle={cattleList} buildings={buildings} />}
        {widgetSettings.visible.calving && <CalvingAlertBanner cattle={cattleList} buildings={buildings} />}

        {widgetSettings.visible.stats && (
          <div style={{ display: 'flex', gap: '14px', overflowX: 'auto', paddingBottom: '14px', marginBottom: '28px', scrollSnapType: 'x mandatory', scrollPadding: '0 4px', WebkitOverflowScrolling: 'touch' }}>
            <PremiumInfoCard title="총 사육두수" value={`${totalHeadcount}두`} change="전월 대비 +0" changeType="positive" />
            <PremiumInfoCard
              title="이번달 출하"
              value={`${monthlySalesCount}두`}
              change={`매출 ${formatMoney(monthlySalesTotal / 10000)}만`}
              changeType="positive"
            />
            <PremiumInfoCard title="평균 체중" value={`${avgWeight}kg`} change="전체 평균 유지" changeType="positive" />
          </div>
        )}

        {!selectedBuildingId ? (
          <div className="animate-fadeInUp" style={{ animationDelay: '200ms' }}>
            <div className="section-header">
              <span className="section-header-icon">🏠</span>
              <h2 className="section-header-title">축사 현황</h2>
            </div>
            <div className="grid gap-3">
              {buildings.map((building, index) => {
                const buildingHeadcount = summary?.buildingOccupancy?.find((b) => b.buildingId === building.id)?.headcount
                  ?? cattleList.filter((cow) => cow.buildingId === building.id).length;
                return (
                  <Card key={building.id} onClick={() => setSelectedBuildingId(building.id)} className="animate-fadeInUp cursor-pointer hover:-translate-y-1 hover:shadow-[var(--shadow-md)] group/building" style={{ animationDelay: `${250 + index * 50}ms` }}>
                    <CardContent className="flex justify-between items-center p-5">
                      <div>
                        <div className="font-bold text-[15px] mb-1.5 tracking-[-0.01em]">{building.name}</div>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {building.description || `총 ${building.penCount}칸`} · <strong className="text-foreground">{buildingHeadcount}두</strong>
                        </p>
                      </div>
                      <span className="text-xl text-muted-foreground transition-[transform,color,opacity] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] opacity-40 group-hover/building:translate-x-1 group-hover/building:text-[var(--color-primary-custom)] group-hover/building:opacity-100">›</span>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        ) : !selectedPenId ? (
          <div className="animate-fadeIn">
            <div className="flex items-center gap-3 mb-4">
              <PremiumButton variant="ghost" size="icon" onClick={() => setSelectedBuildingId(null)} className="h-9 w-9">
                <ArrowLeft className="h-5 w-5" />
              </PremiumButton>
              <h2 className="text-lg font-extrabold text-foreground">{buildings.find((building) => building.id === selectedBuildingId)?.name}</h2>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '12px' }}>
              {[...Array(buildings.find((building) => building.id === selectedBuildingId)?.penCount || 32)].map((_, index) => {
                const penNum = index + 1;
                const penCattle = cattleList.filter((cow) => cow.buildingId === selectedBuildingId && cow.penNumber === penNum);
                return <PenCard key={penNum} penNumber={penNum} cattle={penCattle} buildingId={selectedBuildingId} onSelect={(_buildingId, penId) => setSelectedPenId(penId)} onDrop={handleDragDrop} delay={index * 20} />;
              })}
            </div>
          </div>
        ) : (
          <div className="animate-fadeIn">
            <div className="flex items-center gap-3 mb-4">
              <PremiumButton variant="ghost" size="icon" onClick={() => setSelectedPenId(null)} className="h-9 w-9">
                <ArrowLeft className="h-5 w-5" />
              </PremiumButton>
              <h2 className="text-lg font-extrabold text-foreground">{selectedPenId}번 칸 상세</h2>
            </div>
            <div className="flex flex-col gap-3">
              {cattleList.filter((cow) => cow.buildingId === selectedBuildingId && cow.penNumber === selectedPenId).map((cow, index) => (
                <CattleRow key={cow.id} cow={cow} onClick={setSelectedCow} delay={index * 50} draggable />
              ))}
              {cattleList.filter((cow) => cow.buildingId === selectedBuildingId && cow.penNumber === selectedPenId).length === 0 && (
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
          <div className="mb-3 flex items-center gap-2.5 rounded-[20px] px-4 py-3 text-sm font-bold text-white shadow-[var(--shadow-md)]" style={{ background: 'linear-gradient(145deg, color-mix(in srgb, var(--color-warning) 72%, white 28%), var(--color-warning))', border: '1px solid rgba(255,255,255,0.2)' }}>
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

      {showAddModal && <CattleForm onSubmit={handleAddCattle} onCancel={() => setShowAddModal(false)} />}

      {isEditing && selectedCow && (
        <CattleForm cattle={selectedCow} onSubmit={(updated) => { handleUpdateCattle(updated); setIsEditing(false); }} onCancel={() => setIsEditing(false)} />
      )}

      {selectedCow && !isEditing && (
        <CattleDetailModal cattle={selectedCow} onClose={() => setSelectedCow(null)} onEdit={() => setIsEditing(true)} onDelete={() => handleDeleteCattle(selectedCow.id)} onUpdate={handleUpdateCattle} />
      )}

      <footer className="footer-glass mt-16 mx-2 px-6 pt-8 pb-6 text-center text-xs text-muted-foreground leading-relaxed">
        <div className="font-bold text-sm text-primary mb-3 flex items-center justify-center gap-2">🐄 Joolife (쥬라프)</div>
        <p className="mb-1">대표: 박주호 | Business License: 000-00-00000</p>
        <p className="mb-1">Contact: 010-3159-3708 | joolife@joolife.io.kr</p>
        <p className="text-[11px] text-muted-foreground/60 mb-4">Address: 경기 안양시 동안구 관평로212번길 21 공작부영아파트 309동 1312호</p>
        <Separator className="mb-4 opacity-40" />
        <div className="flex justify-center gap-5 flex-wrap">
          <a href="/terms" className="no-underline text-muted-foreground hover:text-foreground transition-[color,transform] duration-200 py-1 hover:-translate-y-px">이용약관</a>
          <a href="/privacy" className="no-underline text-muted-foreground hover:text-foreground transition-[color,transform] duration-200 py-1 hover:-translate-y-px">개인정보처리방침</a>
          <a href="/subscription" className="no-underline text-primary font-semibold hover:text-foreground transition-[color,transform] duration-200 py-1 hover:-translate-y-px">⭐ 프리미엄 구독</a>
        </div>
        <p className="mt-4 text-[11px] text-muted-foreground/50">Copyright &copy; 2026 Joolife. All rights reserved.</p>
      </footer>
    </div>
  );
}
