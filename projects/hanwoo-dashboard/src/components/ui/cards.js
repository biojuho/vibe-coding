import { STATUS_COLORS } from "@/lib/constants";
import {
	getDaysUntilCalving,
	getDaysUntilEstrus,
	getMonthAge,
	isCalvingAlert,
	isEstrusAlert,
} from "@/lib/utils";
import { HeartIcon } from "./common";

function normalizeCardComponentOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export function StatCard(options = {}) {
	const { label, value, sub, color, delay = 0 } =
		normalizeCardComponentOptions(options);

	return (
		<div
			className="stat-card animate-fadeInUp"
			style={{
				"--stat-color": color,
				flex: "1 1 140px",
				minWidth: "140px",
				animationDelay: `${delay}ms`,
				scrollSnapAlign: "start",
			}}
		>
			<div
				style={{
					fontSize: "12px",
					color: "var(--color-text-muted)",
					marginBottom: "6px",
					fontWeight: 600,
					letterSpacing: "0.03em",
					textTransform: "uppercase",
				}}
			>
				{label}
			</div>
			<div className="stat-value">{value}</div>
			{sub && (
				<div
					style={{
						fontSize: "12px",
						color: "var(--color-text-secondary)",
						marginTop: "6px",
						lineHeight: "1.4",
					}}
				>
					{sub}
				</div>
			)}
		</div>
	);
}

function normalizePenCattle(cattle) {
	return Array.isArray(cattle)
		? cattle
				.filter((cow) => cow && typeof cow === "object" && !Array.isArray(cow))
				.map((cow, index) => ({
					...cow,
					id: cow.id ?? `pen-cattle-${index}`,
					name:
						typeof cow.name === "string" && cow.name.trim()
							? cow.name
							: "개체명 미등록",
				}))
		: [];
}

function normalizeDroppedCattleData(value) {
	if (!value || typeof value !== "object" || Array.isArray(value)) {
		return null;
	}

	const cattleId = value.cattleId;
	if (typeof cattleId === "string" && cattleId.trim()) {
		return { cattleId };
	}
	if (typeof cattleId === "number" && Number.isFinite(cattleId)) {
		return { cattleId };
	}

	return null;
}

function normalizeCattleRowCow(cow) {
	const safeCow = cow && typeof cow === "object" && !Array.isArray(cow) ? cow : {};

	return {
		...safeCow,
		id: safeCow.id ?? "cattle-row-unknown",
		name:
			typeof safeCow.name === "string" && safeCow.name.trim()
				? safeCow.name
				: "개체명 미등록",
		status:
			typeof safeCow.status === "string" && safeCow.status.trim()
				? safeCow.status
				: "상태 미등록",
		tagNumber:
			typeof safeCow.tagNumber === "string" && safeCow.tagNumber.trim()
				? safeCow.tagNumber
				: "이표번호 미등록",
		weight:
			safeCow.weight !== null && safeCow.weight !== undefined && safeCow.weight !== ""
				? safeCow.weight
				: "체중 미등록",
		geneticInfo:
			safeCow.geneticInfo &&
			typeof safeCow.geneticInfo === "object" &&
			!Array.isArray(safeCow.geneticInfo)
				? safeCow.geneticInfo
				: {},
	};
}

