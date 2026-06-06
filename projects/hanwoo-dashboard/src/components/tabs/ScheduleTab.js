"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
	CalendarPlus,
	ChevronLeft,
	ChevronRight,
	PlusCircle,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import EmptyState from "@/components/ui/empty-state";
import {
	createScheduleFormValues,
	scheduleEventSchema,
} from "@/lib/formSchemas";
import { focusElementSafely } from "@/lib/safeFocus";

const TYPE_STYLES = {
	Vaccination: { label: "백신", color: "var(--chart-clay-4)" },
	Checkup: { label: "검진", color: "var(--chart-clay-5)" },
	Breeding: { label: "번식", color: "var(--color-calving)" },
	Other: { label: "기타", color: "var(--color-text-muted)" },
	General: { label: "일반", color: "var(--chart-clay-1)" },
};

const errorTextStyle = {
	fontSize: "12px",
	marginTop: "6px",
	color: "var(--color-danger)",
	fontWeight: 600,
};

function toValidDate(value) {
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

function toDateKey(value) {
	const date = toValidDate(value);
	return date ? date.toISOString().split("T")[0] : null;
}

function normalizeScheduleEvents(events) {
	if (!Array.isArray(events)) return [];

	return events
		.filter((event) => event && typeof event === "object" && !Array.isArray(event))
		.map((event, index) => ({
			...event,
			id: event.id ?? `schedule-${index}`,
			title:
				typeof event.title === "string" && event.title.trim()
					? event.title
					: "일정명 미등록",
			type:
				typeof event.type === "string" && TYPE_STYLES[event.type]
					? event.type
					: "General",
			isCompleted: Boolean(event.isCompleted),
		}));
}

function formatDaysLeftLabel(daysLeft) {
	return daysLeft === 0 ? "오늘" : `${daysLeft}일 남음`;
}

function normalizeScheduleTabOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export default function ScheduleTab(options = {}) {
	const { events, onCreateEvent, onToggleEvent, quickActionIntent = null } =
		normalizeScheduleTabOptions(options);
	const handleCreateEvent =
		typeof onCreateEvent === "function" ? onCreateEvent : async () => false;
	const handleToggleEvent =
		typeof onToggleEvent === "function" ? onToggleEvent : async () => false;
	const [isAdding, setIsAdding] = useState(
		() => quickActionIntent?.actionId === "add-schedule",
	);
	const [isSaving, setIsSaving] = useState(false);
	const [savingEventId, setSavingEventId] = useState(null);
	const [currentDate, setCurrentDate] = useState(new Date());
	const isMountedRef = useRef(false);
	const scheduleFormRef = useRef(null);
	const scheduleTitleInputRef = useRef(null);
	const saveInFlightRef = useRef(false);
	const completionInFlightRef = useRef(false);
	const submitButtonLabel = isSaving ? "일정 등록 중" : "일정 등록";
	const submitButtonText = isSaving ? "일정 등록 중..." : "일정 등록";
	const addFormButtonLabel = isSaving
		? "일정 저장 중에는 등록 창을 닫을 수 없습니다"
		: isAdding
			? "일정 등록 취소"
			: "일정 등록 창 열기";
	const addFormButtonText = isSaving
		? "일정 저장 중..."
		: isAdding
			? "일정 등록 취소"
			: "일정 등록";

	const {
		register,
		handleSubmit,
		reset,
		setValue,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(scheduleEventSchema),
		defaultValues: createScheduleFormValues(),
	});
	const scheduleTitleRegistration = register("title");

	const safeEvents = useMemo(() => normalizeScheduleEvents(events), [events]);

	useEffect(() => {
		isMountedRef.current = true;

		return () => {
			isMountedRef.current = false;
			saveInFlightRef.current = false;
			completionInFlightRef.current = false;
		};
	}, []);

	useEffect(() => {
		if (quickActionIntent?.actionId === "add-schedule") {
			setIsAdding(true);
		}
	}, [quickActionIntent?.actionId, quickActionIntent?.nonce]);

	useEffect(() => {
		if (!isAdding) {
			return;
		}

		const timeoutId = window.setTimeout(() => {
			try {
				scheduleFormRef.current?.scrollIntoView({
					behavior: "smooth",
					block: "start",
					inline: "nearest",
				});
			} catch {
				scheduleFormRef.current?.scrollIntoView();
			}

			focusElementSafely(scheduleTitleInputRef.current);
		}, 0);

		return () => {
			window.clearTimeout(timeoutId);
		};
	}, [isAdding, quickActionIntent?.nonce]);

	const monthDays = useMemo(() => {
		const days = [];
		const total = new Date(
			currentDate.getFullYear(),
			currentDate.getMonth() + 1,
			0,
		).getDate();
		const firstDay = new Date(
			currentDate.getFullYear(),
			currentDate.getMonth(),
			1,
		).getDay();

		for (let index = 0; index < firstDay; index += 1) {
			days.push(null);
		}

		for (let day = 1; day <= total; day += 1) {
			days.push(
				new Date(currentDate.getFullYear(), currentDate.getMonth(), day),
			);
		}

		return days;
	}, [currentDate]);

	const currentMonthEvents = useMemo(
		() =>
			safeEvents.filter((event) => {
				const date = toValidDate(event.date);
				return (
					date &&
					date.getMonth() === currentDate.getMonth() &&
					date.getFullYear() === currentDate.getFullYear()
				);
			}),
		[safeEvents, currentDate],
	);

	const upcomingEvents = useMemo(() => {
		const now = new Date();
		now.setHours(0, 0, 0, 0);

		return safeEvents
			.filter((event) => {
				const date = toValidDate(event.date);
				return date && date >= now && !event.isCompleted;
			})
			.sort(
				(first, second) => toValidDate(first.date) - toValidDate(second.date),
			)
			.slice(0, 5);
	}, [safeEvents]);

	const toggleAddForm = () => {
		if (saveInFlightRef.current || isSaving) {
			return;
		}

		const next = !isAdding;
		setIsAdding(next);

		if (!next) {
			setIsSaving(false);
			reset(createScheduleFormValues());
		}
	};

	const openFormForDate = (dateString) => {
		if (saveInFlightRef.current || isSaving) {
			return;
		}

		setValue("date", dateString, { shouldDirty: true, shouldValidate: true });
		setIsAdding(true);
	};

	const submitSchedule = async (values) => {
		if (saveInFlightRef.current) {
			return;
		}

		saveInFlightRef.current = true;
		setIsSaving(true);

		try {
			const saved = await handleCreateEvent(values);
			if (!saved || !isMountedRef.current) {
				return;
			}

			setIsAdding(false);
			reset(createScheduleFormValues());
		} finally {
			saveInFlightRef.current = false;
			if (isMountedRef.current) {
				setIsSaving(false);
			}
		}
	};

	const handleScheduleSubmit = (event) => {
		void handleSubmit(submitSchedule)(event);
	};

	const toggleEventCompletion = async (event) => {
		if (completionInFlightRef.current || savingEventId) {
			return;
		}

		completionInFlightRef.current = true;
		setSavingEventId(event.id);

		try {
			await handleToggleEvent(event.id, !event.isCompleted);
		} finally {
			completionInFlightRef.current = false;
			if (isMountedRef.current) {
				setSavingEventId(null);
			}
		}
	};

	return (
		<div>
			<div className="mb-4 flex items-center justify-between gap-3">
				<div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
					<span aria-hidden="true" style={{ fontSize: "20px", lineHeight: 1 }}>
						🗓️
					</span>
					<span
						style={{
							fontSize: "17px",
							fontWeight: 800,
							color: "var(--color-text)",
							letterSpacing: "-0.01em",
						}}
					>
						목장 일정 관리
					</span>
				</div>
				<button
					type="button"
					onClick={toggleAddForm}
					disabled={isSaving}
					aria-busy={isSaving}
					aria-label={addFormButtonLabel}
					title={addFormButtonLabel}
					className="clay-pressable inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-[color:var(--color-text)]"
				>
					<PlusCircle size={14} aria-hidden="true" />
					{addFormButtonText}
				</button>
			</div>

			{isAdding ? (
				<form
					ref={scheduleFormRef}
					onSubmit={handleScheduleSubmit}
					className="clay-page-section mb-4 p-4"
				>
					<div className="mb-3 text-sm font-bold text-[color:var(--color-text)]">
						일정 등록
					</div>
					<div className="grid gap-3">
						<div>
							<label
								htmlFor="schedule-title"
								className="mb-1 block text-xs font-bold text-[color:var(--color-text-muted)]"
							>
								일정 제목
							</label>
							<input
								id="schedule-title"
								placeholder="예: 1번 구제역 백신"
								aria-invalid={Boolean(errors.title)}
								aria-describedby={
									errors.title ? "schedule-title-error" : undefined
								}
								{...scheduleTitleRegistration}
								ref={(element) => {
									scheduleTitleRegistration.ref(element);
									scheduleTitleInputRef.current = element;
								}}
								className="clay-inset w-full rounded-[16px] px-4 py-3 text-sm text-[color:var(--color-text)] outline-none"
							/>
							{errors.title ? (
								<div
									id="schedule-title-error"
									role="alert"
									style={errorTextStyle}
								>
									{errors.title.message}
								</div>
							) : null}
						</div>

						<div className="grid grid-cols-2 gap-3">
							<div>
								<label
									htmlFor="schedule-date"
									className="mb-1 block text-xs font-bold text-[color:var(--color-text-muted)]"
								>
									일정 날짜
								</label>
								<input
									id="schedule-date"
									type="date"
									aria-invalid={Boolean(errors.date)}
									aria-describedby={
										errors.date ? "schedule-date-error" : undefined
									}
									{...register("date")}
									className="clay-inset w-full rounded-[16px] px-4 py-3 text-sm text-[color:var(--color-text)] outline-none"
								/>
								{errors.date ? (
									<div
										id="schedule-date-error"
										role="alert"
										style={errorTextStyle}
									>
										{errors.date.message}
									</div>
								) : null}
							</div>

							<div>
								<label
									htmlFor="schedule-type"
									className="mb-1 block text-xs font-bold text-[color:var(--color-text-muted)]"
								>
									일정 종류
								</label>
								<select
									id="schedule-type"
									aria-invalid={Boolean(errors.type)}
									aria-describedby={
										errors.type ? "schedule-type-error" : undefined
									}
									{...register("type")}
									className="clay-inset w-full rounded-[16px] px-4 py-3 text-sm text-[color:var(--color-text)] outline-none"
								>
									<option value="General">일반</option>
									<option value="Vaccination">백신</option>
									<option value="Checkup">검진</option>
									<option value="Breeding">번식</option>
									<option value="Other">기타</option>
								</select>
								{errors.type ? (
									<div
										id="schedule-type-error"
										role="alert"
										style={errorTextStyle}
									>
										{errors.type.message}
									</div>
								) : null}
							</div>
						</div>

						<button
							type="submit"
							disabled={isSaving}
							aria-busy={isSaving}
							aria-label={submitButtonLabel}
							title={submitButtonLabel}
							className="rounded-[18px] px-4 py-3 text-sm font-bold text-white"
							style={{
								background: "var(--surface-gradient-primary)",
								boxShadow: "var(--shadow-button-primary)",
							}}
						>
							{submitButtonText}
						</button>
					</div>
				</form>
			) : null}

			<div className="mb-3 flex items-center justify-between px-1">
				<button
					type="button"
					onClick={() =>
						setCurrentDate(
							new Date(
								currentDate.getFullYear(),
								currentDate.getMonth() - 1,
								1,
							),
						)
					}
					aria-label="이전 달 보기"
					title="이전 달 보기"
				>
					<ChevronLeft
						className="text-[color:var(--color-text-secondary)]"
						aria-hidden="true"
					/>
				</button>
				<div
					className="text-2xl font-bold text-[color:var(--color-text)]"
					style={{ fontFamily: "var(--font-display-custom)" }}
				>
					{currentDate.getFullYear()}년 {currentDate.getMonth() + 1}월
				</div>
				<button
					type="button"
					onClick={() =>
						setCurrentDate(
							new Date(
								currentDate.getFullYear(),
								currentDate.getMonth() + 1,
								1,
							),
						)
					}
					aria-label="다음 달 보기"
					title="다음 달 보기"
				>
					<ChevronRight
						className="text-[color:var(--color-text-secondary)]"
						aria-hidden="true"
					/>
				</button>
			</div>

			<div className="clay-page-section mb-5 p-3">
				<div className="mb-2 grid grid-cols-7 gap-2 text-center">
					{["일", "월", "화", "수", "목", "금", "토"].map((label, index) => (
						<div
							key={label}
							className="text-[11px] font-semibold"
							style={{
								color:
									index === 0
										? "var(--color-danger)"
										: "var(--color-text-secondary)",
							}}
						>
							{label}
						</div>
					))}
				</div>

				<div className="grid grid-cols-7 gap-2">
					{monthDays.map((day, index) => {
						if (!day) {
							return (
								<div
									key={`empty-${index}`}
									className="clay-inset min-h-[78px] rounded-[16px]"
								/>
							);
						}

						const dateStr = day.toISOString().split("T")[0];
						const dayEvents = currentMonthEvents.filter(
							(event) => toDateKey(event.date) === dateStr,
						);
						const isToday = dateStr === new Date().toISOString().split("T")[0];

						return (
							<button
								type="button"
								key={dateStr}
								onClick={() => openFormForDate(dateStr)}
								aria-label={`${dateStr} 일정 등록 열기`}
								title={`${dateStr} 일정 등록 열기`}
								className="rounded-[16px] border p-2"
								style={{
									minHeight: "78px",
									background: isToday
										? "color-mix(in srgb, var(--chart-clay-1) 14%, var(--color-surface-elevated))"
										: "var(--surface-gradient)",
									borderColor: isToday
										? "color-mix(in srgb, var(--chart-clay-1) 38%, transparent)"
										: "var(--color-surface-stroke)",
									textAlign: "left",
									font: "inherit",
									cursor: "pointer",
									boxShadow: "var(--shadow-sm)",
								}}
							>
								<div className="mb-1 text-[11px] font-semibold text-[color:var(--color-text)]">
									{day.getDate()}
								</div>
								<div className="grid gap-1">
									{dayEvents.slice(0, 3).map((event) => {
										const typeStyle =
											TYPE_STYLES[event.type] || TYPE_STYLES.General;

										return (
											<div
												key={event.id}
												className="truncate rounded-full px-2 py-0.5 text-[9px] font-bold text-white"
												style={{ background: typeStyle.color }}
											>
												{event.title}
											</div>
										);
									})}
									{dayEvents.length > 3 ? (
										<div className="text-center text-[9px] font-semibold text-[color:var(--color-text-muted)]">
											+{dayEvents.length - 3}
										</div>
									) : null}
								</div>
							</button>
						);
					})}
				</div>
			</div>

			<div className="mb-3 text-sm font-bold text-[color:var(--color-text)]">
				다가오는 일정
			</div>
			<div className="grid gap-3">
				{upcomingEvents.length > 0 ? (
					upcomingEvents.map((event) => {
						const eventDate = toValidDate(event.date);
						const daysLeft = Math.ceil(
							(eventDate - new Date()) / (1000 * 60 * 60 * 24),
						);
						const typeStyle = TYPE_STYLES[event.type] || TYPE_STYLES.General;
						const isSavingEvent = savingEventId === event.id;
						const eventCompletionLabel = isSavingEvent
							? `${event.title} 일정 완료 상태 변경 중`
							: `${event.title} 일정 완료 상태 변경`;
						const eventCompletionText = isSavingEvent
							? "일정 완료 상태 변경 중..."
							: event.isCompleted
								? "완료됨"
								: "미완료";

						return (
							<div
								key={event.id}
								className="clay-page-section flex items-center gap-3 p-4"
							>
								<input
									type="checkbox"
									checked={event.isCompleted}
									onChange={() => toggleEventCompletion(event)}
									disabled={isSavingEvent}
									aria-busy={isSavingEvent}
									aria-label={eventCompletionLabel}
									title={eventCompletionLabel}
									style={{
										width: "18px",
										height: "18px",
										accentColor: "var(--chart-clay-1)",
										cursor: "pointer",
									}}
								/>
								<div className="min-w-0 flex-1">
									<div className="mb-1 flex flex-wrap items-center justify-between gap-2">
										<span
											className="inline-flex rounded-full px-3 py-1 text-[10px] font-bold text-white"
											style={{ background: typeStyle.color }}
										>
											{typeStyle.label}
										</span>
										<span
											className="text-xs font-medium"
											style={{
												color:
													daysLeft <= 3
														? "var(--color-danger)"
														: "var(--color-text-secondary)",
											}}
										>
											{eventDate.toLocaleDateString()}{" "}
											({formatDaysLeftLabel(daysLeft)})
										</span>
									</div>
									<div className="text-sm font-semibold text-[color:var(--color-text)]">
										{event.title}
									</div>
									<div className="mt-1 text-xs font-semibold text-[color:var(--color-text-muted)]">
										{eventCompletionText}
									</div>
								</div>
							</div>
						);
					})
				) : (
					<EmptyState
						icon={CalendarPlus}
						title="예정된 일정이 없습니다"
						description="검진, 접종, 번식 일정을 먼저 올려두면 오늘 브리프와 알림에서 바로 이어집니다."
						actionLabel="일정 추가"
						onAction={() => setIsAdding(true)}
					/>
				)}
			</div>
		</div>
	);
}
