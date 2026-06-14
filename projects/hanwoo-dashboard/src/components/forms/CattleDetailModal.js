import { CalendarCheck2, CheckCircle2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
	Line,
	LineChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";
import {
	BackIcon,
	btnDanger,
	btnPrimary,
	btnSecondary,
	EditIcon,
	TrashIcon,
} from "@/components/ui/common";
import QRCodeWidget from "@/components/widgets/QRCodeWidget";
import { getCattleHistory } from "@/lib/actions";
import { extractWeightHistoryPoints } from "@/lib/cattle-history.mjs";
import { STATUS_COLORS } from "@/lib/constants";
import { focusElementSafely } from "@/lib/safeFocus";
import {
	formatDate,
	formatMoney,
	getCalvingDate,
	getDaysUntilEstrus,
	getMonthAge,
	toInputDate,
} from "@/lib/utils";

const HISTORY_ICONS = {
	status_change: "🔄",
	weight: "⚖️",
	calving: "🍼",
	movement: "🏠",
	purchase: "📥",
	sale: "💰",
};

function toStrictInputDate(value) {
	if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
		return null;
	}

	const date = new Date(`${value}T00:00:00.000Z`);
	return Number.isNaN(date.getTime()) ||
		date.toISOString().slice(0, 10) !== value
		? null
		: date;
}

function normalizeDetailBuildings(buildings) {
	return Array.isArray(buildings)
		? buildings
				.filter((building) => building && typeof building === "object")
				.map((building, index) => ({
					...building,
					id: building.id ?? `detail-building-${index}`,
					name:
						typeof building.name === "string" && building.name.trim()
							? building.name
							: "축사 이름 미등록",
				}))
		: [];
}

function deferCattleDetailTask(callback) {
	try {
		queueMicrotask(callback);
	} catch {
		Promise.resolve().then(callback);
	}
}

function formatDaysLeftLabel(daysLeft) {
	return daysLeft === 0 ? "오늘" : `${daysLeft}일 남음`;
}