export function PenCard(options = {}) {
	const {
		penNumber,
		cattle,
		buildingId,
		onSelect,
		delay = 0,
		onDrop,
	} = normalizeCardComponentOptions(options);
	const visibleCattle = normalizePenCattle(cattle);
	const handleSelect =
		typeof onSelect === "function" ? onSelect : () => undefined;
	const handleMoveCattle =
		typeof onDrop === "function" ? onDrop : () => undefined;
	const hasAlert = visibleCattle.some(
		(c) => c.lastEstrus && isEstrusAlert(c.lastEstrus),
	);
	const isEmpty = visibleCattle.length === 0;
	const penAlertLabel = hasAlert ? ", 발정 알림 있음" : "";
	const penAccessibleLabel = `${penNumber}번 칸 상세 보기, ${visibleCattle.length}두 배치됨${penAlertLabel}`;

	const handleDragOver = (e) => {
		e.preventDefault();
		e.currentTarget.classList.add("pen-drop-hover");
	};
	const handleDragLeave = (e) => {
		e.currentTarget.classList.remove("pen-drop-hover");
	};
	const handleDrop = (e) => {
		e.preventDefault();
		e.currentTarget.classList.remove("pen-drop-hover");
		if (typeof onDrop === "function") {
			try {
				const data = normalizeDroppedCattleData(
					JSON.parse(e.dataTransfer.getData("text/plain")),
				);
				if (data) {
					handleMoveCattle(data.cattleId, buildingId, penNumber);
				}
			} catch {}
		}
	};

	return (
		<button
			type="button"
			onClick={() => handleSelect(buildingId, penNumber)}
			aria-label={penAccessibleLabel}
			title={penAccessibleLabel}
			onDragOver={handleDragOver}
			onDragLeave={handleDragLeave}
			onDrop={handleDrop}
			className={`pen-card animate-fadeInUp ${isEmpty ? "empty" : ""} ${hasAlert ? "alert" : ""}`}
			style={{ animationDelay: `${delay}ms` }}
		>
			{hasAlert && (
				<div className="pen-alert-badge" aria-hidden="true">
					❤️
				</div>
			)}
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
					marginBottom: "8px",
				}}
			>
				<span
					style={{
						fontFamily: "var(--font-display)",
						fontWeight: 700,
						fontSize: "14px",
						color: isEmpty
							? "var(--color-text-muted)"
							: "var(--color-primary-light)",
					}}
				>
					#{penNumber}
				</span>
				<span
					style={{
						fontSize: "11px",
						background: isEmpty
							? "var(--color-border)"
							: "var(--color-border-light)",
						padding: "3px 8px",
						borderRadius: "8px",
						color: isEmpty
							? "var(--color-text-muted)"
							: "var(--color-text-secondary)",
						fontWeight: 500,
					}}
				>
					{visibleCattle.length}/5
				</span>
			</div>
			{isEmpty ? (
				<div
					style={{
						color: "var(--color-text-muted)",
						fontSize: "12px",
						textAlign: "center",
						paddingTop: "8px",
					}}
				>
					비어있음
				</div>
			) : (
				<div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
					{visibleCattle.map((c, idx) => {
						const sc = STATUS_COLORS[c.status] || { dot: "#888" };
						const al = c.lastEstrus && isEstrusAlert(c.lastEstrus);
						const penCowPreviewLabel = al
							? `${c.name} 발정 알림 있음`
							: `${c.name} 칸 배치됨`;
						return (
							<div
								key={c.id}
								title={penCowPreviewLabel}
								className="animate-scaleIn"
								style={{
									width: "28px",
									height: "28px",
									borderRadius: "50%",
									background: al
										? "linear-gradient(135deg,#FF1744,#D50000)"
										: `linear-gradient(135deg,${sc.dot},${sc.dot}dd)`,
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									color: "white",
									fontSize: "10px",
									fontWeight: 700,
									boxShadow: al
										? "0 2px 10px rgba(255,23,68,0.45)"
										: "0 2px 8px rgba(0,0,0,0.15)",
									animationDelay: `${delay + idx * 30}ms`,
									transition:
										"transform 0.25s cubic-bezier(0.22,1,0.36,1), box-shadow 0.25s ease",
									cursor: "pointer",
								}}
								onMouseEnter={(e) => {
									e.currentTarget.style.transform = "scale(1.18)";
									e.currentTarget.style.boxShadow = al
										? "0 4px 14px rgba(255,23,68,0.55)"
										: `0 4px 14px ${sc.dot}55`;
								}}
								onMouseLeave={(e) => {
									e.currentTarget.style.transform = "scale(1)";
									e.currentTarget.style.boxShadow = al
										? "0 2px 10px rgba(255,23,68,0.45)"
										: "0 2px 8px rgba(0,0,0,0.15)";
								}}
							>
								{c.gender === "암" ? "♀" : "♂"}
							</div>
						);
					})}
				</div>
			)}
		</button>
	);
}

