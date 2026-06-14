"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { LogOut, MapPin, Settings, Trash2 } from "lucide-react";
import { signOut, useSession } from "next-auth/react";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useAppFeedback } from "@/components/feedback/FeedbackProvider";
import {
	clearDeadLetterQueue,
	getDeadLetterQueue,
} from "@/lib/offlineQueue";
import { PremiumButton } from "@/components/ui/premium-button";
import {
	PremiumInput,
	PremiumLabel,
	PremiumSelect,
} from "@/components/ui/premium-input";
import {
	buildingFormSchema,
	createBuildingFormValues,
	createFarmSettingsValues,
	farmSettingsSchema,
} from "@/lib/formSchemas";
import { focusElementSafely } from "@/lib/safeFocus";
import { deleteAccount } from "@/lib/actions";

const errorTextStyle = {
	fontSize: "12px",
	marginTop: "6px",
	color: "var(--color-danger)",
	fontWeight: 600,
};

const widgetSettingsGridStyle = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(88px, 1fr))",
	gap: "8px",
};

const widgetSettingsGridViewportStyle = {
	overflowY: "auto",
	overscrollBehavior: "contain",
	paddingRight: "2px",
	paddingBottom: "12px",
	scrollPaddingBottom: "64px",
};

const widgetSettingsControlStyle = {
	display: "grid",
	gridTemplateColumns: "1fr",
	alignItems: "start",
	gap: "10px",
	minHeight: "70px",
	minWidth: 0,
	padding: "8px",
	borderRadius: "10px",
	background: "var(--color-bg)",
	border: "1px solid var(--color-border)",
	transition: "all 0.2s ease",
};

const widgetSettingsLabelStyle = {
	display: "grid",
	gridTemplateColumns: "16px minmax(0, 1fr)",
	alignItems: "center",
	gap: "8px",
	minWidth: 0,
};

const widgetSettingsTextStyle = {
	minWidth: 0,
};

const widgetSettingsNameStyle = {
	display: "block",
	fontSize: "12px",
	fontWeight: 700,
	lineHeight: 1.25,
	color: "var(--color-text)",
	overflowWrap: "anywhere",
};

function normalizeSettingsBuildings(buildings) {
	return Array.isArray(buildings)
		? buildings
				.filter(
					(building) =>
						building &&
						typeof building === "object" &&
						!Array.isArray(building) &&
						building.id != null,
				)
				.map((building) => ({
					...building,
					name:
						typeof building.name === "string" && building.name.trim()
							? building.name
							: "축사 이름 미등록",
					penCount: Number.isFinite(Number(building.penCount))
						? building.penCount
						: 0,
				}))
		: [];
}

function normalizeSettingsTabOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeSettingsWidgetRegistry(widgets) {
	return Array.isArray(widgets)
		? widgets.filter(
				(widget) => widget && typeof widget === "object" && !Array.isArray(widget),
			)
		: [];
}

function normalizeSettingsWidgetVisible(widgetVisible) {
	return widgetVisible &&
		typeof widgetVisible === "object" &&
		!Array.isArray(widgetVisible)
		? widgetVisible
		: {};
}