export default function CattleDetailModal({
	cattle,
	buildings = [],
	isDeleting = false,
	onClose,
	onEdit,
	onDelete,
	onUpdate,
}) {
	const dialogRef = useRef(null);
	const [history, setHistory] = useState([]);
	const [activeBreedingAction, setActiveBreedingAction] = useState(null);
	const [breedingDate, setBreedingDate] = useState(toInputDate(new Date()));
	const [breedingError, setBreedingError] = useState("");
	const [isBreedingSaving, setIsBreedingSaving] = useState(false);
	const mountedRef = useRef(false);
	const breedingSaveInFlightRef = useRef(false);
	const safeBuildings = useMemo(
		() => normalizeDetailBuildings(buildings),
		[buildings],
	);

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
		return () => {
			cancelled = true;
		};
	}, [cattle?.id]);

	useEffect(() => {
		mountedRef.current = true;

		return () => {
			mountedRef.current = false;
			breedingSaveInFlightRef.current = false;
		};
	}, []);

	useEffect(() => {
		let cancelled = false;
		breedingSaveInFlightRef.current = false;

		deferCattleDetailTask(() => {
			if (cancelled) {
				return;
			}

			setActiveBreedingAction(null);
			setBreedingDate(toInputDate(new Date()));
			setBreedingError("");
			setIsBreedingSaving(false);
		});

		return () => {
			cancelled = true;
		};
	}, [cattle?.id]);

	useEffect(() => {
		focusElementSafely(dialogRef.current);
	}, [cattle?.id]);

	if (!cattle) return null;

	const monthAge = getMonthAge(cattle.birthDate);
	const statusColor = STATUS_COLORS[cattle.status] || {
		bg: "#eee",
		text: "#333",
	};
	const buildingName =
		safeBuildings.find((building) => building.id === cattle.buildingId)?.name ||
		cattle.buildingId ||
		"축사 미배정";
	const breedingDateErrorId = "breeding-record-date-error";
	const isDetailBusy = isDeleting || isBreedingSaving;
	const closeButtonLabel = isDetailBusy
		? `${cattle.name} 개체 처리 중에는 상세 창을 닫을 수 없습니다`
		: "개체 상세 닫기";
	const editButtonLabel = isDetailBusy
		? `${cattle.name} 개체 처리 중에는 수정할 수 없습니다`
		: `${cattle.name} 개체 정보 수정`;
	const editButtonText = isDetailBusy ? "개체 처리 중..." : "개체 정보 수정";
	const archiveButtonLabel = isDetailBusy
		? `${cattle.name} 개체 처리 중에는 보관할 수 없습니다`
		: `${cattle.name} 개체 보관 처리`;
	const archiveButtonText = isDetailBusy ? "개체 처리 중..." : "개체 보관 처리";
	const estrusButtonLabel = isDetailBusy
		? `${cattle.name} 개체 처리 중에는 발정 기록을 시작할 수 없습니다`
		: `${cattle.name} 발정 기록`;
	const estrusButtonText = isDetailBusy ? "개체 처리 중..." : "발정 기록";
	const pregnancyButtonLabel = isDetailBusy
		? `${cattle.name} 개체 처리 중에는 수정 기록을 시작할 수 없습니다`
		: `${cattle.name} 수정 기록`;
	const pregnancyButtonText = isDetailBusy ? "개체 처리 중..." : "수정 기록";
	const breedingCancelButtonLabel = isBreedingSaving
		? "번식 기록 저장 중에는 취소할 수 없습니다"
		: "번식 기록 취소";
	const breedingCancelButtonText = isBreedingSaving
		? "번식 기록 저장 중..."
		: "번식 기록 취소";
	const breedingSubmitButtonLabel = isBreedingSaving
		? "번식 기록 저장 중"
		: "번식 기록 저장";
	const breedingSubmitButtonText = isBreedingSaving
		? "번식 기록 저장 중..."
		: "번식 기록 저장";

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
		if (typeof cattle.weightHistory === "string") {
			try {
				return JSON.parse(cattle.weightHistory);
			} catch {
				return [];
			}
		}
		return [];
	})();
	const weightChartLabel = `${cattle.name} 체중 변화 차트. 날짜별 체중 기록을 선으로 비교합니다.`;

	const openBreedingForm = (action) => {
		if (breedingSaveInFlightRef.current || isDetailBusy) {
			return;
		}

		setActiveBreedingAction(action);
		setBreedingDate(toInputDate(new Date()));
		setBreedingError("");
	};

	const handleSaveBreedingRecord = async (event) => {
		event.preventDefault();

		if (breedingSaveInFlightRef.current || isBreedingSaving) {
			return;
		}

		if (!breedingDate) {
			setBreedingError("기록할 날짜를 선택해 주세요.");
			return;
		}

		const selectedDate = toStrictInputDate(breedingDate);

		if (!selectedDate) {
			setBreedingError("올바른 날짜를 선택해 주세요.");
			return;
		}

		const nextCattle =
			activeBreedingAction === "pregnancy"
				? {
						...cattle,
						status: "임신우",
						pregnancyDate: selectedDate.toISOString(),
					}
				: { ...cattle, lastEstrus: selectedDate.toISOString() };

		breedingSaveInFlightRef.current = true;
		setIsBreedingSaving(true);
		setBreedingError("");

		try {
			const saved = await onUpdate(nextCattle, {
				successTitle:
					activeBreedingAction === "pregnancy"
						? "수정 기록을 저장했습니다."
						: "발정 기록을 저장했습니다.",
				successDescription: `${formatDate(selectedDate)} 기록이 반영되었습니다.`,
				errorTitle: "번식 기록 저장에 실패했습니다.",
				offlineDescription: "번식 기록 수정 요청이 대기열에 저장되었습니다.",
			});

			if (saved !== false && mountedRef.current) {
				setActiveBreedingAction(null);
			}
		} finally {
			breedingSaveInFlightRef.current = false;
			if (mountedRef.current) {
				setIsBreedingSaving(false);
			}
		}
	};

	const handleDialogKeyDown = (event) => {
		if (event.key === "Escape") {
			if (isDetailBusy) {
				return;
			}
			onClose();
			return;
		}

		if (event.key === "Tab" && dialogRef.current) {
			const focusable = Array.from(
				dialogRef.current.querySelectorAll(
					'button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),a[href],[tabindex]:not([tabindex="-1"])',
				),
			);
			if (focusable.length === 0) return;
			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			if (event.shiftKey) {
				if (document.activeElement === first) {
					event.preventDefault();
					last.focus();
				}
			} else {
				if (document.activeElement === last) {
					event.preventDefault();
					first.focus();
				}
			}
		}
	};

	return (
		<div className="modal-overlay" style={{ alignItems: "flex-start" }}>
			<div
				ref={dialogRef}
				className="animate-slideInUp"
				role="dialog"
				aria-modal="true"
				aria-labelledby="cattle-detail-title"
				tabIndex={-1}
				onKeyDown={handleDialogKeyDown}
				style={{
					background: "var(--color-bg-card)",
					width: "100%",
					maxWidth: "600px",
					minHeight: "100vh",
					overflowY: "auto",
					paddingBottom: "60px",
					boxShadow: "0 -8px 40px rgba(0,0,0,0.15)",
				}}
			>
				{/* Header Image Area — gradient with depth */}
				<div
					className="animate-fadeIn"
					style={{
						height: "240px",
						background: `linear-gradient(155deg, ${statusColor.bg}, ${statusColor.bg}dd, color-mix(in srgb, ${statusColor.bg} 80%, var(--color-bg-card)))`,
						position: "relative",
						display: "flex",
						alignItems: "flex-end",
						padding: "28px 24px",
						borderBottom:
							"1px solid color-mix(in srgb, var(--color-surface-stroke) 40%, transparent)",
					}}
				>
					<button
						type="button"
						onClick={onClose}
						disabled={isDetailBusy}
						aria-busy={isDetailBusy}
						aria-label={closeButtonLabel}
						title={closeButtonLabel}
						className="btn btn-icon animate-scaleIn"
						style={{
							position: "absolute",
							top: "20px",
							left: "20px",
							background: "var(--color-bg-card)",
							boxShadow: "var(--shadow-md)",
						}}
					>
						<BackIcon />
					</button>
					<div style={{ width: "100%" }}>
						<div
							style={{
								display: "flex",
								justifyContent: "space-between",
								alignItems: "flex-end",
							}}
						>
							<div className="animate-fadeInUp">
								<div
									id="cattle-detail-title"
									style={{
										fontSize: "38px",
										fontWeight: 800,
										marginBottom: "8px",
										color: statusColor.text,
										fontFamily: "var(--font-display)",
										letterSpacing: "-0.02em",
										lineHeight: 1,
									}}
								>
									{cattle.name}
								</div>
								<div
									style={{
										fontSize: "15px",
										opacity: 0.8,
										fontWeight: 600,
										color: statusColor.text,
										letterSpacing: "0.02em",
									}}
								>
									{cattle.tagNumber}
								</div>
							</div>
							<div
								className="animate-fadeInUp"
								style={{
									background: "var(--color-bg-card)",
									padding: "8px 16px",
									borderRadius: "var(--radius-full)",
									fontSize: "13px",
									fontWeight: 700,
									color: statusColor.text,
									boxShadow: "var(--shadow-sm)",
									animationDelay: "100ms",
								}}
							>
								{cattle.gender} · {cattle.status} · {monthAge}개월
							</div>
						</div>
					</div>
				</div>

				<div style={{ padding: "24px" }}>
					{/* Quick Actions */}
					<div
						className="animate-fadeInUp"
						style={{
							display: "flex",
							gap: "12px",
							marginBottom: "28px",
							animationDelay: "100ms",
						}}
					>
						<button
							type="button"
							onClick={onEdit}
							aria-label={editButtonLabel}
							title={editButtonLabel}
							disabled={isDetailBusy}
							aria-busy={isDetailBusy}
							className="btn btn-secondary"
							style={{
								...btnSecondary,
								flex: 1,
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								gap: "8px",
							}}
						>
							<EditIcon /> {editButtonText}
						</button>
						<button
							type="button"
							onClick={onDelete}
							aria-label={archiveButtonLabel}
							title={archiveButtonLabel}
							disabled={isDetailBusy}
							aria-busy={isDetailBusy}
							className="btn btn-danger"
							style={{
								...btnDanger,
								flex: 1,
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								gap: "8px",
							}}
						>
							<TrashIcon /> {archiveButtonText}
						</button>
					</div>

					{/* Basic Info */}
					<div
						className="animate-fadeInUp"
						style={{ marginBottom: "28px", animationDelay: "150ms" }}
					>
						<SectionTitle icon="📋" title="기본 정보" />
						<div
							style={{
								display: "grid",
								gridTemplateColumns: "1fr 1fr",
								gap: "14px",
							}}
						>
							<InfoItem
								label="위치"
								value={`${buildingName} ${cattle.penNumber}번 칸`}
								delay={0}
							/>
							<InfoItem
								label="생년월일"
								value={formatDate(cattle.birthDate)}
								delay={50}
							/>
							<InfoItem
								label="현재체중"
								value={`${cattle.weight} kg`}
								highlight
								delay={100}
							/>
							<InfoItem
								label="유전능력"
								value={`부:${cattle.geneticInfo?.father || "부계 미등록"} / 모:${cattle.geneticInfo?.mother || "모계 미등록"}`}
								delay={150}
							/>
							{cattle.purchasePrice && (
								<InfoItem
									label="구입가격"
									value={`${formatMoney(cattle.purchasePrice)}원`}
									delay={200}
								/>
							)}
							{cattle.purchaseDate && (
								<InfoItem
									label="구입일자"
									value={formatDate(cattle.purchaseDate)}
									delay={250}
								/>
							)}
						</div>
					</div>

					{/* Reproduction Management */}
					{(cattle.status === "번식우" ||
						cattle.status === "임신우" ||
						cattle.gender === "암") && (
						<div
							className="animate-fadeInUp"
							style={{
								marginBottom: "28px",
								background:
									"linear-gradient(135deg, color-mix(in srgb, var(--color-warning-light) 78%, var(--color-surface-elevated)), var(--color-warning-light))",
								borderRadius: "var(--radius-lg)",
								padding: "20px",
								animationDelay: "200ms",
							}}
						>
							<SectionTitle
								icon="❤️"
								title="번식 관리"
								color="var(--color-warning)"
							/>
							<div
								style={{
									display: "grid",
									gridTemplateColumns: "1fr 1fr",
									gap: "14px",
									marginBottom: "16px",
								}}
							>
								<InfoItem
									label="최근 발정"
									value={
										cattle.lastEstrus
											? formatDate(cattle.lastEstrus)
											: "발정일 미등록"
									}
								/>
								<InfoItem
									label="다음 발정 예정"
									value={
										cattle.lastEstrus
											? formatDaysLeftLabel(
													getDaysUntilEstrus(cattle.lastEstrus),
												)
											: "최근 발정일 미등록"
									}
								/>
								<InfoItem
									label="수정일(임신)"
									value={
										cattle.pregnancyDate
											? formatDate(cattle.pregnancyDate)
											: "수정일 미등록"
									}
								/>
								<InfoItem
									label="분만 예정일"
									value={
										cattle.pregnancyDate
											? formatDate(getCalvingDate(cattle.pregnancyDate))
											: "분만 예정일 미등록"
									}
								/>
							</div>
							<div style={{ display: "flex", gap: "10px" }}>
								<button
									type="button"
									onClick={() => openBreedingForm("estrus")}
									disabled={isDetailBusy}
									aria-busy={isDetailBusy}
									aria-label={estrusButtonLabel}
									title={estrusButtonLabel}
									className="btn"
									style={{
										...btnPrimary,
										padding: "12px 16px",
										fontSize: "13px",
										background:
											"linear-gradient(135deg, var(--color-warning), color-mix(in srgb, var(--color-warning) 78%, #9b6e40 22%))",
										flex: 1,
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
										gap: "8px",
									}}
								>
									<CalendarCheck2 size={16} aria-hidden="true" /> {estrusButtonText}
								</button>
								<button
									type="button"
									onClick={() => openBreedingForm("pregnancy")}
									disabled={isDetailBusy}
									aria-busy={isDetailBusy}
									aria-label={pregnancyButtonLabel}
									title={pregnancyButtonLabel}
									className="btn"
									style={{
										...btnPrimary,
										padding: "12px 16px",
										fontSize: "13px",
										background:
											"linear-gradient(135deg, var(--color-primary-custom), var(--color-primary-dark))",
										flex: 1,
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
										gap: "8px",
									}}
								>
									<CheckCircle2 size={16} aria-hidden="true" /> {pregnancyButtonText}
								</button>
							</div>
							{activeBreedingAction ? (
								<form
									onSubmit={handleSaveBreedingRecord}
									style={{
										marginTop: "14px",
										background: "var(--color-bg-card)",
										border:
											"1px solid color-mix(in srgb, var(--color-warning) 28%, var(--color-border-custom))",
										borderRadius: "var(--radius-md)",
										padding: "14px",
										boxShadow: "var(--shadow-sm)",
									}}
								>
									<label
										htmlFor="breeding-record-date"
										style={{
											display: "block",
											fontSize: "12px",
											fontWeight: 800,
											color: "var(--color-text-secondary)",
											marginBottom: "8px",
										}}
									>
										{activeBreedingAction === "pregnancy"
											? "수정일"
											: "발정 관찰일"}
									</label>
									<div
										style={{
											display: "flex",
											gap: "10px",
											alignItems: "center",
											flexWrap: "wrap",
										}}
									>
										<input
											id="breeding-record-date"
											type="date"
											className="input"
											value={breedingDate}
											onChange={(event) => {
												setBreedingDate(event.target.value);
												setBreedingError("");
											}}
											aria-required="true"
								aria-invalid={Boolean(breedingError)}
											aria-describedby={
												breedingError ? breedingDateErrorId : undefined
											}
											style={{
												flex: "1 1 170px",
												minHeight: "42px",
												border: "1px solid var(--color-border)",
												borderRadius: "var(--radius-md)",
												padding: "0 12px",
												background: "var(--color-surface-elevated)",
												color: "var(--color-text)",
												fontWeight: 700,
											}}
										/>
										<button
											type="button"
											className="btn btn-secondary"
											onClick={() => setActiveBreedingAction(null)}
											disabled={isBreedingSaving}
											aria-busy={isBreedingSaving}
											aria-label={breedingCancelButtonLabel}
											title={breedingCancelButtonLabel}
											style={{
												...btnSecondary,
												padding: "10px 14px",
												fontSize: "13px",
											}}
										>
											{breedingCancelButtonText}
										</button>
										<button
											type="submit"
											className="btn btn-primary"
											disabled={isBreedingSaving}
											aria-busy={isBreedingSaving}
											aria-label={breedingSubmitButtonLabel}
											title={breedingSubmitButtonLabel}
											style={{
												...btnPrimary,
												padding: "10px 14px",
												fontSize: "13px",
											}}
										>
											{breedingSubmitButtonText}
										</button>
									</div>
									{breedingError ? (
										<div
											id={breedingDateErrorId}
											role="alert"
											style={{
												fontSize: "12px",
												fontWeight: 700,
												color: "var(--color-danger)",
												marginTop: "8px",
											}}
										>
											{breedingError}
										</div>
									) : null}
								</form>
							) : null}
						</div>
					)}

					{/* Weight Chart */}
					<div
						className="animate-fadeInUp"
						style={{ marginBottom: "28px", animationDelay: "250ms" }}
					>
						<SectionTitle icon="📈" title="체중 변화" />
						<div
							role="img"
							aria-label={weightChartLabel}
							title={weightChartLabel}
							style={{
								height: "220px",
								background: "var(--color-border-light)",
								borderRadius: "var(--radius-lg)",
								padding: "16px",
							}}
						>
							<ResponsiveContainer
								width="100%"
								height="100%"
								minWidth={0}
								minHeight={0}
								initialDimension={{ width: 1, height: 1 }}
							>
								<LineChart data={weightChartData}>
									<XAxis
										dataKey="date"
										tick={{ fontSize: 11 }}
										tickFormatter={(v) => v.substring(5)}
										stroke="#999"
									/>
									<YAxis
										domain={["auto", "auto"]}
										width={35}
										tick={{ fontSize: 11 }}
										stroke="#999"
									/>
									<Tooltip
										contentStyle={{
											background: "var(--color-bg-card)",
											border: "none",
											borderRadius: "8px",
											boxShadow: "var(--shadow-md)",
										}}
									/>
									<Line
										type="monotone"
										dataKey="weight"
										stroke="var(--color-primary)"
										strokeWidth={3}
										dot={{ r: 4, fill: "var(--color-primary)" }}
									/>
								</LineChart>
							</ResponsiveContainer>
						</div>
					</div>

					{/* History Timeline */}
					{history.length > 0 && (
						<div
							className="animate-fadeInUp"
							style={{ marginBottom: "28px", animationDelay: "280ms" }}
						>
							<SectionTitle icon="📜" title="이력 타임라인" />
							<div
								role="list"
							style={{ display: "flex", flexDirection: "column", gap: "0" }}
							>
								{history.map((h, idx) => (
									<div
										key={h.id}
										role="listitem"
										style={{
											display: "flex",
											gap: "12px",
											position: "relative",
										}}
									>
										{/* Timeline line */}
										{idx < history.length - 1 && (
											<div
												style={{
													position: "absolute",
													left: "15px",
													top: "32px",
													bottom: "-8px",
													width: "2px",
													background: "var(--color-border)",
												}}
											/>
										)}
										{/* Icon — elevated with subtle shadow */}
										<div
											aria-hidden="true"
											style={{
												width: "34px",
												height: "34px",
												borderRadius: "50%",
												background: "var(--color-surface-elevated)",
												border: "1px solid var(--color-surface-stroke)",
												display: "flex",
												alignItems: "center",
												justifyContent: "center",
												fontSize: "16px",
												flexShrink: 0,
												zIndex: 1,
												boxShadow: "var(--shadow-sm)",
												transition: "transform 0.2s ease",
											}}
										>
											{HISTORY_ICONS[h.eventType] || "📌"}
										</div>
										{/* Content */}
										<div style={{ paddingBottom: "18px", flex: 1 }}>
											<div
												style={{
													fontSize: "13px",
													fontWeight: 700,
													color: "var(--color-text)",
													letterSpacing: "-0.01em",
												}}
											>
												{h.description || h.eventType}
											</div>
											<div
												style={{
													fontSize: "11px",
													color: "var(--color-text-muted)",
													marginTop: "3px",
												}}
											>
												{formatDate(h.eventDate)}
											</div>
										</div>
									</div>
								))}
							</div>
						</div>
					)}

					{/* Memo */}
					<div
						className="animate-fadeInUp"
						style={{ marginBottom: "28px", animationDelay: "300ms" }}
					>
						<SectionTitle icon="📝" title="메모" />
						<div
							style={{
								background: "var(--color-border-light)",
								borderRadius: "var(--radius-md)",
								padding: "18px",
								fontSize: "14px",
								lineHeight: "1.7",
								color: "var(--color-text-secondary)",
								minHeight: "90px",
							}}
						>
							{cattle.memo || "등록된 메모가 없습니다."}
						</div>
					</div>

					{/* QR Code */}
					<div className="animate-fadeInUp" style={{ animationDelay: "350ms" }}>
						<SectionTitle icon="📱" title="개체 식별 QR" />
						<div
							style={{
								background: "var(--color-border-light)",
								borderRadius: "var(--radius-md)",
								padding: "20px",
								display: "flex",
								justifyContent: "center",
							}}
						>
							<QRCodeWidget
								value={`https://joolife.kr/cattle/${cattle.id}`}
								label={`${cattle.name} (${cattle.tagNumber})`}
							/>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}

