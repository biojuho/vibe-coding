"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import {
	CartesianGrid,
	Legend,
	Line,
	LineChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";

import { useAppFeedback } from "@/components/feedback/FeedbackProvider";
import { PremiumButton } from "@/components/ui/premium-button";
import {
	PremiumInput,
	PremiumLabel,
	PremiumTextarea,
} from "@/components/ui/premium-input";
import { BREED_STATUS_OPTIONS } from "@/lib/constants";
import { createFeedRecordValues, feedRecordSchema } from "@/lib/formSchemas";
import { toFiniteNumber } from "@/lib/utils";

const errorTextStyle = {
	fontSize: "12px",
	marginTop: "6px",
	color: "var(--color-danger)",
	fontWeight: 600,
};

function normalizeFeedHelperOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function FilterChip(options = {}) {
	const {
		active,
		children,
		onClick,
		label,
		disabled = false,
	} = normalizeFeedHelperOptions(options);
	const safeOnClick = typeof onClick === "function" ? onClick : undefined;
	const actionLabel = disabled
		? `${label} - 급여 기록 저장 중에는 변경할 수 없습니다`
		: label;
	const chipText = disabled ? "급여 기록 저장 중..." : children;

	return (
		<PremiumButton
			variant={active ? "primary" : "secondary"}
			size="sm"
			onClick={safeOnClick}
			disabled={disabled}
			aria-busy={disabled}
			aria-pressed={active}
			aria-label={actionLabel}
			title={actionLabel}
			className={`rounded-full px-4 py-2 font-bold text-[13px] whitespace-nowrap shadow-sm ${active ? "shadow-[var(--shadow-button-primary)] text-white" : ""}`}
		>
			{chipText}
		</PremiumButton>
	);
}

function toValidFeedDate(value) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	if (Number.isNaN(date.getTime())) {
		return null;
	}

	if (typeof value === "string") {
		const dateKey = value.trim().slice(0, 10);
		if (
			/^\d{4}-\d{2}-\d{2}$/.test(dateKey) &&
			date.toISOString().slice(0, 10) !== dateKey
		) {
			return null;
		}
	}

	return date;
}

function getFeedDateTime(value) {
	return toValidFeedDate(value)?.getTime() ?? Number.NEGATIVE_INFINITY;
}

function formatFeedDateLabel(value, options) {
	const date = toValidFeedDate(value);
	return date ? date.toLocaleDateString("ko-KR", options) : "날짜 미등록";
}

function normalizeFeedItems(items) {
	return Array.isArray(items)
		? items.filter(
				(item) => item && typeof item === "object" && !Array.isArray(item),
			)
		: [];
}

function normalizeFeedBuildings(buildings) {
	return normalizeFeedItems(buildings).map((building, index) => ({
		...building,
		id: building.id ?? `feed-building-${index}`,
		name:
			typeof building.name === "string" && building.name.trim()
				? building.name
				: "축사 이름 미등록",
	}));
}

function normalizeFeedTabOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export default function FeedTab(options = {}) {
	const {
		cattle,
		feedStandards = [],
		feedHistory = [],
		onRecordFeed,
		buildings = [],
	} = normalizeFeedTabOptions(options);
	const [selectedBuilding, setSelectedBuilding] = useState(null);
	const [isSaving, setIsSaving] = useState(false);
	const isMountedRef = useRef(false);
	const saveInFlightRef = useRef(false);
	const { notify } = useAppFeedback();
	const handleRecordFeed =
		typeof onRecordFeed === "function" ? onRecordFeed : async () => false;
	const submitButtonLabel = isSaving
		? "급여 기록 저장 중"
		: "급여 기록 저장";
	const submitButtonText = isSaving
		? "급여 기록 저장 중..."
		: "급여 기록 저장";
	const feedChartLabel =
		"최근 급여 추이 차트. 조사료와 배합사료 급여량을 날짜별로 비교합니다.";

	const {
		register,
		handleSubmit,
		reset,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(feedRecordSchema),
		defaultValues: createFeedRecordValues(),
	});

	const safeCattle = useMemo(() => normalizeFeedItems(cattle), [cattle]);
	const safeFeedStandards = useMemo(
		() => normalizeFeedItems(feedStandards),
		[feedStandards],
	);
	const safeFeedHistory = useMemo(
		() => normalizeFeedItems(feedHistory),
		[feedHistory],
	);
	const safeBuildings = useMemo(
		() => normalizeFeedBuildings(buildings),
		[buildings],
	);

	const standardsMap = useMemo(() => {
		const map = {};
		safeFeedStandards.forEach((standard) => {
			map[standard.status] = standard;
		});
		return map;
	}, [safeFeedStandards]);

	const feedSummary = useMemo(() => {
		const summary = {};

		BREED_STATUS_OPTIONS.forEach((status) => {
			const count = safeCattle.filter((row) => row.status === status).length;
			const standard = standardsMap[status];

			if (count > 0 && standard) {
				summary[status] = {
					count,
					roughageTotal: (toFiniteNumber(standard.roughageKg) * count).toFixed(
						1,
					),
					concentrateTotal: (
						toFiniteNumber(standard.concentrateKg) * count
					).toFixed(1),
				};
			}
		});

		return summary;
	}, [safeCattle, standardsMap]);

	const totalStandardRoughage = Object.values(feedSummary)
		.reduce((sum, value) => sum + toFiniteNumber(value.roughageTotal), 0)
		.toFixed(1);
	const totalStandardConcentrate = Object.values(feedSummary)
		.reduce((sum, value) => sum + toFiniteNumber(value.concentrateTotal), 0)
		.toFixed(1);

	const filteredCattle = useMemo(() => {
		if (!selectedBuilding) {
			return safeCattle;
		}

		return safeCattle.filter((row) => row.buildingId === selectedBuilding);
	}, [safeCattle, selectedBuilding]);

	const chartData = useMemo(() => {
		const grouped = {};
		const sorted = [...safeFeedHistory].sort(
			(first, second) =>
				getFeedDateTime(first.date) - getFeedDateTime(second.date),
		);

		sorted.forEach((record) => {
			const key = formatFeedDateLabel(record.date, {
				month: "short",
				day: "numeric",
			});
			if (!grouped[key]) {
				grouped[key] = { date: key, roughage: 0, concentrate: 0 };
			}
			grouped[key].roughage += toFiniteNumber(record.roughage);
			grouped[key].concentrate += toFiniteNumber(record.concentrate);
		});

		return Object.values(grouped);
	}, [safeFeedHistory]);

	const roughageGuide = selectedBuilding
		? filteredCattle
				.reduce(
					(sum, row) =>
						sum + toFiniteNumber(standardsMap[row.status]?.roughageKg),
					0,
				)
				.toFixed(1)
		: totalStandardRoughage;
	const concentrateGuide = selectedBuilding
		? filteredCattle
				.reduce(
					(sum, row) =>
						sum + toFiniteNumber(standardsMap[row.status]?.concentrateKg),
					0,
				)
				.toFixed(1)
		: totalStandardConcentrate;

	useEffect(() => {
		isMountedRef.current = true;

		return () => {
			isMountedRef.current = false;
			saveInFlightRef.current = false;
		};
	}, []);

	const submitFeedRecord = async (values) => {
		if (saveInFlightRef.current) {
			return;
		}

		if (!selectedBuilding) {
			notify({
				title: "축사를 먼저 선택해 주세요.",
				description: "급여 기록은 특정 축사 기준으로 저장됩니다.",
				variant: "warning",
			});
			return;
		}

		saveInFlightRef.current = true;
		setIsSaving(true);

		try {
			const recorded = await handleRecordFeed({
				...values,
				buildingId: selectedBuilding,
			});

			if (!recorded || !isMountedRef.current) {
				return;
			}

			reset({
				...createFeedRecordValues(),
				date: values.date,
			});
		} finally {
			saveInFlightRef.current = false;
			if (isMountedRef.current) {
				setIsSaving(false);
			}
		}
	};

	const handleFeedSubmit = (event) => {
		void handleSubmit(submitFeedRecord)(event);
	};

	return (
		<div>
			<div className="section-header" style={{ marginBottom: "16px" }}>
				<span className="section-header-icon" aria-hidden="true">
					🌾
				</span>
				<h2 className="section-header-title">사료 급여 모니터링</h2>
			</div>

			<div
				style={{
					display: "flex",
					gap: "8px",
					marginBottom: "12px",
					overflowX: "auto",
					paddingBottom: "4px",
				}}
			>
				<FilterChip
					active={!selectedBuilding}
					onClick={() => setSelectedBuilding(null)}
					label="전체 축사 급여 보기"
					disabled={isSaving}
				>
					전체
				</FilterChip>
				{safeBuildings.map((building) => (
					<FilterChip
						key={building.id}
						active={selectedBuilding === building.id}
						onClick={() => setSelectedBuilding(building.id)}
						label={`${building.name} 급여 보기`}
						disabled={isSaving}
					>
						{building.name}
					</FilterChip>
				))}
			</div>

			<div
				style={{
					background:
						"linear-gradient(145deg, color-mix(in srgb, var(--chart-clay-1) 78%, white 22%), color-mix(in srgb, var(--chart-clay-1) 76%, #5a734f 24%))",
					borderRadius: "24px",
					padding: "18px",
					color: "white",
					marginBottom: "20px",
					boxShadow: "var(--shadow-md)",
				}}
			>
				<div
					style={{
						fontSize: "13px",
						opacity: 0.9,
						marginBottom: "8px",
						display: "flex",
						justifyContent: "space-between",
						gap: "12px",
					}}
				>
					<span>
						오늘 급여 가이드{" "}
						{selectedBuilding
							? `(${safeBuildings.find((row) => row.id === selectedBuilding)?.name})`
							: "(전체)"}
					</span>
					<span>{filteredCattle.length}두</span>
				</div>
				<div style={{ display: "flex", gap: "20px" }}>
					<div>
						<div
							style={{
								fontSize: "24px",
								fontWeight: 800,
								fontFamily: "var(--font-display-custom)",
							}}
						>
							{roughageGuide}kg
						</div>
						<div style={{ fontSize: "11px", opacity: 0.82 }}>조사료 권장량</div>
					</div>
					<div>
						<div
							style={{
								fontSize: "24px",
								fontWeight: 800,
								fontFamily: "var(--font-display-custom)",
							}}
						>
							{concentrateGuide}kg
						</div>
						<div style={{ fontSize: "11px", opacity: 0.82 }}>
							배합사료 권장량
						</div>
					</div>
				</div>
			</div>

			{selectedBuilding ? (
				<form
					onSubmit={handleFeedSubmit}
					style={{
						background: "var(--surface-gradient)",
						borderRadius: "24px",
						padding: "24px",
						marginBottom: "20px",
						border: "1px solid var(--color-surface-stroke)",
						boxShadow: "var(--shadow-md)",
					}}
				>
					<div
						style={{
							fontSize: "16px",
							fontWeight: 700,
							marginBottom: "16px",
							color: "var(--color-text)",
						}}
					>
						오늘 급여 기록
						<span
							style={{
								fontSize: "13px",
								fontWeight: 500,
								color: "var(--color-text-muted)",
								marginLeft: "8px",
							}}
						>
							{safeBuildings.find((row) => row.id === selectedBuilding)?.name}
						</span>
					</div>

					<div style={{ marginBottom: "16px" }}>
						<PremiumLabel htmlFor="feed-date">기록 날짜</PremiumLabel>
						<PremiumInput
							id="feed-date"
							type="date"
							{...register("date")}
							aria-invalid={Boolean(errors.date)}
							aria-describedby={errors.date ? "feed-date-error" : undefined}
							hasError={!!errors.date}
						/>
						{errors.date ? (
							<div id="feed-date-error" role="alert" style={errorTextStyle}>
								{errors.date.message}
							</div>
						) : null}
					</div>

					<div
						style={{
							display: "grid",
							gridTemplateColumns: "1fr 1fr",
							gap: "16px",
							marginBottom: "16px",
						}}
					>
						<Field
							label="조사료"
							suffix="kg"
							error={errors.roughage?.message}
							inputProps={register("roughage")}
						/>
						<Field
							label="배합사료"
							suffix="kg"
							error={errors.concentrate?.message}
							inputProps={register("concentrate")}
						/>
					</div>

					<div style={{ marginBottom: "16px" }}>
						<PremiumLabel htmlFor="feed-note">특이사항 메모</PremiumLabel>
						<PremiumTextarea
							id="feed-note"
							{...register("note")}
							aria-invalid={Boolean(errors.note)}
							aria-describedby={errors.note ? "feed-note-error" : undefined}
							placeholder="사료 상태, 섭취 변화, 축사 메모를 적어 주세요."
							hasError={!!errors.note}
							className="h-[82px]"
						/>
						{errors.note ? (
							<div id="feed-note-error" role="alert" style={errorTextStyle}>
								{errors.note.message}
							</div>
						) : null}
					</div>

					<PremiumButton
						type="submit"
						disabled={isSaving}
						aria-busy={isSaving}
						aria-label={submitButtonLabel}
						title={submitButtonLabel}
						className="w-full py-4 text-lg mt-3 bg-linear-to-b from-blue-500 to-blue-600 border-none shadow-(--shadow-button-primary) font-bold"
						glow={true}
					>
						{submitButtonText}
					</PremiumButton>
				</form>
			) : null}

			<div
				role="img"
				aria-label={feedChartLabel}
				title={feedChartLabel}
				style={{
					background: "var(--surface-gradient)",
					borderRadius: "24px",
					padding: "16px",
					border: "1px solid var(--color-surface-stroke)",
					height: "300px",
					boxShadow: "var(--shadow-sm)",
				}}
			>
				<div
					style={{
						fontSize: "14px",
						fontWeight: 700,
						marginBottom: "16px",
						color: "var(--color-text)",
					}}
				>
					최근 급여 추이
				</div>
				<ResponsiveContainer width="100%" height="100%">
					<LineChart data={chartData}>
						<CartesianGrid
							strokeDasharray="3 3"
							vertical={false}
							stroke="var(--color-border)"
						/>
						<XAxis
							dataKey="date"
							tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
							axisLine={false}
							tickLine={false}
						/>
						<YAxis
							tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
							axisLine={false}
							tickLine={false}
						/>
						<Tooltip
							contentStyle={{
								borderRadius: 18,
								border: "1px solid var(--color-surface-stroke)",
								boxShadow: "var(--shadow-md)",
								background: "var(--surface-gradient)",
							}}
						/>
						<Legend />
						<Line
							type="monotone"
							dataKey="roughage"
							name="조사료"
							stroke="var(--chart-clay-1)"
							strokeWidth={3}
							dot={{ r: 3 }}
							activeDot={{ r: 5 }}
						/>
						<Line
							type="monotone"
							dataKey="concentrate"
							name="배합사료"
							stroke="var(--chart-clay-2)"
							strokeWidth={3}
							dot={{ r: 3 }}
							activeDot={{ r: 5 }}
						/>
					</LineChart>
				</ResponsiveContainer>
			</div>

			<div style={{ marginTop: "20px" }}>
				<div
					style={{
						fontSize: "14px",
						fontWeight: 700,
						marginBottom: "10px",
						color: "var(--color-text)",
					}}
				>
					최근 기록
				</div>
				<div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
					{safeFeedHistory.slice(0, 5).map((record, index) => (
						<div
							key={record.id ?? `feed-record-${index}`}
							style={{
								background: "var(--surface-gradient)",
								borderRadius: "18px",
								padding: "12px 14px",
								border: "1px solid var(--color-surface-stroke)",
								display: "flex",
								justifyContent: "space-between",
								alignItems: "center",
								boxShadow: "var(--shadow-sm)",
							}}
						>
							<div>
								<div
									style={{
										fontSize: "13px",
										fontWeight: 600,
										color: "var(--color-text)",
									}}
								>
									{formatFeedDateLabel(record.date)}
									<span
										style={{
											fontSize: "11px",
											color: "var(--color-text-muted)",
											fontWeight: 400,
											marginLeft: "6px",
										}}
									>
										{
											safeBuildings.find((row) => row.id === record.buildingId)
												?.name
										}
									</span>
								</div>
								{record.note ? (
									<div
										style={{
											fontSize: "11px",
											color: "var(--color-text-muted)",
											marginTop: "2px",
										}}
									>
										{record.note}
									</div>
								) : null}
							</div>
							<div style={{ fontSize: "12px", fontWeight: 700 }}>
								<span style={{ color: "var(--chart-clay-1)" }}>
									조 {record.roughage}
								</span>{" "}
								·{" "}
								<span style={{ color: "var(--chart-clay-2)" }}>
									배 {record.concentrate}
								</span>
							</div>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}

function Field(options = {}) {
	const { label, suffix, error, inputProps } =
		normalizeFeedHelperOptions(options);
	const safeInputProps = normalizeFeedHelperOptions(inputProps);
	const inputName =
		typeof safeInputProps.name === "string" && safeInputProps.name.trim()
			? safeInputProps.name
			: "field";
	const fieldId = `feed-${inputName}`;
	const errorId = `${fieldId}-error`;

	return (
		<div style={{ position: "relative" }}>
			<PremiumLabel htmlFor={fieldId}>{label}</PremiumLabel>
			<div style={{ position: "relative" }}>
				<PremiumInput
					id={fieldId}
					type="number"
					placeholder="0.0"
					{...safeInputProps}
					aria-invalid={Boolean(error)}
					aria-describedby={error ? errorId : undefined}
					hasError={!!error}
					className="text-[16px] font-bold font-['var(--font-display-custom)']"
				/>
				<span
					style={{
						position: "absolute",
						right: "14px",
						top: "50%",
						transform: "translateY(-50%)",
						fontSize: "12px",
						color: "var(--color-text-muted)",
						fontWeight: 600,
					}}
				>
					{suffix}
				</span>
			</div>
			{error ? (
				<div id={errorId} role="alert" style={errorTextStyle}>
					{error}
				</div>
			) : null}
		</div>
	);
}
