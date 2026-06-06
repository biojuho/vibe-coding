"use client";

import {
	AlertTriangle,
	ArrowLeft,
	Bell,
	CalendarDays,
	ChartSpline,
	Check,
	ClipboardList,
	ClipboardPlus,
	Home,
	PackageCheck,
	PackagePlus,
	Plus,
	ReceiptText,
	Settings,
	WifiOff,
} from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAppFeedback } from "@/components/feedback/FeedbackProvider";
import CattleDetailModal from "@/components/forms/CattleDetailModal";
import CattleForm from "@/components/forms/CattleForm";
import CalvingTab from "@/components/tabs/CalvingTab";
import InventoryTab from "@/components/tabs/InventoryTab";
import ScheduleTab from "@/components/tabs/ScheduleTab";
import SettingsTab from "@/components/tabs/SettingsTab";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { CattleRow, PenCard, StatCard } from "@/components/ui/cards";
import NotificationModal from "@/components/ui/NotificationModal";
import { PremiumButton } from "@/components/ui/premium-button";
import { PremiumInfoCard } from "@/components/ui/premium-card";
import { Separator } from "@/components/ui/separator";
import {
	CalvingAlertBanner,
	EstrusAlertBanner,
} from "@/components/widgets/AlertBanners";
import ExcelExportButton from "@/components/widgets/ExcelExportButton";
import FieldModeView from "@/components/widgets/FieldModeView";
import MarketPriceWidget from "@/components/widgets/MarketPriceWidget";
import { ProfitabilityWidget } from "@/components/widgets/ProfitabilityWidget";
import { TabBar, WeatherWidget } from "@/components/widgets/widgets";
import {
	addInventoryItem,
	createBuilding,
	createCattle,
	createSalesRecord,
	createScheduleEvent,
	deleteBuilding,
	deleteCattle,
	getNotifications,
	recordCalving,
	recordFeed,
	toggleEventCompletion,
	updateCattle,
	updateFarmSettings,
	updateInventoryQuantity,
} from "@/lib/actions";
import { playTactileClick } from "@/lib/audio";
import { getNextDashboardPaginationState } from "@/lib/dashboard/pagination-guard.mjs";
import { buildSetupProgressItems } from "@/lib/dashboard/setup-progress.mjs";
import { buildTodayFocusItems } from "@/lib/dashboard/today-focus.mjs";
import { fetchWithTimeout, isTimeoutError } from "@/lib/fetchWithTimeout";
import { useCattlePagination } from "@/lib/hooks/useCattlePagination";
import { useSalesPagination } from "@/lib/hooks/useSalesPagination";
import { useDashboardModals } from "@/lib/hooks/useDashboardModals";
import {
	useWidgetSettings,
	WIDGET_REGISTRY,
} from "@/lib/hooks/useWidgetSettings";
import { enqueue, queueSize } from "@/lib/offlineQueue";
import { syncOfflineQueue } from "@/lib/syncManager";
import { useOnlineStatus } from "@/lib/useOnlineStatus";
import { useTheme } from "@/lib/useTheme";
import { formatMoney, toFiniteNumber } from "@/lib/utils";
import {
	buildUnavailableWeatherState,
	markWeatherAsStale,
	normalizeWeatherPayload,
	readWeatherApiResponseSafely,
	WEATHER_STALE_MESSAGE,
	WEATHER_TIMEOUT_MESSAGE,
	WEATHER_UNAVAILABLE_MESSAGE,
} from "@/lib/weather-state.mjs";

const FeedTab = dynamic(() => import("@/components/tabs/FeedTab"), {
	ssr: false,
});
const SalesTab = dynamic(() => import("@/components/tabs/SalesTab"), {
	ssr: false,
});
const AnalysisTab = dynamic(() => import("@/components/tabs/AnalysisTab"), {
	ssr: false,
});
const FinancialChartWidget = dynamic(
	() => import("@/components/widgets/FinancialChartWidget"),
	{ ssr: false },
);
const AIChatWidget = dynamic(
	() => import("@/components/widgets/AIChatWidget"),
	{ ssr: false },
);
const AIInsightWidget = dynamic(
	() => import("@/components/widgets/AIInsightWidget"),
	{ ssr: false },
);
const NotificationWidget = dynamic(
	() => import("@/components/widgets/NotificationWidget"),
	{ ssr: false },
);

const NOTIFICATION_MODAL_ID = "notification-center-dialog";
const DASHBOARD_PAGE_LIMIT = 100;
const OFFLINE_SYNC_REFRESH_ERROR_MESSAGE =
	"동기화 결과를 보려면 화면을 새로고침해 주세요.";
const FULL_CATTLE_LOAD_ERROR_MESSAGE =
	"전체 개체 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.";
const FULL_SALES_LOAD_ERROR_MESSAGE =
	"전체 판매 기록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.";

function toStrictIsoDateOrNull(value) {
	if (typeof value !== "string") {
		return null;
	}

	const normalized = value.trim();
	if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
		return null;
	}

	const date = new Date(`${normalized}T00:00:00.000Z`);
	return Number.isNaN(date.getTime()) ||
		date.toISOString().slice(0, 10) !== normalized
		? null
		: date.toISOString();
}

const FOCUS_ICON_BY_TYPE = {
	alert: AlertTriangle,
	offline: WifiOff,
	schedule: CalendarDays,
	stock: PackageCheck,
	sales: ChartSpline,
};

const QUICK_ACTIONS = [
	{
		id: "add-cattle",
		label: "개체 등록",
		detail: "새 송아지·입식우",
		icon: ClipboardPlus,
		tone: "primary",
	},
	{
		id: "record-sale",
		label: "출하 기록",
		detail: "판매 기록 바로 입력",
		icon: ReceiptText,
		tone: "success",
		targetTab: "sales",
	},
	{
		id: "add-schedule",
		label: "일정 추가",
		detail: "검진·백신·번식",
		icon: CalendarDays,
		tone: "info",
		targetTab: "schedule",
	},
	{
		id: "add-inventory",
		label: "재고 등록",
		detail: "사료·약품 보충",
		icon: PackagePlus,
		tone: "warning",
		targetTab: "inventory",
	},
];

function getSortableDateTime(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? null : date.getTime();
}

function toValidCalendarDate(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	if (Number.isNaN(date.getTime())) {
		return null;
	}

	if (typeof value === "string") {
		const dateKey = value.trim().slice(0, 10);
		if (/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) {
			const strictDate = new Date(`${dateKey}T00:00:00.000Z`);
			if (
				Number.isNaN(strictDate.getTime()) ||
				strictDate.toISOString().slice(0, 10) !== dateKey
			) {
				return null;
			}
		}
	}

	return date;
}

function normalizeDashboardBuildings(buildings) {
	if (!Array.isArray(buildings)) return [];

	return buildings
		.filter(
			(building) =>
				building &&
				typeof building === "object" &&
				!Array.isArray(building) &&
				building.id != null,
		)
		.map((building, index) => ({
			...building,
			id: building.id,
			name:
				typeof building.name === "string" && building.name.trim().length > 0
					? building.name
					: "축사 이름 미등록",
			penCount: Math.max(
				1,
				Math.floor(toFiniteNumber(building.penCount) || 32),
			),
			description:
				typeof building.description === "string" ? building.description : "",
			_displayIndex: index,
		}));
}

function normalizeDashboardItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) =>
					item &&
					typeof item === "object" &&
					!Array.isArray(item) &&
					item.id != null,
			)
		: [];
}

function normalizeDashboardCattleList(cattleItems) {
	return normalizeDashboardItems(cattleItems).map((cow) => ({
		...cow,
		id: cow.id,
		name:
			typeof cow.name === "string" && cow.name.trim().length > 0
				? cow.name
				: "개체명 미등록",
	}));
}

function normalizeDashboardNotifications(notifications) {
	return Array.isArray(notifications)
		? notifications.filter(
				(notification) =>
					notification &&
					typeof notification === "object" &&
					!Array.isArray(notification),
			)
		: [];
}

function normalizeDashboardClientOptions(options) {
	const safeOptions =
		options && typeof options === "object" && !Array.isArray(options) ? options : {};

	return {
		initialCattlePage: safeOptions.initialCattlePage,
		initialSalesPage: safeOptions.initialSalesPage,
		initialSummary: safeOptions.initialSummary,
		initialNotifications: safeOptions.initialNotifications ?? [],
		initialFeedStandards: safeOptions.initialFeedStandards ?? [],
		initialInventory: safeOptions.initialInventory ?? [],
		initialSchedule: safeOptions.initialSchedule ?? [],
		initialFeedHistory: safeOptions.initialFeedHistory ?? [],
		initialBuildings: safeOptions.initialBuildings ?? [],
		initialFarmSettings: safeOptions.initialFarmSettings ?? {},
		initialExpenses: safeOptions.initialExpenses ?? [],
		initialMarketPrice: safeOptions.initialMarketPrice ?? null,
		initialProfitability: safeOptions.initialProfitability ?? null,
	};
}

function normalizeFullListLoadOptions(options) {
	const safeOptions =
		options && typeof options === "object" && !Array.isArray(options) ? options : {};

	return {
		silent: safeOptions.silent === true,
	};
}