function SectionTitle({ icon, title, color = "var(--color-text)" }) {
	return (
		<div
			role="heading"
			aria-level={3}
			style={{
				fontSize: "16px",
				fontWeight: 800,
				marginBottom: "16px",
				paddingBottom: "10px",
				borderBottom:
					"1px solid color-mix(in srgb, var(--color-border-custom) 35%, transparent)",
				color,
				display: "flex",
				alignItems: "center",
				gap: "10px",
				letterSpacing: "-0.01em",
			}}
		>
			<span aria-hidden="true" style={{ fontSize: "18px", lineHeight: 1 }}>
				{icon}
			</span>{" "}
			{title}
		</div>
	);
}

function InfoItem({ label, value, highlight = false, delay = 0 }) {
	return (
		<div
			className="animate-fadeInUp"
			style={{
				background: "var(--color-bg-card)",
				border: "1px solid var(--color-border)",
				borderRadius: "var(--radius-md)",
				padding: "14px 16px",
				transition: "all 0.25s cubic-bezier(0.22,1,0.36,1)",
				animationDelay: `${delay}ms`,
				cursor: "default",
			}}
			onMouseEnter={(e) => {
				e.currentTarget.style.transform = "translateY(-2px)";
				e.currentTarget.style.boxShadow = "var(--shadow-sm)";
			}}
			onMouseLeave={(e) => {
				e.currentTarget.style.transform = "translateY(0)";
				e.currentTarget.style.boxShadow = "none";
			}}
		>
			<div
				style={{
					fontSize: "11px",
					color: "var(--color-text-muted)",
					marginBottom: "5px",
					fontWeight: 600,
					letterSpacing: "0.03em",
					textTransform: "uppercase",
				}}
			>
				{label}
			</div>
			<div
				style={{
					fontSize: highlight ? "20px" : "14px",
					fontWeight: highlight ? 800 : 700,
					color: "var(--color-text)",
					fontFamily: highlight ? "var(--font-display)" : "inherit",
					letterSpacing: highlight ? "-0.02em" : "0",
				}}
			>
				{value}
			</div>
		</div>
	);
}