export default function SettingsTab(options = {}) {
	const {
		buildings = [],
		onCreateBuilding,
		onDeleteBuilding,
		farmSettings,
		onUpdateFarmSettings,
		theme,
		onToggleTheme,
		widgetRegistry = [],
		widgetVisible = {},
		onToggleWidget,
		quickActionIntent = null,
		subscriptionStatus = null,
	} = normalizeSettingsTabOptions(options);
	const safeBuildings = normalizeSettingsBuildings(buildings);
	const safeWidgetRegistry = normalizeSettingsWidgetRegistry(widgetRegistry);
	const safeWidgetVisible = normalizeSettingsWidgetVisible(widgetVisible);
	const [isAdding, setIsAdding] = useState(
		() => quickActionIntent?.actionId === "add-building",
	);
	const [isSavingFarm, setIsSavingFarm] = useState(false);
	const [isSavingBuilding, setIsSavingBuilding] = useState(false);
	const [deletingBuildingId, setDeletingBuildingId] = useState(null);
	const [deadLetterItems, setDeadLetterItems] = useState([]);
	const [pwCurrent, setPwCurrent] = useState("");
	const [pwNew, setPwNew] = useState("");
	const [pwConfirm, setPwConfirm] = useState("");
	const [pwError, setPwError] = useState("");
	const [pwSuccess, setPwSuccess] = useState(false);
	const [isSavingPw, setIsSavingPw] = useState(false);
	const { data: currentSession } = useSession();
	const currentUsername = currentSession?.user?.name || "";
	const isMountedRef = useRef(false);
	const buildingFormRef = useRef(null);
	const buildingNameInputRef = useRef(null);
	const farmSaveInFlightRef = useRef(false);
	const buildingSaveInFlightRef = useRef(false);
	const deleteBuildingInFlightRef = useRef(false);
	const { confirm } = useAppFeedback();
	const handleCreateBuilding =
		typeof onCreateBuilding === "function" ? onCreateBuilding : async () => false;
	const handleDeleteBuildingAction =
		typeof onDeleteBuilding === "function" ? onDeleteBuilding : async () => false;
	const handleUpdateFarmSettings =
		typeof onUpdateFarmSettings === "function"
			? onUpdateFarmSettings
			: async () => false;
	const handleToggleTheme =
		typeof onToggleTheme === "function" ? onToggleTheme : () => {};
	const handleToggleWidget =
		typeof onToggleWidget === "function" ? onToggleWidget : () => {};
	const farmSubmitButtonLabel = isSavingFarm
		? "농장 정보 저장 중"
		: "농장 정보 저장";
	const farmSubmitButtonText = isSavingFarm
		? "농장 정보 저장 중..."
		: "농장 정보 저장";
	const buildingSubmitButtonLabel = isSavingBuilding
		? "축사 등록 중"
		: "축사 등록";
	const buildingSubmitButtonText = isSavingBuilding
		? "축사 등록 중..."
		: "축사 등록";
	const buildingAddFormButtonLabel = isSavingBuilding
		? "축사 저장 중에는 등록 창을 닫을 수 없습니다"
		: isAdding
			? "축사 등록 취소"
			: "축사 등록 창 열기";
	const buildingAddFormButtonText = isSavingBuilding
		? "축사 저장 중..."
		: isAdding
			? "축사 등록 취소"
			: "축사 등록";

	const {
		register: registerBuilding,
		handleSubmit: handleSubmitBuilding,
		reset: resetBuilding,
		formState: { errors: buildingErrors },
	} = useForm({
		resolver: zodResolver(buildingFormSchema),
		defaultValues: createBuildingFormValues(),
	});
	const buildingNameRegistration = registerBuilding("name");

	const {
		register: registerFarm,
		handleSubmit: handleSubmitFarm,
		reset: resetFarm,
		setValue: setFarmValue,
		formState: { errors: farmErrors },
	} = useForm({
		resolver: zodResolver(farmSettingsSchema),
		defaultValues: createFarmSettingsValues(farmSettings),
	});

	useEffect(() => {
		isMountedRef.current = true;
		setDeadLetterItems(getDeadLetterQueue());

		return () => {
			isMountedRef.current = false;
			farmSaveInFlightRef.current = false;
			buildingSaveInFlightRef.current = false;
			deleteBuildingInFlightRef.current = false;
		};
	}, []);

	useEffect(() => {
		resetFarm(createFarmSettingsValues(farmSettings));
	}, [farmSettings, resetFarm]);

	useEffect(() => {
		if (!isAdding) {
			return;
		}

		const timeoutId = window.setTimeout(() => {
			try {
				buildingFormRef.current?.scrollIntoView({
					behavior: "smooth",
					block: "start",
					inline: "nearest",
				});
			} catch {
				buildingFormRef.current?.scrollIntoView();
			}

			focusElementSafely(buildingNameInputRef.current);
		}, 0);

		return () => {
			window.clearTimeout(timeoutId);
		};
	}, [isAdding, quickActionIntent?.nonce]);

	const koreanLocations = [
			{ name: "서울", lat: 37.566, lng: 126.978 },
			{ name: "부산", lat: 35.179, lng: 129.075 },
			{ name: "대구", lat: 35.871, lng: 128.601 },
			{ name: "인천", lat: 37.456, lng: 126.705 },
			{ name: "광주", lat: 35.16, lng: 126.851 },
			{ name: "대전", lat: 36.35, lng: 127.384 },
			{ name: "울산", lat: 35.538, lng: 129.311 },
			{ name: "세종", lat: 36.48, lng: 127.289 },
			{ name: "경기 수원", lat: 37.263, lng: 127.028 },
			{ name: "강원 춘천", lat: 37.881, lng: 127.729 },
			{ name: "충북 청주", lat: 36.642, lng: 127.489 },
			{ name: "충남 홍성", lat: 36.601, lng: 126.66 },
			{ name: "전북 전주", lat: 35.824, lng: 127.147 },
			{ name: "전북 남원", lat: 35.416, lng: 127.39 },
			{ name: "전북 남원 대강", lat: 35.446, lng: 127.344 },
			{ name: "전남 무안", lat: 34.99, lng: 126.471 },
			{ name: "경북 안동", lat: 36.568, lng: 128.729 },
			{ name: "경남 창원", lat: 35.227, lng: 128.681 },
			{ name: "제주", lat: 33.499, lng: 126.531 },
	];

	const handleLocationSelect = (event) => {
		if (farmSaveInFlightRef.current || isSavingFarm) {
			return;
		}

		const selected = koreanLocations.find(
			(location) => location.name === event.target.value,
		);
		if (!selected) {
			return;
		}

		setFarmValue("location", selected.name, {
			shouldDirty: true,
			shouldValidate: true,
		});
		setFarmValue("latitude", selected.lat, {
			shouldDirty: true,
			shouldValidate: true,
		});
		setFarmValue("longitude", selected.lng, {
			shouldDirty: true,
			shouldValidate: true,
		});
	};

	const submitBuilding = async (values) => {
		if (buildingSaveInFlightRef.current) {
			return;
		}

		buildingSaveInFlightRef.current = true;
		setIsSavingBuilding(true);

		try {
			const saved = await handleCreateBuilding(values);
			if (!saved || !isMountedRef.current) {
				return;
			}

			setIsAdding(false);
			resetBuilding(createBuildingFormValues());
		} finally {
			buildingSaveInFlightRef.current = false;
			if (isMountedRef.current) {
				setIsSavingBuilding(false);
			}
		}
	};

	const submitFarmSettings = async (values) => {
		if (farmSaveInFlightRef.current) {
			return;
		}

		farmSaveInFlightRef.current = true;
		setIsSavingFarm(true);

		try {
			await handleUpdateFarmSettings(values);
		} finally {
			farmSaveInFlightRef.current = false;
			if (isMountedRef.current) {
				setIsSavingFarm(false);
			}
		}
	};

	const handleFarmSubmit = (event) => {
		void handleSubmitFarm(submitFarmSettings)(event);
	};

	const handleBuildingSubmit = (event) => {
		void handleSubmitBuilding(submitBuilding)(event);
	};

	const handleDeleteBuilding = async (id, name) => {
		if (deleteBuildingInFlightRef.current) {
			return;
		}

		deleteBuildingInFlightRef.current = true;

		const shouldDelete = await confirm({
			title: `${name} 축사를 삭제할까요?`,
			description: "연결된 개체가 있으면 삭제되지 않습니다.",
			confirmLabel: "축사 삭제",
			cancelLabel: "축사 삭제 취소",
			variant: "destructive",
		});

		if (!shouldDelete || !isMountedRef.current) {
			deleteBuildingInFlightRef.current = false;
			return;
		}

		setDeletingBuildingId(id);

		try {
			await handleDeleteBuildingAction(id);
		} finally {
			deleteBuildingInFlightRef.current = false;
			if (isMountedRef.current) {
				setDeletingBuildingId(null);
			}
		}
	};

	const handleClearDeadLetter = () => {
		clearDeadLetterQueue();
		setDeadLetterItems([]);
	};

	const handleChangePassword = async (e) => {
		e.preventDefault();
		setPwError("");
		setPwSuccess(false);
		if (pwNew !== pwConfirm) {
			setPwError("새 비밀번호가 일치하지 않습니다.");
			return;
		}
		setIsSavingPw(true);
		try {
			const res = await fetch("/api/auth/change-password", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ currentPassword: pwCurrent, newPassword: pwNew }),
			});
			const data = await res.json();
			if (!res.ok) {
				setPwError(data.error || "비밀번호 변경에 실패했습니다.");
				return;
			}
			setPwSuccess(true);
			setPwCurrent("");
			setPwNew("");
			setPwConfirm("");
		} catch {
			setPwError("네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
		} finally {
			if (isMountedRef.current) setIsSavingPw(false);
		}
	};

	const isDark = theme === "dark";

	return (
		<div>
			<div className="section-header" style={{ marginBottom: "22px" }}>
				<Settings
					size={20}
					className="text-[color:var(--color-text)]"
					aria-hidden="true"
				/>
				<h2 className="section-header-title">환경 설정</h2>
			</div>

			<div
				style={{
					background: "var(--color-bg-card)",
					padding: "18px 20px",
					borderRadius: "20px",
					boxShadow: "var(--shadow-sm)",
					border: "1px solid var(--color-surface-stroke)",
					marginBottom: "20px",
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
					transition: "all 0.3s cubic-bezier(0.22,1,0.36,1)",
				}}
			>
				<div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
					<span aria-hidden="true" style={{ fontSize: "20px" }}>
						{isDark ? "야" : "주"}
					</span>
					<div>
						<div
							style={{
								fontSize: "14px",
								fontWeight: 700,
								color: "var(--color-text)",
							}}
						>
							다크모드
						</div>
						<div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
							{isDark ? "어두운 화면 사용 중" : "밝은 화면 사용 중"}
						</div>
					</div>
				</div>
				<button
					type="button"
					onClick={handleToggleTheme}
					role="switch"
					aria-checked={isDark}
					aria-label={isDark ? "다크모드 끄기" : "다크모드 켜기"}
					title={isDark ? "다크모드 끄기" : "다크모드 켜기"}
					style={{
						width: "52px",
						height: "44px",
						borderRadius: "22px",
						border: "none",
						cursor: "pointer",
						position: "relative",
						display: "inline-flex",
						alignItems: "center",
						justifyContent: "center",
						padding: 0,
						background: "transparent",
					}}
				>
					<div
						aria-hidden="true"
						style={{
							width: "52px",
							height: "28px",
							borderRadius: "14px",
							position: "relative",
							background: isDark
								? "var(--color-primary)"
								: "var(--color-border)",
							transition: "background 0.3s ease",
						}}
					>
						<div
							style={{
								width: "22px",
								height: "22px",
								borderRadius: "50%",
								background: "var(--color-bg-card)",
								position: "absolute",
								top: "3px",
								left: isDark ? "27px" : "3px",
								transition: "left 0.3s ease",
								boxShadow: "0 1px 4px rgba(0,0,0,0.2)",
							}}
						/>
					</div>
				</button>
			</div>

			{safeWidgetRegistry.length > 0 ? (
				<div
					className="settings-widget-card"
					style={{
						background: "var(--color-bg-card)",
						padding: "var(--settings-widget-card-padding, 18px 20px)",
						borderRadius: "16px",
						boxShadow: "var(--shadow-sm)",
						marginBottom: "var(--settings-widget-card-margin-bottom, 20px)",
					}}
				>
					<div
						style={{
							fontSize: "14px",
							fontWeight: 700,
							color: "var(--color-text)",
							marginBottom: "var(--settings-widget-title-margin-bottom, 14px)",
							display: "flex",
							alignItems: "center",
							gap: "8px",
						}}
					>
						<span aria-hidden="true" style={{ fontSize: "18px" }}>
							위젯
						</span>{" "}
						대시보드 위젯
					</div>
					<div
						style={{
							fontSize: "11px",
							color: "var(--color-text-muted)",
							marginBottom: "var(--settings-widget-description-margin-bottom, 12px)",
						}}
					>
						홈 화면에 표시할 위젯을 선택해 주세요.
					</div>
					<div
						className="settings-widget-grid-viewport"
						style={widgetSettingsGridViewportStyle}
					>
						<div style={widgetSettingsGridStyle}>
							{safeWidgetRegistry.map((widget) => {
								const isOn = safeWidgetVisible[widget.id] !== false;

								return (
									<div key={widget.id} style={widgetSettingsControlStyle}>
										<div style={widgetSettingsLabelStyle}>
											<span aria-hidden="true" style={{ fontSize: "16px" }}>
												{widget.icon}
											</span>
											<span
												style={widgetSettingsTextStyle}
												title={widget.description ?? undefined}
											>
												<span style={widgetSettingsNameStyle}>
													{widget.label}
												</span>
											</span>
										</div>
										<button
											type="button"
											onClick={() => handleToggleWidget(widget.id)}
											role="switch"
											aria-checked={isOn}
											aria-label={`${widget.label} 위젯 ${isOn ? "숨기기" : "보이기"}`}
											title={`${widget.label} 위젯 ${isOn ? "숨기기" : "보이기"}`}
											style={{
												width: "44px",
												height: "44px",
												borderRadius: "22px",
												border: "none",
												cursor: "pointer",
												justifySelf: "end",
												position: "relative",
												display: "inline-flex",
												alignItems: "center",
												justifyContent: "center",
												padding: 0,
												background: "transparent",
											}}
										>
											<div
												aria-hidden="true"
												style={{
													width: "44px",
													height: "24px",
													borderRadius: "12px",
													position: "relative",
													background: isOn
														? "var(--color-success)"
														: "var(--color-border)",
													transition: "background 0.3s ease",
												}}
											>
												<div
													style={{
														width: "18px",
														height: "18px",
														borderRadius: "50%",
														background: "var(--color-bg-card)",
														position: "absolute",
														top: "3px",
														left: isOn ? "23px" : "3px",
														transition: "left 0.3s ease",
														boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
													}}
												/>
											</div>
										</button>
									</div>
								);
							})}
						</div>
					</div>
				</div>
			) : null}

			<form
				className="settings-farm-form"
				onSubmit={handleFarmSubmit}
				style={{
					background: "var(--color-bg-card)",
					padding: "20px",
					borderRadius: "16px",
					boxShadow: "var(--shadow-sm)",
					marginTop: "var(--settings-farm-form-margin-top, 0)",
					marginBottom: "var(--settings-farm-form-margin-bottom, 30px)",
				}}
			>
				<div
					style={{
						fontSize: "15px",
						fontWeight: 700,
						marginBottom: "16px",
						color: "var(--color-text)",
						display: "flex",
						alignItems: "center",
						gap: "6px",
					}}
				>
					<MapPin size={16} aria-hidden="true" /> 농장 정보 설정
				</div>

				<div
					className="settings-farm-fields-viewport"
					style={{ display: "grid", gap: "16px" }}
				>
					<div>
						<PremiumLabel htmlFor="farm-name">농장 이름</PremiumLabel>
						<PremiumInput
							id="farm-name"
							{...registerFarm("name")}
							placeholder="예: 행복한 한우 농장"
							hasError={!!farmErrors.name}
							disabled={isSavingFarm}
							aria-invalid={Boolean(farmErrors.name)}
							aria-describedby={farmErrors.name ? "farm-name-error" : undefined}
						/>
						{farmErrors.name ? (
							<div id="farm-name-error" role="alert" style={errorTextStyle}>
								{farmErrors.name.message}
							</div>
						) : null}
					</div>

					<div>
						<PremiumLabel htmlFor="farm-location-select">
							지역 선택 (자동 입력)
						</PremiumLabel>
						<PremiumSelect
							id="farm-location-select"
							onChange={handleLocationSelect}
							className="mb-2"
							hasError={false}
							disabled={isSavingFarm}
						>
							<option value="" className="bg-slate-900">
								주요 지역 선택...
							</option>
							{koreanLocations.map((location) => (
								<option
									key={location.name}
									value={location.name}
									className="bg-slate-900"
								>
									{location.name}
								</option>
							))}
						</PremiumSelect>
						<PremiumLabel htmlFor="farm-location">지역명</PremiumLabel>
						<PremiumInput
							id="farm-location"
							{...registerFarm("location")}
							placeholder="지역명을 직접 입력해 주세요."
							hasError={!!farmErrors.location}
							disabled={isSavingFarm}
							aria-invalid={Boolean(farmErrors.location)}
							aria-describedby={
								farmErrors.location ? "farm-location-error" : undefined
							}
						/>
						{farmErrors.location ? (
							<div id="farm-location-error" role="alert" style={errorTextStyle}>
								{farmErrors.location.message}
							</div>
						) : null}
					</div>

					<div
						style={{
							display: "grid",
							gridTemplateColumns: "1fr 1fr",
							gap: "10px",
						}}
					>
						<div>
							<PremiumLabel htmlFor="farm-latitude">위도</PremiumLabel>
							<PremiumInput
								id="farm-latitude"
								type="number"
								step="0.001"
								{...registerFarm("latitude")}
								placeholder="35.446"
								hasError={!!farmErrors.latitude}
								disabled={isSavingFarm}
								aria-invalid={Boolean(farmErrors.latitude)}
								aria-describedby={
									farmErrors.latitude ? "farm-latitude-error" : undefined
								}
							/>
							{farmErrors.latitude ? (
								<div
									id="farm-latitude-error"
									role="alert"
									style={errorTextStyle}
								>
									{farmErrors.latitude.message}
								</div>
							) : null}
						</div>
						<div>
							<PremiumLabel htmlFor="farm-longitude">경도</PremiumLabel>
							<PremiumInput
								id="farm-longitude"
								type="number"
								step="0.001"
								{...registerFarm("longitude")}
								placeholder="127.344"
								hasError={!!farmErrors.longitude}
								disabled={isSavingFarm}
								aria-invalid={Boolean(farmErrors.longitude)}
								aria-describedby={
									farmErrors.longitude ? "farm-longitude-error" : undefined
								}
							/>
							{farmErrors.longitude ? (
								<div
									id="farm-longitude-error"
									role="alert"
									style={errorTextStyle}
								>
									{farmErrors.longitude.message}
								</div>
							) : null}
						</div>
					</div>

					<div
						style={{
							fontSize: "11px",
							color: "var(--color-text-muted)",
							marginBottom: "4px",
						}}
					>
						정확한 날씨 정보를 위해 좌표를 확인해 주세요.
					</div>

					<PremiumButton
						type="submit"
						disabled={isSavingFarm}
						aria-busy={isSavingFarm}
						aria-label={farmSubmitButtonLabel}
						title={farmSubmitButtonLabel}
						className="w-full mt-1 py-3.5 rounded-[10px]"
						glow
					>
						{farmSubmitButtonText}
					</PremiumButton>

					<div
						style={{
							marginTop: "10px",
							borderTop: "1px dashed var(--color-border)",
							paddingTop: "10px",
							textAlign: "center",
						}}
					>
						<a
							href="/admin/diagnostics"
							aria-label="시스템 진단 도구 열기"
							title="시스템 진단 도구 열기"
							style={{
								fontSize: "12px",
								color: "var(--color-text-muted)",
								textDecoration: "none",
							}}
						>
							시스템 진단 도구
						</a>
					</div>
				</div>
			</form>

			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
					marginBottom: "16px",
				}}
			>
				<div
					style={{
						fontSize: "15px",
						fontWeight: 700,
						color: "var(--color-text-secondary)",
					}}
				>
					축사 관리
				</div>
				<PremiumButton
					variant="secondary"
					size="sm"
					disabled={isSavingBuilding}
					aria-busy={isSavingBuilding}
					aria-label={buildingAddFormButtonLabel}
					title={buildingAddFormButtonLabel}
					onClick={() => {
						const next = !isAdding;
						setIsAdding(next);
						if (!next) {
							resetBuilding(createBuildingFormValues());
						}
					}}
					className="text-xs px-3 py-1.5 rounded-lg font-bold"
				>
					{buildingAddFormButtonText}
				</PremiumButton>
			</div>

			{isAdding ? (
				<form
					ref={buildingFormRef}
					onSubmit={handleBuildingSubmit}
					style={{
						background: "var(--color-bg-card)",
						padding: "20px",
						borderRadius: "12px",
						boxShadow: "var(--shadow-sm)",
						marginBottom: "20px",
					}}
				>
					<div
						style={{
							fontSize: "14px",
							fontWeight: 700,
							marginBottom: "12px",
							color: "var(--color-text)",
						}}
					>
						새 축사 등록
					</div>
					<div style={{ display: "grid", gap: "12px" }}>
						<div>
							<PremiumLabel htmlFor="building-name">축사 이름</PremiumLabel>
							<PremiumInput
								id="building-name"
								{...buildingNameRegistration}
								ref={(element) => {
									buildingNameRegistration.ref(element);
									buildingNameInputRef.current = element;
								}}
								placeholder="축사 이름을 입력해 주세요."
								hasError={!!buildingErrors.name}
								aria-invalid={Boolean(buildingErrors.name)}
								aria-describedby={
									buildingErrors.name ? "building-name-error" : undefined
								}
							/>
							{buildingErrors.name ? (
								<div
									id="building-name-error"
									role="alert"
									style={errorTextStyle}
								>
									{buildingErrors.name.message}
								</div>
							) : null}
						</div>

						<div>
							<PremiumLabel htmlFor="building-pen-count">
								칸 수
							</PremiumLabel>
							<PremiumInput
								id="building-pen-count"
								type="number"
								{...registerBuilding("penCount")}
								hasError={!!buildingErrors.penCount}
								aria-invalid={Boolean(buildingErrors.penCount)}
								aria-describedby={
									buildingErrors.penCount
										? "building-pen-count-error"
										: undefined
								}
							/>
							{buildingErrors.penCount ? (
								<div
									id="building-pen-count-error"
									role="alert"
									style={errorTextStyle}
								>
									{buildingErrors.penCount.message}
								</div>
							) : null}
						</div>

						<PremiumButton
							type="submit"
							variant="primary"
							disabled={isSavingBuilding}
							aria-busy={isSavingBuilding}
							aria-label={buildingSubmitButtonLabel}
							title={buildingSubmitButtonLabel}
							className="w-full py-3 rounded-lg"
							glow
						>
							{buildingSubmitButtonText}
						</PremiumButton>
					</div>
				</form>
			) : null}

			<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
				{safeBuildings.map((building) => {
					const isDeletingBuilding = deletingBuildingId === building.id;
					const buildingDeleteButtonLabel = isDeletingBuilding
						? `${building.name} 축사 삭제 중`
						: `${building.name} 축사 삭제`;

					return (
						<div
							key={building.id}
							style={{
								background: "var(--color-bg-card)",
								padding: "16px",
								borderRadius: "12px",
								border: "1px solid var(--color-border)",
								display: "flex",
								justifyContent: "space-between",
								alignItems: "center",
							}}
						>
							<div>
								<div
									style={{
										fontSize: "16px",
										fontWeight: 700,
										color: "var(--color-text)",
									}}
								>
									{building.name}
								</div>
								<div
									style={{ fontSize: "12px", color: "var(--color-text-muted)" }}
								>
									총 {building.penCount}칸
								</div>
							</div>
							<PremiumButton
								variant="outline"
								size="sm"
								onClick={() => handleDeleteBuilding(building.id, building.name)}
								disabled={isDeletingBuilding}
								aria-busy={isDeletingBuilding}
								aria-label={buildingDeleteButtonLabel}
								title={buildingDeleteButtonLabel}
								className="text-xs text-red-500 border-red-500/50 hover:bg-red-500/10 px-2 py-1 rounded h-auto"
							>
								{isDeletingBuilding ? "축사 삭제 중..." : "축사 삭제"}
							</PremiumButton>
						</div>
					);
				})}
			</div>

			{deadLetterItems.length > 0 ? (
				<div
					style={{
						marginTop: "28px",
						background: "var(--color-bg-card)",
						padding: "18px 20px",
						borderRadius: "16px",
						border: "1px solid var(--color-danger)",
						boxShadow: "var(--shadow-sm)",
					}}
				>
					<div
						style={{
							display: "flex",
							justifyContent: "space-between",
							alignItems: "center",
							marginBottom: "12px",
						}}
					>
						<div>
							<div
								style={{
									fontSize: "14px",
									fontWeight: 700,
									color: "var(--color-danger)",
									marginBottom: "2px",
								}}
							>
								동기화 실패 항목 ({deadLetterItems.length}건)
							</div>
							<div
								style={{ fontSize: "11px", color: "var(--color-text-muted)" }}
							>
								자동 재시도가 중단된 오프라인 요청입니다.
							</div>
						</div>
						<PremiumButton
							variant="outline"
							size="sm"
							onClick={handleClearDeadLetter}
							aria-label="동기화 실패 항목 전체 삭제"
							title="동기화 실패 항목 전체 삭제"
							className="text-xs text-red-500 border-red-500/50 hover:bg-red-500/10 px-3 py-1.5 rounded-lg"
						>
							전체 삭제
						</PremiumButton>
					</div>
					<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
						{deadLetterItems.map((item, idx) => (
							<div
								key={item.id ?? idx}
								style={{
									background: "var(--color-bg)",
									padding: "10px 14px",
									borderRadius: "10px",
									border: "1px solid var(--color-border)",
									fontSize: "12px",
									color: "var(--color-text-muted)",
									display: "flex",
									justifyContent: "space-between",
									alignItems: "center",
									gap: "8px",
								}}
							>
								<span
									style={{
										fontFamily: "var(--font-mono, monospace)",
										fontWeight: 600,
									}}
								>
									{item.action ?? "알 수 없는 작업"}
								</span>
								{item.deadLetteredAt ? (
									<span>
										{new Date(item.deadLetteredAt).toLocaleString("ko-KR", {
											month: "2-digit",
											day: "2-digit",
											hour: "2-digit",
											minute: "2-digit",
										})}
									</span>
								) : null}
							</div>
						))}
					</div>
				</div>
			) : null}

			{/* 비밀번호 변경 */}
			<div
				style={{
					background: "var(--color-bg-card)",
					padding: "18px 20px",
					borderRadius: "20px",
					border: "1px solid var(--color-surface-stroke)",
					marginTop: "20px",
				}}
			>
				<div style={{ fontWeight: 700, fontSize: "14px", color: "var(--color-text)", marginBottom: "14px" }}>
					비밀번호 변경
				</div>
				<form onSubmit={handleChangePassword} noValidate style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
					<PremiumInput
						id="pw-current"
						type="password"
						placeholder="현재 비밀번호"
						value={pwCurrent}
						onChange={(e) => { setPwCurrent(e.target.value); setPwError(""); setPwSuccess(false); }}
						aria-label="현재 비밀번호"
						autoComplete="current-password"
					/>
					<PremiumInput
						id="pw-new"
						type="password"
						placeholder="새 비밀번호 (8자 이상)"
						value={pwNew}
						onChange={(e) => { setPwNew(e.target.value); setPwError(""); setPwSuccess(false); }}
						aria-label="새 비밀번호"
						autoComplete="new-password"
					/>
					<PremiumInput
						id="pw-confirm"
						type="password"
						placeholder="새 비밀번호 확인"
						value={pwConfirm}
						onChange={(e) => { setPwConfirm(e.target.value); setPwError(""); setPwSuccess(false); }}
						aria-label="새 비밀번호 확인"
						autoComplete="new-password"
					/>
					{pwError && (
						<div role="alert" style={{ fontSize: "12px", color: "var(--color-danger)", fontWeight: 600 }}>
							{pwError}
						</div>
					)}
					{pwSuccess && (
						<div role="status" style={{ fontSize: "12px", color: "#16a34a", fontWeight: 600 }}>
							비밀번호가 변경되었습니다.
						</div>
					)}
					<PremiumButton
						type="submit"
						variant="secondary"
						size="sm"
						disabled={isSavingPw || !pwCurrent || !pwNew || !pwConfirm}
						aria-busy={isSavingPw}
						className="self-end"
					>
						{isSavingPw ? "변경 중..." : "비밀번호 변경"}
					</PremiumButton>
				</form>
			</div>

			{/* 구독 현황 */}
			{subscriptionStatus && (
				<div
					style={{
						background: "var(--color-bg-card)",
						padding: "18px 20px",
						borderRadius: "20px",
						border: "1px solid var(--color-surface-stroke)",
						marginTop: "20px",
					}}
				>
					<div style={{ fontWeight: 700, fontSize: "14px", color: "var(--color-text)", marginBottom: "12px" }}>
						구독 현황
					</div>
					<div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
						<div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
							{subscriptionStatus.status === "ACTIVE" && (
								<>
									<span
										style={{
											display: "inline-flex",
											alignItems: "center",
											padding: "3px 10px",
											borderRadius: "999px",
											background: "color-mix(in srgb, #16a34a 12%, transparent)",
											color: "#16a34a",
											fontWeight: 700,
											fontSize: "11px",
											letterSpacing: "0.03em",
										}}
									>
										프리미엄 구독 중
									</span>
									{subscriptionStatus.daysLeft != null && (
										<span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
											{subscriptionStatus.daysLeft}일 후 갱신
										</span>
									)}
								</>
							)}
							{subscriptionStatus.status === "TRIAL" && (
								<>
									<span
										style={{
											display: "inline-flex",
											alignItems: "center",
											padding: "3px 10px",
											borderRadius: "999px",
											background: "color-mix(in srgb, var(--color-accent) 12%, transparent)",
											color: "var(--color-accent)",
											fontWeight: 700,
											fontSize: "11px",
											letterSpacing: "0.03em",
										}}
									>
										무료 체험 중
									</span>
									{subscriptionStatus.daysLeft != null && (
										<span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
											{subscriptionStatus.daysLeft > 0
												? `${subscriptionStatus.daysLeft}일 남음`
												: "오늘 만료"}
										</span>
									)}
								</>
							)}
							{subscriptionStatus.status === "INACTIVE" && (
								<span
									style={{
										display: "inline-flex",
										alignItems: "center",
										padding: "3px 10px",
										borderRadius: "999px",
										background: "color-mix(in srgb, var(--color-text-muted) 12%, transparent)",
										color: "var(--color-text-secondary)",
										fontWeight: 700,
										fontSize: "11px",
										letterSpacing: "0.03em",
									}}
								>
									미구독
								</span>
							)}
						</div>
						<a
							href="/subscription"
							style={{
								fontSize: "12px",
								color: "var(--color-accent)",
								fontWeight: 600,
								textDecoration: "none",
							}}
						>
							{subscriptionStatus.status === "ACTIVE" ? "구독 관리" : "구독하기"} →
						</a>
					</div>
				</div>
			)}

			{/* 로그아웃 */}
			<div
				style={{
					background: "var(--color-bg-card)",
					padding: "18px 20px",
					borderRadius: "20px",
					border: "1px solid var(--color-surface-stroke)",
					marginTop: "20px",
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
				}}
			>
				<div>
					{currentUsername ? (
						<div style={{ fontSize: "11px", color: "var(--color-text-secondary)", marginBottom: "2px" }}>
							로그인 계정:{" "}
							<strong style={{ color: "var(--color-text)" }}>{currentUsername}</strong>
						</div>
					) : null}
					<div style={{ fontWeight: 700, fontSize: "14px", color: "var(--color-text)" }}>
						로그아웃
					</div>
					<div style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginTop: "2px" }}>
						현재 기기에서 로그인 세션을 종료합니다.
					</div>
				</div>
				<PremiumButton
					variant="outline"
					size="sm"
					onClick={() => signOut({ callbackUrl: "/" })}
					aria-label="로그아웃"
					title="로그아웃"
					className="gap-1.5"
				>
					<LogOut size={14} aria-hidden="true" />
					로그아웃
				</PremiumButton>
			</div>

			{/* 계정 삭제 */}
			<DeleteAccountSection confirm={confirm} />
		</div>
	);
}