function normalizeDashboardHelperOptions(options) {
	const safeOptions =
		options && typeof options === "object" && !Array.isArray(options) ? options : {};

	return {
		items: safeOptions.items ?? [],
		buildings: safeOptions.buildings ?? [],
		cattleList: safeOptions.cattleList ?? [],
		onOpenNotifications:
			typeof safeOptions.onOpenNotifications === "function"
				? safeOptions.onOpenNotifications
				: () => {},
		onNavigate:
			typeof safeOptions.onNavigate === "function"
				? safeOptions.onNavigate
				: () => {},
		onAction:
			typeof safeOptions.onAction === "function" ? safeOptions.onAction : () => {},
		progress: safeOptions.progress ?? null,
		buildingId: safeOptions.buildingId,
		penId: safeOptions.penId,
		onSelect:
			typeof safeOptions.onSelect === "function" ? safeOptions.onSelect : () => {},
		onCreateEvent: safeOptions.onCreateEvent,
	};
}

function normalizeDashboardHelperItems(items) {
	return Array.isArray(items)
		? items.filter((item) => item && typeof item === "object" && !Array.isArray(item) && item.id != null)
		: [];
}

export default function DashboardClient(options = {}) {
	const {
		initialCattlePage,
		initialSalesPage,
		initialSummary,
		initialNotifications,
		initialFeedStandards,
		initialInventory,
		initialSchedule,
		initialFeedHistory,
		initialBuildings,
		initialFarmSettings,
		initialExpenses,
		initialMarketPrice,
		initialProfitability,
	} = normalizeDashboardClientOptions(options);
	const router = useRouter();
	const { theme, toggleTheme } = useTheme();
	const { notify, confirm } = useAppFeedback();
	const widgetSettings = useWidgetSettings();
	const isOnline = useOnlineStatus();
	const [activeTab, setActiveTab] = useState("home");
	const [isFieldMode, setIsFieldMode] = useState(false);

	// Pagination hooks — these are the PRIMARY data sources for cattle and sales

	// Summary data from SSR (headcount, monthly rollup, building occupancy)
	const [summary, setSummary] = useState(initialSummary);
	// Cache metadata from /api/dashboard/summary (source: 'snapshot'|'rebuilt'|'live', staleAt, ageSeconds).
	// Null until the first client-side refresh — SSR seeds `summary` only.
	const [summaryMeta, setSummaryMeta] = useState(null);
	const [notifications, setNotifications] = useState(() =>
		normalizeDashboardNotifications(initialNotifications),
	);

	const [feedStandards, setFeedStandards] = useState(initialFeedStandards);
	const [inventoryList, setInventoryList] = useState(initialInventory);
	const [scheduleEvents, setScheduleEvents] = useState(initialSchedule);
	const [feedHistory, setFeedHistory] = useState(initialFeedHistory);
	const [buildings, setBuildings] = useState(() =>
		normalizeDashboardBuildings(initialBuildings),
	);
	const [farmSettings, setFarmSettings] = useState(initialFarmSettings);
	const [expenseRecords, setExpenseRecords] = useState(initialExpenses || []);

	const [weather, setWeather] = useState(null);
	const {
		showAddModal,
		setShowAddModal,
		quickActionIntent,
		setQuickActionIntent,
		selectedCow,
		setSelectedCow,
		isEditing,
		setIsEditing,
		deletingCattleId,
		setDeletingCattleId, // const [deletingCattleId, setDeletingCattleId] = useState(null);
		selectedBuildingId,
		setSelectedBuildingId,
		selectedPenId,
		setSelectedPenId,
		showNotifications,
		setShowNotifications,
	} = useDashboardModals();
	const [allCattleRegistry, setAllCattleRegistry] = useState(null);
	const [allSalesLedger, setAllSalesLedger] = useState(null);
	const [isAllCattleLoading, setIsAllCattleLoading] = useState(false);
	const [isAllSalesLoading, setIsAllSalesLoading] = useState(false);
	const [allCattleLoadError, setAllCattleLoadError] = useState("");
	const [allSalesLoadError, setAllSalesLoadError] = useState("");
	const summaryRefreshRequestRef = useRef(0);
	const dashboardMountedRef = useRef(false);
	const fullCattleLoadRef = useRef(null);
	const fullSalesLoadRef = useRef(null);
	const movingCattleIdRef = useRef(null);
	const {
		items: pagedCattleItems,
		setItems: setPagedCattleItems,
		...cattlePagination
	} = useCattlePagination({
		initialItems: initialCattlePage?.items ?? [],
		initialPageInfo: initialCattlePage?.pageInfo ?? null,
	});
	const {
		items: pagedSalesItems,
		setItems: setPagedSalesItems,
		...salesPagination
	} = useSalesPagination({
		initialItems: initialSalesPage?.items ?? [],
		initialPageInfo: initialSalesPage?.pageInfo ?? null,
	});

	// Full registries remain optional and are loaded only when a view truly needs them.
	const cattleList = useMemo(
		() => normalizeDashboardCattleList(allCattleRegistry ?? pagedCattleItems),
		[allCattleRegistry, pagedCattleItems],
	);
	const saleRecords = allSalesLedger ?? pagedSalesItems;
	const safeBuildings = useMemo(
		() => normalizeDashboardBuildings(buildings),
		[buildings],
	);

	// Memoize: 발정/분만 알림은 cattleList 변경 시에만 재계산
	useEffect(() => {
		dashboardMountedRef.current = true;

		return () => {
			dashboardMountedRef.current = false;
		};
	}, []);

	const readJsonSafely = useCallback(async (response) => {
		try {
			return await response.json();
		} catch {
			return null;
		}
	}, []);

	// Helper to refresh summary from API (after mutations)
	const refreshSummary = useCallback(async () => {
		const requestId = summaryRefreshRequestRef.current + 1;
		summaryRefreshRequestRef.current = requestId;

		try {
			const res = await fetchWithTimeout(
				"/api/dashboard/summary?fresh=1",
				{ cache: "no-store" },
				{
					timeoutMs: 5000,
					errorMessage: "대시보드 요약 갱신에 시간이 오래 걸리고 있습니다.",
				},
			);
			const json = await readJsonSafely(res);
			if (!res.ok || !json?.success || !json?.data) {
				return false;
			}

			if (
				dashboardMountedRef.current &&
				summaryRefreshRequestRef.current === requestId
			) {
				setSummary(json.data);
				if (json.meta) {
					setSummaryMeta(json.meta);
				}
			}

			return true;
		} catch (err) {
			console.error("대시보드 요약 갱신 실패:", err);
			return false;
		}
	}, [readJsonSafely]);

	const refreshNotifications = useCallback(async () => {
		try {
			const nextNotifications = await getNotifications();
			if (dashboardMountedRef.current) {
				setNotifications(normalizeDashboardNotifications(nextNotifications));
			}
		} catch (error) {
			console.error("알림 갱신 실패:", error);
		}
	}, []);

	const showSuccess = (title, description = "") => {
		notify({ title, description, variant: "success" });
	};

	const showWarning = (title, description = "") => {
		notify({ title, description, variant: "warning" });
	};

	const showError = (title, description = "") => {
		notify({ title, description, variant: "error" });
	};

	const unexpectedActionErrorDescription =
		"요청 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";

	const sortByName = (items) =>
		[...items].sort((left, right) => left.name.localeCompare(right.name));
	const sortInventoryItems = (items) =>
		[...items].sort(
			(left, right) =>
				(left.category || "").localeCompare(right.category || "") ||
				left.name.localeCompare(right.name),
		);
	const sortByDateAsc = useCallback(
		(items, key) =>
			[...items].sort((left, right) => {
				const leftTime = getSortableDateTime(left[key]);
				const rightTime = getSortableDateTime(right[key]);
				if (leftTime === null && rightTime === null) return 0;
				if (leftTime === null) return 1;
				if (rightTime === null) return -1;
				return leftTime - rightTime;
			}),
		[],
	);
	const sortByDateDesc = useCallback(
		(items, key) =>
			[...items].sort((left, right) => {
				const leftTime = getSortableDateTime(left[key]);
				const rightTime = getSortableDateTime(right[key]);
				if (leftTime === null && rightTime === null) return 0;
				if (leftTime === null) return 1;
				if (rightTime === null) return -1;
				return rightTime - leftTime;
			}),
		[],
	);
	const refreshDashboardReadModels = useCallback(async () => {
		await Promise.allSettled([refreshSummary(), refreshNotifications()]);
	}, [refreshNotifications, refreshSummary]);

	const fetchDashboardItems = useCallback(
		async (pathname) => {
			const items = [];
			let nextCursor = null;
			let hasMore = true;
			let pageCount = 0;
			const seenCursors = new Set();

			while (hasMore) {
				const params = new URLSearchParams();
				params.set("limit", String(DASHBOARD_PAGE_LIMIT));
				if (nextCursor) {
					params.set("cursor", nextCursor);
				}

				const res = await fetchWithTimeout(
					`${pathname}?${params.toString()}`,
					{ cache: "no-store" },
					{
						timeoutMs: 10000,
						errorMessage: `대시보드 정보를 불러오는 데 시간이 오래 걸리고 있습니다. (${pathname})`,
					},
				);
				const json = await readJsonSafely(res);
				if (!res.ok || !json?.success || !json?.data) {
					throw new Error(
						json?.message ||
							`대시보드 정보를 불러오지 못했습니다. (${pathname})`,
					);
				}

				items.push(...normalizeDashboardItems(json.data.items));
				pageCount += 1;

				const nextPageState = getNextDashboardPaginationState({
					currentCursor: nextCursor,
					receivedPageInfo: json.data.pageInfo,
					seenCursors,
					pageCount,
					source: pathname,
				});

				hasMore = nextPageState.hasMore;
				nextCursor = nextPageState.nextCursor;
				if (nextCursor) {
					seenCursors.add(nextCursor);
				}
			}

			return items;
		},
		[readJsonSafely],
	);

	const ensureAllCattleLoaded = useCallback(
		async (options = {}) => {
			const { silent = false } = normalizeFullListLoadOptions(options);

			if (Array.isArray(allCattleRegistry)) {
				return allCattleRegistry;
			}

			if (fullCattleLoadRef.current) {
				return fullCattleLoadRef.current;
			}

			setIsAllCattleLoading(true);
			setAllCattleLoadError("");
			const promise = fetchDashboardItems("/api/dashboard/cattle")
				.then((items) => {
					const normalizedItems = normalizeDashboardCattleList(items);
					if (dashboardMountedRef.current) {
						setAllCattleRegistry(normalizedItems);
					}
					return normalizedItems;
				})
				.catch((error) => {
					if (dashboardMountedRef.current) {
						setAllCattleLoadError(FULL_CATTLE_LOAD_ERROR_MESSAGE);
					}
					if (!silent) {
						console.error("전체 개체 목록 로딩 실패:", error);
					}
					throw error;
				})
				.finally(() => {
					if (dashboardMountedRef.current) {
						setIsAllCattleLoading(false);
					}
					fullCattleLoadRef.current = null;
				});

			fullCattleLoadRef.current = promise;
			return promise;
		},
		[allCattleRegistry, fetchDashboardItems],
	);

	const ensureAllSalesLoaded = useCallback(
		async (options = {}) => {
			const { silent = false } = normalizeFullListLoadOptions(options);

			if (Array.isArray(allSalesLedger)) {
				return allSalesLedger;
			}

			if (fullSalesLoadRef.current) {
				return fullSalesLoadRef.current;
			}

			setIsAllSalesLoading(true);
			setAllSalesLoadError("");
			const promise = fetchDashboardItems("/api/dashboard/sales")
				.then((items) => {
					if (dashboardMountedRef.current) {
						setAllSalesLedger(items);
					}
					return items;
				})
				.catch((error) => {
					if (dashboardMountedRef.current) {
						setAllSalesLoadError(FULL_SALES_LOAD_ERROR_MESSAGE);
					}
					if (!silent) {
						console.error("전체 판매 기록 로딩 실패:", error);
					}
					throw error;
				})
				.finally(() => {
					if (dashboardMountedRef.current) {
						setIsAllSalesLoading(false);
					}
					fullSalesLoadRef.current = null;
				});

			fullSalesLoadRef.current = promise;
			return promise;
		},
		[allSalesLedger, fetchDashboardItems],
	);

	const prependCattleRecord = useCallback(
		(record) => {
			setPagedCattleItems((prev) => [
				record,
				...prev.filter((item) => item.id !== record.id),
			]);
			setAllCattleRegistry((prev) =>
				Array.isArray(prev)
					? [record, ...prev.filter((item) => item.id !== record.id)]
					: prev,
			);
		},
		[setPagedCattleItems],
	);

	const replaceCattleRecord = useCallback(
		(record) => {
			setPagedCattleItems((prev) =>
				prev.map((item) => (item.id === record.id ? record : item)),
			);
			setAllCattleRegistry((prev) =>
				Array.isArray(prev)
					? prev.map((item) => (item.id === record.id ? record : item))
					: prev,
			);
		},
		[setPagedCattleItems],
	);

	const removeCattleRecord = useCallback(
		(recordId) => {
			setPagedCattleItems((prev) =>
				prev.filter((item) => item.id !== recordId),
			);
			setAllCattleRegistry((prev) =>
				Array.isArray(prev)
					? prev.filter((item) => item.id !== recordId)
					: prev,
			);
		},
		[setPagedCattleItems],
	);

	const upsertCalvingRecords = useCallback(
		(motherRecord, calfRecord) => {
			setPagedCattleItems((prev) => [
				calfRecord,
				...prev.map((item) =>
					item.id === motherRecord.id ? motherRecord : item,
				),
			]);
			setAllCattleRegistry((prev) =>
				Array.isArray(prev)
					? [
							calfRecord,
							...prev.map((item) =>
								item.id === motherRecord.id ? motherRecord : item,
							),
						]
					: prev,
			);
		},
		[setPagedCattleItems],
	);

	const prependSaleRecord = useCallback(
		(record) => {
			setPagedSalesItems((prev) =>
				sortByDateDesc(
					[record, ...prev.filter((item) => item.id !== record.id)],
					"saleDate",
				),
			);
			setAllSalesLedger((prev) =>
				Array.isArray(prev)
					? sortByDateDesc(
							[record, ...prev.filter((item) => item.id !== record.id)],
							"saleDate",
						)
					: prev,
			);
		},
		[setPagedSalesItems, sortByDateDesc],
	);

	useEffect(() => {
		let cancelled = false;

		const applyWeatherDegradation = (locationName, message) => {
			if (cancelled) {
				return;
			}

			setWeather((previous) =>
				previous?.available
					? markWeatherAsStale(previous, { locationName, message })
					: buildUnavailableWeatherState({ locationName, message }),
			);
		};

		const fetchWeather = async (lat, lng) => {
			const locationName = farmSettings.location || "서울";

			try {
				const params = [
					`latitude=${lat}`,
					`longitude=${lng}`,
					"current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature",
					"daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
					"forecast_days=3",
					"timezone=Asia/Seoul",
				].join("&");
				const res = await fetchWithTimeout(
					`https://api.open-meteo.com/v1/forecast?${params}`,
					{ cache: "no-store" },
					{
						timeoutMs: 5000,
						errorMessage: WEATHER_TIMEOUT_MESSAGE,
					},
				);

				if (!res.ok) {
					applyWeatherDegradation(locationName, WEATHER_UNAVAILABLE_MESSAGE);
					return;
				}

				const { data, parseError } = await readWeatherApiResponseSafely(res);
				if (parseError) {
					applyWeatherDegradation(locationName, WEATHER_UNAVAILABLE_MESSAGE);
					return;
				}

				const normalized = normalizeWeatherPayload(data, { locationName });
				if (!normalized) {
					applyWeatherDegradation(locationName, WEATHER_UNAVAILABLE_MESSAGE);
					return;
				}

				if (!cancelled) {
					setWeather(normalized);
				}
			} catch (error) {
				if (isTimeoutError(error)) {
					applyWeatherDegradation(locationName, WEATHER_STALE_MESSAGE);
					return;
				}

				console.error("Weather fetch error", error);
				applyWeatherDegradation(locationName, WEATHER_UNAVAILABLE_MESSAGE);
			}
		};

		const fetchFallbackWeather = () => {
			if (cancelled) {
				return;
			}
			fetchWeather(35.446, 127.344);
		};

		const fetchWeatherFromCoords = (latitudeValue, longitudeValue) => {
			if (cancelled) {
				return false;
			}
			const latitude = Number(latitudeValue);
			const longitude = Number(longitudeValue);
			const isValidWeatherCoordinate =
				Number.isFinite(latitude) &&
				Number.isFinite(longitude) &&
				latitude >= -90 &&
				latitude <= 90 &&
				longitude >= -180 &&
				longitude <= 180;

			if (isValidWeatherCoordinate) {
				fetchWeather(latitude, longitude);
				return true;
			}

			return false;
		};

		const fetchWeatherFromPosition = (position) => {
			if (cancelled) {
				return;
			}
			if (fetchWeatherFromCoords(position?.coords?.latitude, position?.coords?.longitude)) {
				return;
			}

			fetchFallbackWeather();
		};

		if (
			farmSettings.latitude !== null &&
			farmSettings.latitude !== undefined &&
			farmSettings.longitude !== null &&
			farmSettings.longitude !== undefined
		) {
			if (!fetchWeatherFromCoords(farmSettings.latitude, farmSettings.longitude)) {
				fetchFallbackWeather();
			}
		} else if (typeof navigator !== "undefined" && "geolocation" in navigator) {
			try {
				navigator.geolocation.getCurrentPosition(
					fetchWeatherFromPosition,
					fetchFallbackWeather,
				);
			} catch {
				fetchFallbackWeather();
			}
		} else {
			fetchFallbackWeather();
		}

		return () => {
			cancelled = true;
		};
	}, [farmSettings.latitude, farmSettings.longitude, farmSettings.location]);

	useEffect(() => {
		if (!isOnline || queueSize() === 0) {
			return undefined;
		}

		let cancelled = false;

		void (async () => {
			try {
				const { synced, failed, deadLettered, reused } =
					await syncOfflineQueue();
				if (cancelled || reused || (synced === 0 && deadLettered === 0)) {
					return;
				}
				notify({
					title:
						failed > 0
							? "오프라인 작업을 일부 동기화했습니다."
							: "오프라인 작업 동기화가 완료되었습니다.",
					description:
						failed > 0
							? `${synced}건은 반영되었고 ${failed}건은 다시 시도해 주세요.`
							: `${synced}건이 서버에 반영되었습니다.`,
					variant: failed > 0 ? "warning" : "success",
				});
				if (synced > 0) {
					try {
						router.refresh();
					} catch (refreshError) {
						console.error("Offline queue refresh failed:", refreshError);
						notify({
							title: "동기화 후 화면 새로고침에 실패했습니다.",
							description: OFFLINE_SYNC_REFRESH_ERROR_MESSAGE,
							variant: "warning",
						});
					}
				}
			} catch (error) {
				if (cancelled) {
					return;
				}

				console.error("Offline queue sync failed:", error);
				notify({
					title: "오프라인 작업 동기화에 실패했습니다.",
					description: "잠시 후 다시 시도해 주세요.",
					variant: "warning",
				});
			}
		})();

		return () => {
			cancelled = true;
		};
	}, [isOnline, notify, router]);

	const preloadForTab = useCallback(
		(nextTab) => {
			if (nextTab === "feed" || nextTab === "calving" || nextTab === "sales") {
				void ensureAllCattleLoaded({ silent: true }).catch(() => {});
			}

			if (nextTab === "analysis") {
				void ensureAllCattleLoaded({ silent: true }).catch(() => {});
				void ensureAllSalesLoaded({ silent: true }).catch(() => {});
			}
		},
		[ensureAllCattleLoaded, ensureAllSalesLoaded],
	);

	const handleTabChange = useCallback(
		(nextTab) => {
			setActiveTab(nextTab);
			preloadForTab(nextTab);
		},
		[preloadForTab],
	);

	const handleQuickAction = useCallback(
		(action) => {
			if (action.id === "add-cattle") {
				setShowAddModal(true);
				return;
			}

			if (action.targetTab) {
				setSelectedBuildingId(null);
				setSelectedPenId(null);
				setActiveTab(action.targetTab);
				preloadForTab(action.targetTab);
				setQuickActionIntent({
					actionId: action.id,
					targetTab: action.targetTab,
					nonce: Date.now(),
				});
			}
		},
		[preloadForTab, setShowAddModal, setSelectedBuildingId, setSelectedPenId, setQuickActionIntent],
	);

	const handleSelectBuilding = useCallback(
		(buildingId) => {
			setSelectedBuildingId(buildingId);
			setSelectedPenId(null);
			void ensureAllCattleLoaded({ silent: true }).catch(() => {});
		},
		[ensureAllCattleLoaded, setSelectedBuildingId, setSelectedPenId],
	);

	const handleTestSMS = () => {
		showSuccess(
			"테스트 문자를 발송했습니다.",
			"Joolife 알림 예시가 등록된 연락처로 전송되었습니다.",
		);
	};

	const handleUpdateFarmSettings = async (data) => {
		const res = await updateFarmSettings(data);
		if (!res.success) {
			if (dashboardMountedRef.current) {
				showError("농장 정보를 저장하지 못했습니다.", res.message);
			}
			return false;
		}

		if (!dashboardMountedRef.current) {
			return true;
		}
		setFarmSettings(res.data);
		showSuccess("농장 정보가 저장되었습니다.");
		return true;
	};

	const handleAddCattle = async (newCattle, feedbackOptions = {}) => {
		const {
			successTitle = "개체가 등록되었습니다.",
			successDescription = "",
			errorTitle = "개체 등록에 실패했습니다.",
			offlineTitle = "오프라인 상태입니다.",
			offlineDescription = "등록 요청이 대기열에 저장되었습니다.",
			skipSuccessFeedback = false,
		} = feedbackOptions;

		if (!isOnline) {
			enqueue("createCattle", [newCattle]);
			prependCattleRecord(newCattle);
			setShowAddModal(false);
			showWarning(offlineTitle, offlineDescription);
			return true;
		}

		try {
			const result = await createCattle(newCattle);
			if (result.success) {
				const savedCattle = result.data || newCattle;
				if (!dashboardMountedRef.current) {
					return true;
				}
				prependCattleRecord(savedCattle);
				setShowAddModal(false);
				void refreshDashboardReadModels();
				if (!skipSuccessFeedback) {
					showSuccess(successTitle, successDescription);
				}
				return true;
			}

			if (dashboardMountedRef.current) {
				showError(errorTitle, result.message);
			}
			return false;
		} catch (error) {
			console.error("Failed to add cattle:", error);
			if (dashboardMountedRef.current) {
				showError(errorTitle, unexpectedActionErrorDescription);
			}
			return false;
		}
	};

	const handleUpdateCattle = async (updated, feedbackOptions = {}) => {
		const {
			successTitle = "개체 정보를 수정했습니다.",
			successDescription = "",
			errorTitle = "개체 수정에 실패했습니다.",
			offlineTitle = "오프라인 상태입니다.",
			offlineDescription = "수정 요청이 대기열에 저장되었습니다.",
			skipSuccessFeedback = false,
		} = feedbackOptions;

		if (!isOnline) {
			enqueue("updateCattle", [updated.id, updated]);
			replaceCattleRecord(updated);
			setIsEditing(false);
			if (selectedCow && selectedCow.id === updated.id) setSelectedCow(updated);
			showWarning(offlineTitle, offlineDescription);
			return true;
		}

		try {
			const result = await updateCattle(updated.id, updated);
			if (result.success) {
				const savedCattle = result.data || updated;
				if (!dashboardMountedRef.current) {
					return true;
				}
				replaceCattleRecord(savedCattle);
				setIsEditing(false);
				if (selectedCow && selectedCow.id === savedCattle.id)
					setSelectedCow(savedCattle);
				void refreshDashboardReadModels();
				if (!skipSuccessFeedback) {
					showSuccess(successTitle, successDescription);
				}
				return true;
			}

			if (dashboardMountedRef.current) {
				showError(errorTitle, result.message);
			}
			return false;
		} catch (error) {
			console.error("Failed to update cattle:", error);
			if (dashboardMountedRef.current) {
				showError(errorTitle, unexpectedActionErrorDescription);
			}
			return false;
		}
	};

	const handleDeleteCattle = async (id) => {
		if (deletingCattleId) {
			return false;
		}

		setDeletingCattleId(id);

		const targetCattle = cattleList.find((cow) => cow.id === id);

		try {
			const shouldDelete = await confirm({
				title: "개체를 보관 처리할까요?",
				description: targetCattle
					? `${targetCattle.name} (${targetCattle.tagNumber}) 정보가 활성 목록에서 숨겨지고 보관 기록으로 남습니다.`
					: "활성 목록에서 숨기고 보관 기록으로 남깁니다.",
				confirmLabel: "개체 보관 처리",
				cancelLabel: "개체 보관 취소",
				variant: "destructive",
			});

			if (!shouldDelete) {
				return false;
			}

			const result = await deleteCattle(id);
			if (result.success) {
				if (!dashboardMountedRef.current) {
					return true;
				}
				removeCattleRecord(id);
				setSelectedCow(null);
				void refreshDashboardReadModels();
				showSuccess("개체를 보관 처리했습니다.");
				return true;
			}

			if (dashboardMountedRef.current) {
				showError("개체 보관 처리에 실패했습니다.", result.message);
			}
			return false;
		} catch {
			if (dashboardMountedRef.current) {
				showError("개체 보관 처리 중 오류가 발생했습니다.");
			}
			return false;
		} finally {
			if (dashboardMountedRef.current) {
				setDeletingCattleId(null);
			}
		}
	};

	const handleAddItem = async (data) => {
		const res = await addInventoryItem(data);
		if (!res.success) {
			if (dashboardMountedRef.current) {
				showError("재고 항목을 추가하지 못했습니다.", res.message);
			}
			return false;
		}

		if (!dashboardMountedRef.current) {
			return true;
		}
		setInventoryList((prev) => sortInventoryItems([res.data, ...prev]));
		showSuccess("재고 항목이 추가되었습니다.");
		return true;
	};

	const handleUpdateQuantity = async (id, qty) => {
		const res = await updateInventoryQuantity(id, qty);
		if (!res.success) {
			if (dashboardMountedRef.current) {
				showError("재고 수량을 수정하지 못했습니다.", res.message);
			}
			return false;
		}

		if (!dashboardMountedRef.current) {
			return true;
		}
		setInventoryList((prev) =>
			prev.map((item) => (item.id === res.data.id ? res.data : item)),
		);
		showSuccess("재고 수량을 업데이트했습니다.");
		return true;
	};

	const handleCreateEvent = async (data) => {
		const res = await createScheduleEvent(data);
		if (!res.success) {
			if (dashboardMountedRef.current) {
				showError("일정을 등록하지 못했습니다.", res.message);
			}
			return false;
		}

		if (!dashboardMountedRef.current) {
			return true;
		}
		setScheduleEvents((prev) => sortByDateAsc([res.data, ...prev], "date"));
		showSuccess("일정을 등록했습니다.");
		return true;
	};

	const handleToggleEvent = async (id, isCompleted) => {
		const res = await toggleEventCompletion(id, isCompleted);
		if (!res.success) {
			if (dashboardMountedRef.current) {
				showError("일정 상태를 변경하지 못했습니다.", res.message);
			}
			return false;
		}

		if (!dashboardMountedRef.current) {
			return true;
		}
		setScheduleEvents((prev) =>
			prev.map((event) => (event.id === res.data.id ? res.data : event)),
		);
		showSuccess(
			isCompleted
				? "일정을 완료 처리했습니다."
				: "일정을 다시 진행 중으로 변경했습니다.",
		);
		return true;
	};

	const handleCreateSale = async (data) => {
		if (!isOnline) {
			enqueue("createSalesRecord", [data]);
			showWarning(
				"오프라인 상태입니다.",
				"판매 기록이 대기열에 저장되었습니다.",
			);
			return true;
		}

		const res = await createSalesRecord(data);
		if (!res.success) {
			if (dashboardMountedRef.current) {
				showError("판매 기록을 등록하지 못했습니다.", res.message);
			}
			return false;
		}

		if (!dashboardMountedRef.current) {
			return true;
		}
		prependSaleRecord(res.data);
		void refreshDashboardReadModels();
		showSuccess("판매 기록이 등록되었습니다.");
		return true;
	};

	const handleRecordFeed = async (data) => {
		if (!isOnline) {
			enqueue("recordFeed", [data]);
			showWarning(
				"오프라인 상태입니다.",
				"급여 기록이 대기열에 저장되었습니다.",
			);
			return true;
		}

		const res = await recordFeed(data);
		if (!res.success) {
			if (dashboardMountedRef.current) {
				showError("급여 기록을 저장하지 못했습니다.", res.message);
			}
			return false;
		}

		if (!dashboardMountedRef.current) {
			return true;
		}
		setFeedHistory((prev) =>
			sortByDateDesc([res.data, ...prev], "date").slice(0, 20),
		);
		showSuccess("급여 기록이 완료되었습니다.");
		return true;
	};

	const handleCreateBuilding = async (data) => {
		const res = await createBuilding(data);
		if (!res.success) {
			if (dashboardMountedRef.current) {
				showError("축사 정보를 추가하지 못했습니다.", res.message);
			}
			return false;
		}

		if (!dashboardMountedRef.current) {
			return true;
		}
		setBuildings((prev) => sortByName([res.data, ...prev]));
		showSuccess("축사를 추가했습니다.");
		return true;
	};

	const handleDeleteBuilding = async (id) => {
		const res = await deleteBuilding(id);
		if (!res.success) {
			if (dashboardMountedRef.current) {
				showError("축사를 삭제하지 못했습니다.", res.message);
			}
			return false;
		}

		if (!dashboardMountedRef.current) {
			return true;
		}
		setBuildings((prev) => prev.filter((building) => building.id !== id));
		if (selectedBuildingId === id) {
			setSelectedBuildingId(null);
			setSelectedPenId(null);
		}
		showSuccess("축사를 삭제했습니다.");
		return true;
	};

	const handleRecordCalving = async ({
		motherId,
		calvingDate,
		calfGender,
		calfTagNumber,
	}) => {
		const mother = cattleList.find((cow) => cow.id === motherId);

		if (!mother) {
			showError("분만 대상 개체를 찾지 못했습니다.");
			return false;
		}

		const birthDate = toStrictIsoDateOrNull(calvingDate);
		if (!birthDate) {
			showError("분만일을 확인해 주세요.");
			return false;
		}

		const updatedMother = {
			...mother,
			status: "번식우",
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
			birthDate,
			weight: 25,
			status: "송아지",
			memo: `모체 ${mother.tagNumber} (${mother.name})`,
			geneticInfo: {
				father: mother.geneticFather || "미상",
				mother: mother.tagNumber,
				grade: "-",
			},
		};

		if (!isOnline) {
			enqueue("recordCalving", [
				{ motherId, calvingDate, calfGender, calfTagNumber },
			]);
			upsertCalvingRecords(updatedMother, calfDraft);
			showWarning(
				"오프라인 상태입니다.",
				"분만 처리 요청이 대기열에 저장되었습니다.",
			);
			return true;
		}

		const res = await recordCalving({
			motherId,
			calvingDate,
			calfGender,
			calfTagNumber,
		});

		if (!res.success) {
			if (dashboardMountedRef.current) {
				showError("분만 처리를 완료하지 못했습니다.", res.message);
			}
			return false;
		}

		const savedMother = res.data?.mother || updatedMother;
		const savedCalf = res.data?.calf || calfDraft;

		if (!dashboardMountedRef.current) {
			return true;
		}
		upsertCalvingRecords(savedMother, savedCalf);
		void refreshDashboardReadModels();
		showSuccess(
			"분만 처리가 완료되었습니다.",
			`${mother.name}의 상태와 송아지 등록이 함께 반영되었습니다.`,
		);
		return true;
	};

	const handleDragDrop = async (cattleId, toBuildingId, toPenNumber) => {
		const cow = cattleList.find((item) => item.id === cattleId);
		if (!cow) return;
		if (cow.buildingId === toBuildingId && cow.penNumber === toPenNumber)
			return;
		if (movingCattleIdRef.current) return false;

		const penCattle = cattleList.filter(
			(item) =>
				item.buildingId === toBuildingId && item.penNumber === toPenNumber,
		);
		const targetBuilding = safeBuildings.find(
			(building) => building.id === toBuildingId,
		);
		const targetLabel = `${targetBuilding?.name || toBuildingId} ${toPenNumber}번 칸`;

		if (penCattle.length >= 5) {
			showWarning(
				"이 칸은 이미 가득 찼습니다.",
				"한 칸에는 최대 5두까지만 배치할 수 있습니다.",
			);
			return false;
		}

		movingCattleIdRef.current = cattleId;

		try {
			const shouldMove = await confirm({
				title: "개체를 이동할까요?",
				description: `${cow.name}을(를) ${targetLabel}(으)로 이동합니다.`,
				confirmLabel: "개체 이동",
				cancelLabel: "개체 이동 취소",
			});

			if (!dashboardMountedRef.current) {
				return false;
			}

			if (!shouldMove) {
				return false;
			}

			const updated = {
				...cow,
				buildingId: toBuildingId,
				penNumber: toPenNumber,
			};
			return handleUpdateCattle(updated, {
				successTitle: "개체를 이동했습니다.",
				successDescription: `${cow.name}을(를) ${targetLabel}(으)로 옮겼습니다.`,
				offlineTitle: "오프라인 상태입니다.",
				offlineDescription: `${cow.name} 이동 요청이 대기열에 저장되었습니다.`,
			});
		} finally {
			movingCattleIdRef.current = null;
		}
	};

	// Stats from summary (SSR-snapshot, refreshed after mutations)
	const totalHeadcount = summary?.headcount?.totalActive ?? cattleList.length;
	const monthlySalesTotal = summary?.monthlyRollup?.salesTotal ?? 0;

	// Memoize: Date 생성 + filter/reduce를 매 렌더가 아닌 데이터 변경 시에만 실행
	const fallbackMonthlySalesCount = useMemo(() => {
		const today = new Date();
		const currentMonth = today.getMonth();
		const currentYear = today.getFullYear();
		return saleRecords.filter((record) => {
			const saleDate = toValidCalendarDate(record.saleDate);
			return (
				saleDate &&
				saleDate.getMonth() === currentMonth &&
				saleDate.getFullYear() === currentYear
			);
		}).length;
	}, [saleRecords]);

	const fallbackAverageWeight = useMemo(() => {
		if (cattleList.length === 0) return 0;
		return Math.floor(
			cattleList.reduce((sum, cow) => sum + toFiniteNumber(cow.weight), 0) /
				cattleList.length,
		);
	}, [cattleList]);

	const monthlySalesCount =
		summary?.monthlyRollup?.salesCount ?? fallbackMonthlySalesCount;
	const avgWeight = summary?.headcount?.averageWeight ?? fallbackAverageWeight;
	const aiInsightSummary = useMemo(
		() => ({
			totalHeadcount,
			monthlySalesCount,
			monthlySalesTotal,
			profitabilityItems: initialProfitability?.data,
			notifications,
			weather,
		}),
		[
			initialProfitability?.data,
			monthlySalesCount,
			monthlySalesTotal,
			notifications,
			totalHeadcount,
			weather,
		],
	);
	const todayFocusItems = useMemo(
		() =>
			buildTodayFocusItems({
				notifications,
				scheduleEvents,
				inventoryList,
				feedHistory,
				monthlySalesCount,
				isOnline,
			}),
		[
			feedHistory,
			inventoryList,
			isOnline,
			monthlySalesCount,
			notifications,
			scheduleEvents,
		],
	);

	const setupProgress = useMemo(
		() =>
			buildSetupProgressItems({
				farmSettings,
				buildings: safeBuildings,
				cattleList,
				inventoryList,
				scheduleEvents,
			}),
		[safeBuildings, cattleList, farmSettings, inventoryList, scheduleEvents],
	);

	const renderContent = () => {
		const needsCompleteCattleData =
			activeTab === "feed" ||
			activeTab === "calving" ||
			activeTab === "sales" ||
			activeTab === "analysis" ||
			selectedBuildingId !== null;
		const cattleLoadMoreLabel = cattlePagination.isLoading
			? "개체 목록을 불러오는 중입니다"
			: "이전 개체 더 보기";

		if (
			needsCompleteCattleData &&
			!Array.isArray(allCattleRegistry) &&
			allCattleLoadError &&
			!isAllCattleLoading
		) {
			return (
				<Card className="animate-fadeIn">
					<CardContent className="py-12 text-center text-sm text-muted-foreground">
						<div className="mx-auto flex max-w-sm flex-col items-center gap-3">
							<p className="m-0 font-semibold text-[color:var(--color-danger)]">
								{allCattleLoadError}
							</p>
							<PremiumButton
								type="button"
								variant="secondary"
								size="sm"
								onClick={() => {
									void ensureAllCattleLoaded({ silent: false }).catch(() => {});
								}}
								aria-label="전체 개체 목록 다시 불러오기"
								title="전체 개체 목록 다시 불러오기"
							>
								다시 불러오기
							</PremiumButton>
						</div>
					</CardContent>
				</Card>
			);
		}

		if (needsCompleteCattleData && !Array.isArray(allCattleRegistry)) {
			return (
				<Card className="animate-fadeIn">
					<CardContent
						className="py-12 text-center text-sm text-muted-foreground"
						role="status"
						aria-live="polite"
						aria-atomic="true"
						aria-busy={isAllCattleLoading}
					>
						{isAllCattleLoading
							? "개체 목록을 불러오는 중입니다..."
							: "개체 목록을 준비 중입니다..."}
					</CardContent>
				</Card>
			);
		}

		if (
			activeTab === "analysis" &&
			!Array.isArray(allSalesLedger) &&
			allSalesLoadError &&
			!isAllSalesLoading
		) {
			return (
				<Card className="animate-fadeIn">
					<CardContent className="py-12 text-center text-sm text-muted-foreground">
						<div className="mx-auto flex max-w-sm flex-col items-center gap-3">
							<p className="m-0 font-semibold text-[color:var(--color-danger)]">
								{allSalesLoadError}
							</p>
							<PremiumButton
								type="button"
								variant="secondary"
								size="sm"
								onClick={() => {
									void ensureAllSalesLoaded({ silent: false }).catch(() => {});
								}}
								aria-label="판매 기록 다시 불러오기"
								title="판매 기록 다시 불러오기"
							>
								다시 불러오기
							</PremiumButton>
						</div>
					</CardContent>
				</Card>
			);
		}

		if (activeTab === "analysis" && !Array.isArray(allSalesLedger)) {
			return (
				<Card className="animate-fadeIn">
					<CardContent
						className="py-12 text-center text-sm text-muted-foreground"
						role="status"
						aria-live="polite"
						aria-atomic="true"
						aria-busy={isAllSalesLoading}
					>
						{isAllSalesLoading
							? "판매 기록을 불러오는 중입니다..."
							: "판매 기록을 준비 중입니다..."}
					</CardContent>
				</Card>
			);
		}

		if (activeTab === "feed") {
			return (
				<FeedTab
					cattle={cattleList}
					feedStandards={feedStandards}
					feedHistory={feedHistory}
					onRecordFeed={handleRecordFeed}
					buildings={safeBuildings}
				/>
			);
		}
		if (activeTab === "calving")
			return (
				<CalvingTab
					cattle={cattleList}
					buildings={safeBuildings}
					onRecordCalving={handleRecordCalving}
				/>
			);
		if (activeTab === "sales") {
			return (
				<SalesTab
					saleRecords={saleRecords}
					cattleList={cattleList}
					onCreateSale={handleCreateSale}
					expenseRecords={expenseRecords}
					initialMarketPrice={initialMarketPrice}
					salesPagination={
						Array.isArray(allSalesLedger) ? null : salesPagination
					}
					quickActionIntent={quickActionIntent}
				/>
			);
		}
		if (activeTab === "inventory") {
			return (
				<InventoryTab
					inventory={inventoryList}
					onAddItem={handleAddItem}
					onUpdateQuantity={handleUpdateQuantity}
					quickActionIntent={quickActionIntent}
				/>
			);
		}
		if (activeTab === "schedule") {
			return (
				<ScheduleTab
					events={scheduleEvents}
					onCreateEvent={handleCreateEvent}
					onToggleEvent={handleToggleEvent}
					quickActionIntent={quickActionIntent}
				/>
			);
		}
		if (activeTab === "analysis") {
			return (
				<AnalysisTab
					saleRecords={saleRecords}
					feedHistory={feedHistory}
					cattleList={cattleList}
					expenseRecords={expenseRecords}
				/>
			);
		}
		if (activeTab === "settings") {
			return (
				<SettingsTab
					key={
						quickActionIntent?.targetTab === "settings"
							? quickActionIntent.nonce
							: "settings"
					}
					buildings={safeBuildings}
					onCreateBuilding={handleCreateBuilding}
					onDeleteBuilding={handleDeleteBuilding}
					farmSettings={farmSettings}
					onUpdateFarmSettings={handleUpdateFarmSettings}
					theme={theme}
					onToggleTheme={toggleTheme}
					widgetRegistry={WIDGET_REGISTRY}
					widgetVisible={widgetSettings.visible}
					onToggleWidget={widgetSettings.toggle}
					quickActionIntent={quickActionIntent}
				/>
			);
		}

		return (
			<>
				{/* Header — generous breathing room for visual hierarchy */}
				<div className="animate-fadeInDown flex justify-between items-start mb-7 pt-2 pb-1">
					<div>
						<h1 className="text-[26px] font-extrabold text-foreground tracking-[-0.02em] mb-1.5 leading-tight flex items-center gap-2">
							{farmSettings.name || "Joolife 한우 농장"}
							<span className="text-[10px] uppercase tracking-wider font-extrabold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
								DEMO
							</span>
						</h1>
						<p className="text-[13px] text-muted-foreground leading-relaxed">
							오늘도 힘찬 하루 되세요! 🐮
						</p>
					</div>
					<div className="flex gap-2.5 pt-0.5">
						<PremiumButton
							variant="outline"
							onClick={() => {
								playTactileClick();
								setIsFieldMode(true);
							}}
							aria-label="현장 스마트 모드 활성화"
							title="현장 스마트 모드 활성화"
							className="relative shadow-[var(--shadow-sm)] border-amber-500/30 text-amber-600 dark:text-amber-400 font-bold hover:bg-amber-500/10 hover:border-amber-400 flex items-center gap-1.5 px-3"
						>
							<span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
							현장 모드 🚜
						</PremiumButton>
						<ExcelExportButton
							cattleList={cattleList}
							resolveCattleList={ensureAllCattleLoaded}
						/>
						<PremiumButton
							variant="outline"
							size="icon"
							onClick={() => setShowNotifications(true)}
							aria-haspopup="dialog"
							aria-expanded={showNotifications}
							aria-controls={NOTIFICATION_MODAL_ID}
							aria-label="알림 센터 열기"
							title="알림 센터 열기"
							className="relative shadow-[var(--shadow-sm)]"
						>
							<Bell className="h-5 w-5" aria-hidden="true" />
							{notifications.some(
								(notification) => notification.level === "critical",
							) && (
								<span
									className="absolute top-1.5 right-1.5 h-2.5 w-2.5 rounded-full bg-destructive border-2 border-background animate-pulse shadow-[0_0_10px_hsl(var(--destructive))]"
									aria-hidden="true"
								/>
							)}
						</PremiumButton>
						<PremiumButton
							size="icon"
							onClick={() => setShowAddModal(true)}
							aria-label="개체 등록 열기"
							title="개체 등록 열기"
							className="shadow-[var(--shadow-button-primary)]"
						>
							<Plus className="h-5 w-5" aria-hidden="true" />
						</PremiumButton>
					</div>
				</div>

				{showNotifications && (
					<NotificationModal
						id={NOTIFICATION_MODAL_ID}
						notifications={notifications}
						onClose={() => setShowNotifications(false)}
						onTestSMS={handleTestSMS}
					/>
				)}

				<TodayFocusPanel
					items={todayFocusItems}
					onOpenNotifications={() => setShowNotifications(true)}
					onNavigate={handleTabChange}
				/>

				<QuickActionPanel
					actions={QUICK_ACTIONS}
					onAction={handleQuickAction}
				/>

				<SetupProgressPanel
					progress={setupProgress}
					onNavigate={handleTabChange}
					onAction={handleQuickAction}
				/>

				{widgetSettings.visible.weather && <WeatherWidget weather={weather} />}
				{widgetSettings.visible.market && (
					<MarketPriceWidget initialData={initialMarketPrice} />
				)}
				{widgetSettings.visible.notification && (
					<NotificationWidget notifications={notifications} />
				)}
				{widgetSettings.visible.financial && (
					<FinancialChartWidget
						saleRecords={saleRecords}
						expenseRecords={expenseRecords}
						seriesData={summary?.financialSeries}
					/>
				)}
				{widgetSettings.visible.profitability && (
					<ProfitabilityWidget
						data={initialProfitability?.data}
						error={initialProfitability?.error}
						isLoading={false}
						meta={initialProfitability?.meta ?? null}
					/>
				)}
				{widgetSettings.visible.aiInsight && (
					<AIInsightWidget summary={aiInsightSummary} />
				)}
				{widgetSettings.visible.estrus && (
					<EstrusAlertBanner
						notifications={notifications}
						buildings={safeBuildings}
					/>
				)}
				{widgetSettings.visible.calving && (
					<CalvingAlertBanner
						notifications={notifications}
						buildings={safeBuildings}
					/>
				)}

				{widgetSettings.visible.stats && (
					<div
						style={{
							display: "flex",
							gap: "14px",
							overflowX: "auto",
							paddingBottom: "14px",
							marginBottom: "28px",
							scrollSnapType: "x mandatory",
							scrollPadding: "0 4px",
							WebkitOverflowScrolling: "touch",
						}}
					>
						<PremiumInfoCard
							title="총 사육두수"
							value={`${totalHeadcount}두`}
						/>
						<PremiumInfoCard
							title="이번 달 출하"
							value={`${monthlySalesCount}두`}
							change={
								monthlySalesTotal > 0
									? `${formatMoney(monthlySalesTotal / 10000)}만`
									: null
							}
							changeType="positive"
						/>
						<PremiumInfoCard title="평균 체중" value={`${avgWeight}kg`} />
					</div>
				)}

				{!selectedBuildingId ? (
					<div className="animate-fadeInUp" style={{ animationDelay: "200ms" }}>
						<div className="section-header">
							<span className="section-header-icon" aria-hidden="true">
								🏠
							</span>
							<h2 className="section-header-title">축사 현황</h2>
						</div>
						{safeBuildings.length === 0 ? (
							<button
								type="button"
								className="empty-state-cta animate-fadeInUp block w-full"
								style={{ animationDelay: "250ms" }}
								onClick={() => handleTabChange("settings")}
								aria-label="설정에서 첫 번째 축사를 추가해 주세요"
								title="설정에서 첫 번째 축사를 추가해 주세요"
							>
								<span className="cta-icon" aria-hidden="true">
									🏠
								</span>
								<div className="cta-title">첫 번째 축사를 추가해 주세요</div>
								<div className="cta-desc">
									축사를 등록하면 칸별 두수 관리, 발정·분만 알림을 시작할 수
									있습니다.
								</div>
							</button>
						) : (
							<div className="grid gap-3">
								{safeBuildings.map((building) => {
									const index = building._displayIndex;
									const buildingHeadcount =
										summary?.buildingOccupancy?.find(
											(b) => b.buildingId === building.id,
										)?.headcount ?? 0;
									const buildingCardLabel = `${building.name} 축사 상세 보기, 총 ${building.penCount}칸, ${buildingHeadcount}두 배치됨`;
									return (
										<button
											key={building.id}
											type="button"
											onClick={() => handleSelectBuilding(building.id)}
											aria-label={buildingCardLabel}
											title={buildingCardLabel}
											className="clay-surface rounded-[28px] text-card-foreground backdrop-blur-md transition-[box-shadow,border-color,transform] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] animate-fadeInUp cursor-pointer hover:-translate-y-1 hover:shadow-[var(--shadow-md)] group/building w-full text-left"
											style={{ animationDelay: `${250 + index * 50}ms` }}
										>
											<CardContent className="flex justify-between items-center p-5">
												<div>
													<div className="font-bold text-[15px] mb-1.5 tracking-[-0.01em]">
														{building.name}
													</div>
													<p className="text-sm text-muted-foreground leading-relaxed">
														{building.description ||
															`총 ${building.penCount}칸`}{" "}
														·{" "}
														<strong className="text-foreground">
															{buildingHeadcount}두
														</strong>
													</p>
												</div>
												<span className="text-xl text-muted-foreground transition-[transform,color,opacity] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] opacity-55 group-hover/building:translate-x-1 group-hover/building:text-[var(--color-primary-custom)] group-hover/building:opacity-100">
													›
												</span>
											</CardContent>
										</button>
									);
								})}
							</div>
						)}
					</div>
				) : !selectedPenId ? (
					<div className="animate-fadeIn">
						<div className="flex items-center gap-3 mb-4">
							<PremiumButton
								variant="ghost"
								size="icon"
								onClick={() => setSelectedBuildingId(null)}
								aria-label="축사 목록으로 돌아가기"
								title="축사 목록으로 돌아가기"
								className="h-9 w-9"
							>
								<ArrowLeft className="h-5 w-5" aria-hidden="true" />
							</PremiumButton>
							<h2 className="text-lg font-extrabold text-foreground">
								{
									safeBuildings.find(
										(building) => building.id === selectedBuildingId,
									)?.name
								}
							</h2>
						</div>
						<div
							style={{
								display: "grid",
								gridTemplateColumns: "repeat(3,1fr)",
								gap: "12px",
							}}
						>
							{[
								...Array(
									safeBuildings.find(
										(building) => building.id === selectedBuildingId,
									)?.penCount || 32,
								),
							].map((_, index) => {
								const penNum = index + 1;
								const penCattle = cattleList.filter(
									(cow) =>
										cow.buildingId === selectedBuildingId &&
										cow.penNumber === penNum,
								);
								return (
									<PenCard
										key={penNum}
										penNumber={penNum}
										cattle={penCattle}
										buildingId={selectedBuildingId}
										onSelect={(_buildingId, penId) => setSelectedPenId(penId)}
										onDrop={handleDragDrop}
										delay={index * 20}
									/>
								);
							})}
						</div>
					</div>
				) : (
					<div className="animate-fadeIn">
						<div className="flex items-center gap-3 mb-4">
							<PremiumButton
								variant="ghost"
								size="icon"
								onClick={() => setSelectedPenId(null)}
								aria-label="칸 목록으로 돌아가기"
								title="칸 목록으로 돌아가기"
								className="h-9 w-9"
							>
								<ArrowLeft className="h-5 w-5" aria-hidden="true" />
							</PremiumButton>
							<h2 className="text-lg font-extrabold text-foreground">
								{selectedPenId}번 칸 상세
							</h2>
						</div>
						{/* filter 1회만 실행 후 분기 */}
						<PenCattleList
							cattleList={cattleList}
							buildingId={selectedBuildingId}
							penId={selectedPenId}
							onSelect={setSelectedCow}
						/>
					</div>
				)}

				{!allCattleRegistry && cattlePagination.hasMore ? (
					<div className="mt-5 flex flex-col items-center gap-2">
						<button
							type="button"
							onClick={() => cattlePagination.loadMore()}
							disabled={cattlePagination.isLoading}
							aria-busy={cattlePagination.isLoading}
							aria-label={cattleLoadMoreLabel}
							title={cattleLoadMoreLabel}
							className="clay-pressable w-full rounded-[18px] px-4 py-3 text-sm font-semibold text-[color:var(--color-text-secondary)]"
						>
							{cattlePagination.isLoading
								? "개체 목록을 불러오는 중입니다..."
								: "이전 개체 더 보기"}
						</button>
						{cattlePagination.loadError ? (
							<p
								className="m-0 text-center text-xs font-semibold text-[color:var(--color-danger)]"
								role="status"
								aria-live="polite"
								aria-atomic="true"
							>
								{cattlePagination.loadError}
							</p>
						) : null}
					</div>
				) : null}

				<AIChatWidget />
			</>
		);
	};

	return (
		<div className="dashboard-container">
			{isFieldMode ? (
				<FieldModeView
					cattleList={cattleList}
					buildings={safeBuildings}
					ensureAllCattleLoaded={ensureAllCattleLoaded}
					onSelect={setSelectedCow}
					onCloseFieldMode={() => setIsFieldMode(false)}
				/>
			) : (
				<div className="max-w-[600px] mx-auto p-4 relative">
					{!isOnline && (
						<div
							className="mb-3 flex items-center gap-2.5 rounded-[20px] px-4 py-3 text-sm font-bold text-white shadow-[var(--shadow-md)]"
							style={{
								background:
									"linear-gradient(145deg, color-mix(in srgb, var(--color-warning) 72%, white 28%), var(--color-warning))",
								border: "1px solid rgba(255,255,255,0.2)",
							}}
						>
							<WifiOff className="h-5 w-5 flex-shrink-0" />
							오프라인 모드 — 작업은 저장되어 연결 복구 시 자동 동기화됩니다
							{queueSize() > 0 && (
								<Badge
									variant="secondary"
									className="ml-auto border-white/15 bg-white/25 text-white text-xs shadow-none"
								>
									{queueSize()}건 대기
								</Badge>
							)}
						</div>
					)}
					{renderContent()}
				</div>
			)}
			{!isFieldMode && (
				<TabBar activeTab={activeTab} onTabChange={handleTabChange} />
			)}

			{showAddModal && (
				<CattleForm
					buildings={safeBuildings}
					onSubmit={handleAddCattle}
					onCancel={() => setShowAddModal(false)}
				/>
			)}

			{isEditing && selectedCow && (
				<CattleForm
					cattle={selectedCow}
					buildings={safeBuildings}
					onSubmit={handleUpdateCattle}
					onCancel={() => setIsEditing(false)}
				/>
			)}

			{selectedCow && !isEditing && (
				<CattleDetailModal
					cattle={selectedCow}
					buildings={safeBuildings}
					isDeleting={deletingCattleId === selectedCow.id}
					onClose={() => setSelectedCow(null)}
					onEdit={() => setIsEditing(true)}
					onDelete={() => handleDeleteCattle(selectedCow.id)}
					onUpdate={handleUpdateCattle}
				/>
			)}

			{!isFieldMode && (
				<footer className="footer-glass mt-16 mx-2 px-6 pt-8 pb-6 text-center text-xs text-muted-foreground leading-relaxed">
					<div className="font-bold text-sm text-primary mb-4 flex items-center justify-center gap-2">
						🐄 Joolife (쥬라프)
					</div>
					<div className="flex justify-center gap-6 flex-wrap mb-5">
						<a
							href="/terms?returnTo=dashboard"
							aria-label="Joolife 이용약관 보기"
							title="Joolife 이용약관 보기"
							className="no-underline text-muted-foreground hover:text-foreground transition-[color,transform] duration-200 py-1.5 px-1 hover:-translate-y-px"
						>
							이용약관
						</a>
						<span className="text-muted-foreground/30 select-none">·</span>
						<a
							href="/privacy?returnTo=dashboard"
							aria-label="Joolife 개인정보처리방침 보기"
							title="Joolife 개인정보처리방침 보기"
							className="no-underline text-muted-foreground hover:text-foreground transition-[color,transform] duration-200 py-1.5 px-1 hover:-translate-y-px"
						>
							개인정보처리방침
						</a>
						<span className="text-muted-foreground/30 select-none">·</span>
						<a
							href="/subscription"
							aria-label="Joolife 프리미엄 구독 화면 열기"
							title="Joolife 프리미엄 구독 화면 열기"
							className="no-underline text-primary font-semibold hover:text-foreground transition-[color,transform] duration-200 py-1.5 px-1 hover:-translate-y-px"
						>
							⭐ 프리미엄
						</a>
					</div>
					<Separator className="mb-4 opacity-30" />
					<div className="text-[10px] text-muted-foreground/40 leading-loose space-y-0.5">
						<p>운영 문의: joolife@joolife.io.kr</p>
						<p className="mt-2 text-muted-foreground/30">
							&copy; 2026 Joolife. 모든 권리 보유.
						</p>
					</div>
				</footer>
			)}
		</div>
	);
}