export function CattleRow(options = {}) {
	const { cow, onClick, delay = 0, draggable = false } =
		normalizeCardComponentOptions(options);
	const safeCow = normalizeCattleRowCow(cow);
	const handleClick =
		typeof onClick === "function" ? onClick : () => undefined;
	const sc = STATUS_COLORS[safeCow.status] || {
		bg: "var(--color-border-light)",
		text: "var(--color-text)",
		dot: "var(--color-text-muted)",
	};
	const hasEstrusAlert =
		safeCow.lastEstrus && isEstrusAlert(safeCow.lastEstrus);
	const estrusD = getDaysUntilEstrus(safeCow.lastEstrus);
	const monthAge = getMonthAge(safeCow.birthDate);
	const hasCalvingAlert =
		safeCow.status === "임신우" &&
		safeCow.pregnancyDate &&
		isCalvingAlert(safeCow.pregnancyDate);
	const calvingDays = getDaysUntilCalving(safeCow.pregnancyDate);
	const cattleAlertSummary = [
		hasEstrusAlert
			? estrusD === 0
				? "오늘 발정 알림"
				: `발정 ${estrusD}일 전 알림`
			: null,
		hasCalvingAlert ? `분만 ${calvingDays}일 전 알림` : null,
	]
		.filter(Boolean)
		.join(", ");
	const cattleAccessibleLabel = cattleAlertSummary
		? `${safeCow.name} 개체 상세 보기, ${cattleAlertSummary}`
		: `${safeCow.name} 개체 상세 보기`;
	const geneticGradeLabel =
		typeof safeCow.geneticInfo?.grade === "string" &&
		safeCow.geneticInfo.grade.trim() &&
		safeCow.geneticInfo.grade !== "-"
			? safeCow.geneticInfo.grade
			: "유전 등급 미등록";
	const weightLabel =
		safeCow.weight === "체중 미등록" ? safeCow.weight : `${safeCow.weight}kg`;

	const handleDragStart = (e) => {
		e.dataTransfer.setData(
			"text/plain",
			JSON.stringify({ cattleId: safeCow.id, name: safeCow.name }),
		);
		e.dataTransfer.effectAllowed = "move";
		e.currentTarget.classList.add("cattle-dragging");
	};
	const handleDragEnd = (e) => {
		e.currentTarget.classList.remove("cattle-dragging");
	};

	return (
		<button
			type="button"
			onClick={() => handleClick(safeCow)}
			aria-label={cattleAccessibleLabel}
			title={cattleAccessibleLabel}
			draggable={draggable}
			onDragStart={draggable ? handleDragStart : undefined}
			onDragEnd={draggable ? handleDragEnd : undefined}
			className={`cattle-row animate-fadeInUp ${hasEstrusAlert ? "estrus-alert" : ""} ${hasCalvingAlert ? "calving-alert" : ""}`}
			style={{
				animationDelay: `${delay}ms`,
				cursor: draggable ? "grab" : "pointer",
			}}
		>
			<div
				className="cattle-avatar"
				style={{
					background: `linear-gradient(135deg,${sc.dot},${sc.dot}cc)`,
					boxShadow: `0 4px 12px ${sc.dot}40`,
				}}
			>
				{safeCow.gender === "암" ? "♀" : "♂"}
			</div>
			<div style={{ flex: 1, minWidth: 0 }}>
				<div
					style={{
						display: "flex",
						alignItems: "center",
						gap: "6px",
						flexWrap: "wrap",
						marginBottom: "5px",
					}}
				>
					<span
						style={{
							fontWeight: 700,
							fontSize: "15px",
							color: "var(--color-text)",
							letterSpacing: "-0.01em",
						}}
					>
						{safeCow.name}
					</span>
					<span className="badge" style={{ background: sc.bg, color: sc.text }}>
						{safeCow.status}
					</span>
					{hasEstrusAlert && (
						<span
							className="badge badge-estrus"
							style={{
								animation: estrusD === 0 ? "shake 0.5s ease-in-out" : "none",
							}}
						>
							{estrusD === 0 ? "발정 오늘" : `발정 ${estrusD}일 남음`}
						</span>
					)}
					{hasCalvingAlert && (
						<span className="badge badge-calving">
							분만 {calvingDays}일 남음
						</span>
					)}
				</div>
				<div
					style={{
						fontSize: "12px",
						color: "var(--color-text-secondary)",
						lineHeight: "1.5",
					}}
				>
					{safeCow.tagNumber} · {monthAge}개월 · {weightLabel} ·{" "}
					{geneticGradeLabel}
				</div>
			</div>
			{/* Animated chevron — slides right on row hover */}
			<div className="cattle-chevron" aria-hidden="true">
				›
			</div>
		</button>
	);
}
