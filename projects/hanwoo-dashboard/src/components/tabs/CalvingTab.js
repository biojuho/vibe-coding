"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ClipboardPlus } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";

import { useAppFeedback } from "@/components/feedback/FeedbackProvider";
import { btnPrimary, inputStyle } from "@/components/ui/common";
import EmptyState from "@/components/ui/empty-state";
import {
	calvingRecordSchema,
	createCalvingFormValues,
} from "@/lib/formSchemas";
import {
	formatDate,
	getCalvingDate,
	getDaysUntilCalving,
	isCalvingAlert,
} from "@/lib/utils";

const errorTextStyle = {
	fontSize: "12px",
	marginTop: "6px",
	color: "var(--color-danger)",
	fontWeight: 600,
};

function getPregnancyDateTime(value) {
	if (value == null) return Number.POSITIVE_INFINITY;
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime())
		? Number.POSITIVE_INFINITY
		: date.getTime();
}

function normalizeCalvingCattle(cattle) {
	return Array.isArray(cattle)
		? cattle.filter(
				(row) =>
					row && typeof row === "object" && !Array.isArray(row) && row.id != null,
			)
		: [];
}

function normalizeCalvingBuildings(buildings) {
	return Array.isArray(buildings)
		? buildings.filter(
				(building) =>
					building && typeof building === "object" && !Array.isArray(building),
			)
		: [];
}

function normalizeCalvingTabOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export default function CalvingTab(options = {}) {
	const { cattle, buildings = [], onRecordCalving, onOpenCattleRegistration } =
		normalizeCalvingTabOptions(options);
	const handleRecordCalving =
		typeof onRecordCalving === "function" ? onRecordCalving : async () => false;
	const handleOpenCattleRegistration =
		typeof onOpenCattleRegistration === "function"
			? onOpenCattleRegistration
			: null;
	const safeCattle = useMemo(() => normalizeCalvingCattle(cattle), [cattle]);
	const safeBuildings = useMemo(
		() => normalizeCalvingBuildings(buildings),
		[buildings],
	);
	const pregnantCows = useMemo(
		() =>
			safeCattle
				.filter((row) => row.status === "임신우")
				.sort((first, second) => {
					const diff =
						getPregnancyDateTime(first.pregnancyDate) -
						getPregnancyDateTime(second.pregnancyDate);
					return Number.isNaN(diff) ? 0 : diff;
				}),
		[safeCattle],
	);
	const calvingAlertCount = useMemo(
		() => pregnantCows.filter((cow) => isCalvingAlert(cow.pregnancyDate)).length,
		[pregnantCows],
	);
	const thisYearCalvingCount = useMemo(() => {
		const thisYear = new Date().getFullYear();
		return safeCattle.filter((row) => {
			if (row.status !== "송아지") return false;
			if (!row.birthDate) return false;
			const date = new Date(row.birthDate);
			return !Number.isNaN(date.getTime()) && date.getFullYear() === thisYear;
		}).length;
	}, [safeCattle]);

	const [selectedCowId, setSelectedCowId] = useState(null);
	const [isSaving, setIsSaving] = useState(false);
	const isMountedRef = useRef(false);
	const saveInFlightRef = useRef(false);
	const { notify } = useAppFeedback();
	const submitButtonLabel = isSaving
		? "분만 기록 저장 중"
		: "분만 완료 및 송아지 등록";
	const submitButtonText = isSaving
		? "분만 기록 저장 중..."
		: "분만 완료 및 송아지 등록";
	const cancelButtonLabel = isSaving
		? "분만 기록 저장 중에는 취소할 수 없습니다"
		: "분만 기록 취소";
	const cancelButtonText = isSaving ? "분만 기록 저장 중..." : "분만 기록 취소";

	const {
		register,
		handleSubmit,
		reset,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(calvingRecordSchema),
		defaultValues: createCalvingFormValues(),
	});

	useEffect(() => {
		isMountedRef.current = true;

		return () => {
			isMountedRef.current = false;
			saveInFlightRef.current = false;
		};
	}, []);

	const closeCalvingForm = () => {
		saveInFlightRef.current = false;
		setIsSaving(false);
		setSelectedCowId(null);
		reset(createCalvingFormValues());
	};

	const openCalvingForm = (cowId) => {
		saveInFlightRef.current = false;
		setIsSaving(false);
		setSelectedCowId(cowId);
		reset(createCalvingFormValues());
	};

	const submitCalving = async (values) => {
		if (saveInFlightRef.current) {
			return;
		}

		const cow = safeCattle.find((row) => row.id === selectedCowId);

		if (!cow) {
			notify({
				title: "분만 대상 개체를 찾지 못했습니다.",
				description: "목록을 새로고침한 뒤 다시 시도해 주세요.",
				variant: "error",
			});
			return;
		}

		saveInFlightRef.current = true;
		setIsSaving(true);

		try {
			const recorded = await handleRecordCalving({
				motherId: cow.id,
				calvingDate: values.calvingDate,
				calfGender: values.calfGender,
				calfTagNumber: values.calfTagNumber,
			});

			if (!recorded || !isMountedRef.current) {
				return;
			}

			closeCalvingForm();
		} finally {
			saveInFlightRef.current = false;
			if (isMountedRef.current) {
				setIsSaving(false);
			}
		}
	};

	const handleCalvingSubmit = (event) => {
		void handleSubmit(submitCalving)(event);
	};

	return (
		<div>
			<div className="section-header" style={{ marginBottom: "12px" }}>
				<span className="section-header-icon" aria-hidden="true">
					🐮
				</span>
				<h2 className="section-header-title">분만 예정 관리</h2>
			</div>

			{(pregnantCows.length > 0 || thisYearCalvingCount > 0) && (
				<div
					aria-live="polite"
					aria-label="분만 현황 요약"
					style={{
						display: "flex",
						flexWrap: "wrap",
						gap: "8px",
						marginBottom: "16px",
					}}
				>
					{pregnantCows.length > 0 && (
						<div className="clay-stat-chip">임신우 {pregnantCows.length}두</div>
					)}
					{calvingAlertCount > 0 && (
						<div
							className="clay-stat-chip"
							style={{
								color: "var(--color-warning)",
								borderColor: "color-mix(in srgb, var(--color-warning) 50%, transparent)",
							}}
						>
							분만 임박 {calvingAlertCount}두
						</div>
					)}
					{thisYearCalvingCount > 0 && (
						<div className="clay-stat-chip">
							올해 출생 {thisYearCalvingCount}두
						</div>
					)}
				</div>
			)}

			<div role="list" aria-label="임신우 목록" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
				{pregnantCows.length === 0 ? (
					<EmptyState
						icon={ClipboardPlus}
						title="현재 임신우가 없습니다"
						description="임신 상태의 개체를 먼저 등록하면 예정일, 분만 처리, 송아지 등록 흐름을 이어갈 수 있습니다."
						actionLabel="임신우 등록하기"
						onAction={handleOpenCattleRegistration}
					/>
				) : (
					pregnantCows.map((cow) => {
						const daysLeft = getDaysUntilCalving(cow.pregnancyDate);
						const alert = isCalvingAlert(cow.pregnancyDate);
						const isSelected = selectedCowId === cow.id;
						const buildingName = safeBuildings.find(
							(row) => row.id === cow.buildingId,
						)?.name;

						return (
							<div
								key={cow.id}
								role="listitem"
								className="rounded-[26px] border p-5"
								style={{
									background: alert
										? "color-mix(in srgb, var(--color-warning-light) 78%, var(--color-surface-elevated))"
										: "var(--surface-gradient)",
									borderColor: alert
										? "var(--color-warning)"
										: "var(--color-surface-stroke)",
									boxShadow: isSelected
										? "var(--shadow-md)"
										: "var(--shadow-sm)",
									transition: "all 0.3s cubic-bezier(0.22,1,0.36,1)",
								}}
							>
								<div className="mb-4 flex items-start justify-between gap-3">
									<div>
										<div className="mb-2 flex flex-wrap items-center gap-2">
											<span className="text-lg font-extrabold text-[color:var(--color-text)]">
												{cow.name}
											</span>
											<span
												className="inline-flex rounded-full px-3 py-1 text-[11px] font-bold"
												style={{
													background:
														"color-mix(in srgb, var(--color-calving) 18%, white 82%)",
													color: "var(--color-calving)",
												}}
											>
												임신우
											</span>
											{alert ? (
												<span
													className="inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white animate-pulse"
													style={{
														background:
															"linear-gradient(145deg, var(--color-warning), color-mix(in srgb, var(--color-warning) 72%, #9b6e40 28%))",
													}}
												>
													임박 {daysLeft}일 남음
												</span>
											) : null}
										</div>
										<div className="text-sm text-[color:var(--color-text-secondary)]">
											{buildingName} {cow.penNumber}번 · {cow.tagNumber}
										</div>
									</div>

									<div className="text-right">
										<div className="text-xs text-[color:var(--color-text-muted)]">
											예정일
										</div>
										<div
											className="text-2xl font-bold"
											style={{
												color: alert
													? "var(--color-warning)"
													: "var(--color-text)",
												fontFamily: "var(--font-display-custom)",
											}}
										>
											{formatDate(getCalvingDate(cow.pregnancyDate))}
										</div>
									</div>
								</div>

								{isSelected ? (
									<form
										onSubmit={handleCalvingSubmit}
										className="clay-inset rounded-[22px] p-4"
										style={{ borderColor: "var(--color-surface-stroke)" }}
									>
										<div className="mb-3 text-sm font-bold text-[color:var(--color-text)]">
											분만 처리
										</div>
										<div
											style={{
												display: "grid",
												gridTemplateColumns:
													"repeat(auto-fit, minmax(160px, 1fr))",
												gap: "12px",
												marginBottom: "14px",
											}}
										>
											<div>
												<label
													htmlFor="calving-date"
													style={{
														fontSize: "12px",
														color: "var(--color-text-secondary)",
														display: "block",
														marginBottom: "4px",
													}}
												>
													분만일
												</label>
												<input
													id="calving-date"
													type="date"
													{...register("calvingDate")}
													aria-required="true"
													aria-invalid={Boolean(errors.calvingDate)}
													aria-describedby={
														errors.calvingDate
															? "calving-date-error"
															: undefined
													}
													style={{ ...inputStyle, width: "100%" }}
												/>
												{errors.calvingDate ? (
													<div
														id="calving-date-error"
														role="alert"
														style={errorTextStyle}
													>
														{errors.calvingDate.message}
													</div>
												) : null}
											</div>
											<div>
												<label
													htmlFor="calf-gender"
													style={{
														fontSize: "12px",
														color: "var(--color-text-secondary)",
														display: "block",
														marginBottom: "4px",
													}}
												>
													송아지 성별
												</label>
												<select
													id="calf-gender"
													{...register("calfGender")}
													aria-required="true"
													aria-invalid={Boolean(errors.calfGender)}
													aria-describedby={
														errors.calfGender ? "calf-gender-error" : undefined
													}
													style={{ ...inputStyle, width: "100%" }}
												>
													<option value="암">암송아지</option>
													<option value="수">수송아지</option>
												</select>
												{errors.calfGender ? (
													<div
														id="calf-gender-error"
														role="alert"
														style={errorTextStyle}
													>
														{errors.calfGender.message}
													</div>
												) : null}
											</div>
											<div>
												<label
													htmlFor="calf-tag-number"
													style={{
														fontSize: "12px",
														color: "var(--color-text-secondary)",
														display: "block",
														marginBottom: "4px",
													}}
												>
													송아지 이력번호
												</label>
												<input
													id="calf-tag-number"
													type="text"
													placeholder="예: 002-1234-5678"
													{...register("calfTagNumber")}
													aria-required="true"
													aria-invalid={Boolean(errors.calfTagNumber)}
													aria-describedby={
														errors.calfTagNumber
															? "calf-tag-number-error"
															: undefined
													}
													style={{ ...inputStyle, width: "100%" }}
												/>
												{errors.calfTagNumber ? (
													<div
														id="calf-tag-number-error"
														role="alert"
														style={errorTextStyle}
													>
														{errors.calfTagNumber.message}
													</div>
												) : null}
											</div>
										</div>

										<div style={{ display: "flex", gap: "8px" }}>
											<button
												type="submit"
												disabled={isSaving}
												aria-busy={isSaving}
												aria-label={submitButtonLabel}
												title={submitButtonLabel}
												style={{ ...btnPrimary, flex: 1, padding: "12px" }}
											>
												{submitButtonText}
											</button>
											<button
												type="button"
												onClick={closeCalvingForm}
												disabled={isSaving}
												aria-busy={isSaving}
												aria-label={cancelButtonLabel}
												title={cancelButtonLabel}
												style={{
													...btnPrimary,
													background: "var(--surface-gradient)",
													color: "var(--color-text)",
													border: "1px solid var(--color-surface-stroke)",
													boxShadow: "var(--shadow-sm)",
													flex: 0.42,
												}}
											>
												{cancelButtonText}
											</button>
										</div>
									</form>
								) : (
									<button
										type="button"
										onClick={() => openCalvingForm(cow.id)}
										aria-label={`${cow.name} 분만 처리 열기`}
										title={`${cow.name} 분만 처리 열기`}
										className="clay-pressable w-full rounded-[18px] px-4 py-3 text-sm font-semibold text-[color:var(--color-text-secondary)]"
										aria-expanded={isSelected}
									>
										분만 처리 열기
									</button>
								)}
							</div>
						);
					})
				)}
			</div>
		</div>
	);
}