function TodayFocusPanel(options = {}) {
	const { items, onOpenNotifications, onNavigate } = normalizeDashboardHelperOptions(options);
	const visibleItems = normalizeDashboardHelperItems(items);
	const handleNavigate = typeof onNavigate === "function" ? onNavigate : () => {};
	const handleOpenNotifications =
		typeof onOpenNotifications === "function" ? onOpenNotifications : () => {};

	if (!visibleItems.length) {
		return null;
	}

	const handleClick = (item) => {
		if (item.type === "alert") {
			handleOpenNotifications();
			return;
		}

		if (item.targetTab) {
			handleNavigate(item.targetTab);
		}
	};

	return (
		<section
			className="today-focus-panel animate-fadeInUp"
			aria-labelledby="today-focus-title"
		>
			<div className="today-focus-header">
				<div>
					<div className="clay-page-eyebrow">오늘 요약</div>
					<h2 id="today-focus-title" className="today-focus-title">
						오늘 바로 볼 일
					</h2>
				</div>
				<div className="today-focus-count">
					{visibleItems.length}개
				</div>
			</div>

			<div className="today-focus-grid">
				{visibleItems.map((item) => {
					const Icon = FOCUS_ICON_BY_TYPE[item.type] || ClipboardList;
					const focusItemLabel = `${item.title} - ${item.detail} (${item.meta})`;

					return (
						<button
							key={item.id}
							type="button"
							className={`today-focus-item today-focus-item-${item.tone}`}
							onClick={() => handleClick(item)}
							aria-label={focusItemLabel}
							title={focusItemLabel}
						>
							<span className="today-focus-icon" aria-hidden="true">
								<Icon size={18} strokeWidth={2.2} />
							</span>
							<span className="today-focus-copy">
								<span className="today-focus-item-title">{item.title}</span>
								<span className="today-focus-item-detail">{item.detail}</span>
							</span>
							<span className="today-focus-meta">{item.meta}</span>
						</button>
					);
				})}
			</div>
		</section>
	);
}