const DELETE_ACCOUNT_CONFIRM_MESSAGE =
	"계정을 삭제하면 로그인이 불가능해집니다. 농장 데이터(개체, 재고, 출하 기록 등)는 삭제되지 않습니다.\n\n정말 삭제하시겠습니까?";

function DeleteAccountSection(options = {}) {
	const { confirm: confirmDialog } =
		options && typeof options === "object" && !Array.isArray(options)
			? options
			: {};
	const safeConfirm = typeof confirmDialog === "function" ? confirmDialog : null;
	const [isDeleting, setIsDeleting] = useState(false);
	const [deleteError, setDeleteError] = useState("");
	const isMountedRef = useRef(false);
	useEffect(() => {
		isMountedRef.current = true;
		return () => {
			isMountedRef.current = false;
		};
	}, []);

	const handleDeleteAccount = async () => {
		if (isDeleting) return;
		if (safeConfirm) {
			const confirmed = await safeConfirm(DELETE_ACCOUNT_CONFIRM_MESSAGE);
			if (!confirmed) return;
		}
		setIsDeleting(true);
		setDeleteError("");
		try {
			const result = await deleteAccount();
			if (!result?.ok) {
				if (isMountedRef.current) {
					setDeleteError(result?.error ?? "계정 삭제에 실패했습니다.");
					setIsDeleting(false);
				}
				return;
			}
			await signOut({ callbackUrl: "/" });
		} catch {
			if (isMountedRef.current) {
				setDeleteError("계정 삭제 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
				setIsDeleting(false);
			}
		}
	};

	const deleteButtonLabel = isDeleting ? "계정 삭제 중" : "계정 삭제";

	return (
		<div
			style={{
				background: "var(--color-bg-card)",
				padding: "18px 20px",
				borderRadius: "20px",
				border: "1px solid color-mix(in srgb, var(--color-danger) 35%, var(--color-surface-stroke))",
				marginTop: "20px",
			}}
		>
			<div style={{ fontWeight: 700, fontSize: "14px", color: "var(--color-danger)", marginBottom: "4px" }}>
				계정 삭제
			</div>
			<div style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginBottom: "12px", lineHeight: 1.5 }}>
				계정을 삭제하면 로그인이 불가능해집니다. 농장 데이터는 삭제되지 않습니다.
			</div>
			{deleteError ? (
				<div
					role="alert"
					style={{
						fontSize: "12px",
						color: "var(--color-danger)",
						fontWeight: 600,
						marginBottom: "10px",
					}}
				>
					{deleteError}
				</div>
			) : null}
			<PremiumButton
				variant="outline"
				size="sm"
				onClick={handleDeleteAccount}
				disabled={isDeleting}
				aria-busy={isDeleting}
				aria-label={deleteButtonLabel}
				title={deleteButtonLabel}
				className="gap-1.5"
				style={{ borderColor: "var(--color-danger)", color: "var(--color-danger)" }}
			>
				<Trash2 size={14} aria-hidden="true" />
				{isDeleting ? "계정 삭제 중..." : "계정 삭제"}
			</PremiumButton>
		</div>
	);
}