/** 칸 상세 뷰 — filter 1회로 렌더/빈칸 분기 처리 */
function QuickActionPanel(options = {}) {
	const { actions, onAction } = normalizeDashboardHelperOptions(options);
	const visibleActions = normalizeDashboardHelperItems(actions);
	const handleAction = typeof onAction === "function" ? onAction : () => {};

	return (
		<section
			className="quick-action-panel animate-fadeInUp"
			aria-labelledby="quick-action-title"
		>
			<div className="quick-action-header">
				<div>
					<div className="clay-page-eyebrow">빠른 기록</div>
					<h2 id="quick-action-title" className="quick-action-title">
						자주 쓰는 기록
					</h2>
				</div>
				<span className="quick-action-hint">1탭 시작</span>
			</div>

			<div className="quick-action-grid">
				{visibleActions.map((action) => {
					const Icon = action.icon;
					const quickActionLabel = `${action.label} - ${action.detail}`;

					return (
						<button
							key={action.id}
							type="button"
							className={`quick-action-button quick-action-${action.tone}`}
							onClick={() => handleAction(action)}
							aria-label={quickActionLabel}
							title={quickActionLabel}
						>
							<span className="quick-action-icon" aria-hidden="true">
								<Icon size={18} strokeWidth={2.2} />
							</span>
							<span className="quick-action-copy">
								<span className="quick-action-label">{action.label}</span>
								<span className="quick-action-detail">{action.detail}</span>
							</span>
						</button>
					);
				})}
			</div>
		</section>
	);
}

const SETUP_ICON_BY_ID = {
	"farm-profile": Settings,
	buildings: Home,
	cattle: ClipboardPlus,
	inventory: PackageCheck,
	schedule: CalendarDays,
};

function SetupProgressPanel(options = {}) {
	const { progress, onNavigate, onAction } = normalizeDashboardHelperOptions(options);
	const safeProgress = {
		percent: progress && typeof progress === "object" ? progress.percent : 0,
		completed: progress && typeof progress === "object" ? progress.completed : 0,
		total: progress && typeof progress === "object" ? progress.total : 0,
		items: progress && typeof progress === "object" ? progress.items : [],
	};
	const progressItems = normalizeDashboardHelperItems(safeProgress.items);
	const progressPercent = Math.min(
		100,
		Math.max(0, toFiniteNumber(safeProgress.percent)),
	);
	const progressCompleted = Math.max(
		0,
		Math.floor(toFiniteNumber(safeProgress.completed, progressItems.length)),
	);
	const progressTotal = Math.max(
		0,
		Math.floor(toFiniteNumber(safeProgress.total, progressItems.length)),
	);
	const handleNavigate =
		typeof onNavigate === "function" ? onNavigate : () => {};
	const handleAction = typeof onAction === "function" ? onAction : () => {};

	if (!progressItems.length || progressPercent === 100) {
		return null;
	}

	const handleItemClick = (item) => {
		if (item.actionId) {
			handleAction({ id: item.actionId, targetTab: item.targetTab });
			return;
		}

		if (item.targetTab) {
			handleNavigate(item.targetTab);
		}
	};
	const setupProgressLabel = `운영 준비도 ${progressPercent}% (${progressCompleted}/${progressTotal})`;
	const setupProgressTrackLabel = "운영 준비도 진행률";

	return (
		<section
			className="setup-progress-panel animate-fadeInUp"
			aria-labelledby="setup-progress-title"
		>
			<div className="setup-progress-topline">
				<div>
					<div className="clay-page-eyebrow">운영 준비</div>
					<h2 id="setup-progress-title" className="setup-progress-title">
						운영 준비도
					</h2>
				</div>
				<div
					className="setup-progress-score"
					aria-label={setupProgressLabel}
					title={setupProgressLabel}
				>
					{progressCompleted}/{progressTotal}
				</div>
			</div>

			<div
				className="setup-progress-track"
				role="progressbar"
				aria-label={setupProgressTrackLabel}
				aria-valuemin={0}
				aria-valuemax={100}
				aria-valuenow={progressPercent}
				aria-valuetext={setupProgressLabel}
				title={setupProgressLabel}
			>
				<span style={{ width: `${progressPercent}%` }} />
			</div>

			<div className="setup-progress-list">
				{progressItems.map((item) => {
					const Icon = SETUP_ICON_BY_ID[item.id] || ClipboardList;
					const setupItemLabel = `${item.title} ${item.done ? "완료됨" : "미완료"}, ${item.detail}`;

					return (
						<button
							key={item.id}
							type="button"
							className={`setup-progress-item ${item.done ? "is-done" : ""}`}
							onClick={() => handleItemClick(item)}
							aria-label={setupItemLabel}
							title={setupItemLabel}
						>
							<span className="setup-progress-icon" aria-hidden="true">
								{item.done ? (
									<Check size={15} strokeWidth={3} />
								) : (
									<Icon size={17} strokeWidth={2.2} />
								)}
							</span>
							<span className="setup-progress-copy">
								<span className="setup-progress-label">{item.title}</span>
								<span className="setup-progress-detail">{item.detail}</span>
							</span>
							{!item.done ? (
								<span className="setup-progress-action">열기</span>
							) : null}
						</button>
					);
				})}
			</div>
		</section>
	);
}

function PenCattleList(options = {}) {
	const { cattleList, buildingId, penId, onSelect } =
		normalizeDashboardHelperOptions(options);
	const visibleCattle = normalizeDashboardHelperItems(cattleList);
	const handleSelect = typeof onSelect === "function" ? onSelect : () => {};

	const penCattle = visibleCattle.filter(
		(cow) => cow.buildingId === buildingId && cow.penNumber === penId,
	);

	return (
		<div className="flex flex-col gap-3">
			{penCattle.length > 0 ? (
				penCattle.map((cow, index) => (
					<CattleRow
						key={cow.id}
						cow={cow}
						onClick={handleSelect}
						delay={index * 50}
						draggable
					/>
				))
			) : (
				<Card className="animate-fadeIn border-2 border-dashed">
					<CardContent className="text-center py-12 px-5">
						<div className="text-3xl mb-2" aria-hidden="true">
							🐄
						</div>
						<p className="text-muted-foreground">이 칸은 비어 있습니다.</p>
					</CardContent>
				</Card>
			)}
		</div>
	);
}
