"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { PackagePlus } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import EmptyState from "@/components/ui/empty-state";
import { PremiumButton } from "@/components/ui/premium-button";
import { PremiumCard, PremiumCardContent } from "@/components/ui/premium-card";
import {
	PremiumInput,
	PremiumLabel,
	PremiumSelect,
} from "@/components/ui/premium-input";
import {
	createInventoryFormValues,
	inventoryItemSchema,
} from "@/lib/formSchemas";
import { focusElementSafely } from "@/lib/safeFocus";

const errorTextStyle = {
	fontSize: "12px",
	marginTop: "6px",
	color: "var(--color-danger)",
	fontWeight: 600,
};

const PLAIN_NONNEGATIVE_NUMBER_INPUT_PATTERN = /^(?:\d+|\d+\.\d+|\.\d+)$/;

function parseInlineQuantityInput(value) {
	const normalized = String(value).trim();
	if (!PLAIN_NONNEGATIVE_NUMBER_INPUT_PATTERN.test(normalized)) {
		return Number.NaN;
	}

	const quantity = Number(normalized);
	return Number.isFinite(quantity) ? quantity : Number.NaN;
}

function toInventoryNumber(value, fallback = 0) {
	if (value === null || value === undefined || value === "") {
		return fallback;
	}

	const number = Number(value);
	return Number.isFinite(number) ? number : fallback;
}

function normalizeInventoryItems(inventory) {
	if (!Array.isArray(inventory)) return [];

	return inventory
		.filter((item) => item && typeof item === "object" && !Array.isArray(item))
		.map((item, index) => ({
			...item,
			category:
				typeof item.category === "string" && item.category.trim()
					? item.category
					: "Other",
			id: item.id ?? `inventory-${index}`,
			name:
				typeof item.name === "string" && item.name.trim()
					? item.name
					: "재고명 미등록",
			quantity: toInventoryNumber(item.quantity, null),
			threshold:
				item.threshold === null ||
				item.threshold === undefined ||
				item.threshold === ""
					? null
					: toInventoryNumber(item.threshold, null),
			unit:
				typeof item.unit === "string" && item.unit.trim() ? item.unit : "개",
		}));
}

function normalizeInventoryTabOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export default function InventoryTab(options = {}) {
	const { inventory, onAddItem, onUpdateQuantity, quickActionIntent = null } =
		normalizeInventoryTabOptions(options);
	const safeInventory = normalizeInventoryItems(inventory);
	const lowStockCount = useMemo(
		() =>
			safeInventory.filter(
				(item) =>
					item.quantity !== null &&
					item.threshold !== null &&
					item.quantity <= item.threshold,
			).length,
		[safeInventory],
	);
	const handleAddItem =
		typeof onAddItem === "function" ? onAddItem : async () => false;
	const handleUpdateQuantity =
		typeof onUpdateQuantity === "function"
			? onUpdateQuantity
			: async () => false;
	const [isAdding, setIsAdding] = useState(
		() => quickActionIntent?.actionId === "add-inventory",
	);
	const [isSaving, setIsSaving] = useState(false);
	const [savingQuantityId, setSavingQuantityId] = useState(null);
	const [editId, setEditId] = useState(null);
	const [editQty, setEditQty] = useState("");
	const isMountedRef = useRef(false);
	const inventoryFormRef = useRef(null);
	const inventoryNameInputRef = useRef(null);
	const saveInFlightRef = useRef(false);
	const quantityInFlightRef = useRef(false);
	const submitButtonLabel = isSaving ? "재고 등록 중" : "재고 등록";
	const submitButtonText = isSaving ? "재고 등록 중..." : "재고 등록";
	const addFormButtonLabel = isSaving
		? "재고 저장 중에는 등록 창을 닫을 수 없습니다"
		: isAdding
			? "재고 등록 취소"
			: "재고 등록 창 열기";
	const addFormButtonText = isSaving
		? "재고 저장 중..."
		: isAdding
			? "재고 등록 취소"
			: "재고 등록";

	const {
		register,
		handleSubmit,
		reset,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(inventoryItemSchema),
		defaultValues: createInventoryFormValues(),
	});
	const inventoryNameRegistration = register("name");

	const categories = {
		Feed: "사료",
		Medicine: "약품",
		Equipment: "기자재",
		Other: "기타",
	};

	useEffect(() => {
		isMountedRef.current = true;

		return () => {
			isMountedRef.current = false;
			saveInFlightRef.current = false;
			quantityInFlightRef.current = false;
		};
	}, []);

	useEffect(() => {
		if (quickActionIntent?.actionId === "add-inventory") {
			setIsAdding(true);
		}
	}, [quickActionIntent?.actionId, quickActionIntent?.nonce]);

	useEffect(() => {
		if (!isAdding) {
			return;
		}

		const timeoutId = window.setTimeout(() => {
			try {
				inventoryFormRef.current?.scrollIntoView({
					behavior: "smooth",
					block: "start",
					inline: "nearest",
				});
			} catch {
				inventoryFormRef.current?.scrollIntoView();
			}

			focusElementSafely(inventoryNameInputRef.current);
		}, 0);

		return () => {
			window.clearTimeout(timeoutId);
		};
	}, [isAdding, quickActionIntent?.nonce]);

	const toggleAddForm = () => {
		if (saveInFlightRef.current || isSaving) {
			return;
		}

		const next = !isAdding;
		setIsAdding(next);

		if (!next) {
			setIsSaving(false);
			reset(createInventoryFormValues());
		}
	};

	const submitNewItem = async (values) => {
		if (saveInFlightRef.current) {
			return;
		}

		saveInFlightRef.current = true;
		setIsSaving(true);

		try {
			const saved = await handleAddItem(values);
			if (!saved || !isMountedRef.current) {
				return;
			}

			setIsAdding(false);
			reset(createInventoryFormValues());
		} finally {
			saveInFlightRef.current = false;
			if (isMountedRef.current) {
				setIsSaving(false);
			}
		}
	};

	const handleInventorySubmit = (event) => {
		void handleSubmit(submitNewItem)(event);
	};

	const handleUpdate = async (id) => {
		if (quantityInFlightRef.current || savingQuantityId) {
			return;
		}

		const parsedQuantity = parseInlineQuantityInput(editQty);
		if (!Number.isFinite(parsedQuantity)) {
			return;
		}

		quantityInFlightRef.current = true;
		setSavingQuantityId(id);

		try {
			const saved = await handleUpdateQuantity(id, parsedQuantity);
			if (!saved || !isMountedRef.current) {
				return;
			}

			setEditId(null);
			setEditQty("");
		} finally {
			quantityInFlightRef.current = false;
			if (isMountedRef.current) {
				setSavingQuantityId(null);
			}
		}
	};

	return (
		<div>
			<div
				style={{
					display: "flex",
					justifyContent: "space-between",
					alignItems: "center",
					marginBottom: "14px",
				}}
			>
				<div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
					<span aria-hidden="true" style={{ fontSize: "20px", lineHeight: 1 }}>
						📦
					</span>
					<span
						style={{
							fontSize: "17px",
							fontWeight: 800,
							color: "var(--color-text)",
							letterSpacing: "-0.01em",
						}}
					>
						재고 관리
					</span>
				</div>
				<PremiumButton
					variant="outline"
					size="sm"
					onClick={toggleAddForm}
					disabled={isSaving}
					aria-busy={isSaving}
					aria-expanded={isAdding}
					aria-label={addFormButtonLabel}
					title={addFormButtonLabel}
					className="min-h-11 text-[13px] text-green-400 border-green-500/50 hover:bg-green-500/10 px-4 py-2 rounded-lg font-bold"
				>
					{addFormButtonText}
				</PremiumButton>
			</div>

			{lowStockCount > 0 && (
				<div style={{ marginBottom: "12px" }}>
					<div
						className="clay-stat-chip"
						style={{
							color: "var(--color-danger)",
							borderColor: "color-mix(in srgb, var(--color-danger) 50%, transparent)",
						}}
					>
						부족 경고 {lowStockCount}건
					</div>
				</div>
			)}

			{isAdding ? (
				<form
					ref={inventoryFormRef}
					onSubmit={handleInventorySubmit}
					className="mb-4"
				>
					<PremiumCard className="bg-slate-800/60 w-full mb-4">
						<PremiumCardContent className="p-4">
							<div
								style={{
									fontSize: "14px",
									fontWeight: 700,
									marginBottom: "12px",
									color: "var(--color-text)",
								}}
							>
								새 재고 등록
							</div>
							<div style={{ display: "grid", gap: "10px" }}>
								<div>
									<PremiumLabel htmlFor="inventory-name">자재명</PremiumLabel>
									<PremiumInput
										id="inventory-name"
										placeholder="자재명 (예: 볏짚)"
										{...inventoryNameRegistration}
										ref={(element) => {
											inventoryNameRegistration.ref(element);
											inventoryNameInputRef.current = element;
										}}
										hasError={!!errors.name}
										aria-invalid={Boolean(errors.name)}
										aria-describedby={
											errors.name ? "inventory-name-error" : undefined
										}
									/>
									{errors.name ? (
										<div
											id="inventory-name-error"
											role="alert"
											style={errorTextStyle}
										>
											{errors.name.message}
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
										<PremiumLabel htmlFor="inventory-category">
											분류
										</PremiumLabel>
										<PremiumSelect
											id="inventory-category"
											{...register("category")}
											hasError={!!errors.category}
											aria-invalid={Boolean(errors.category)}
											aria-describedby={
												errors.category ? "inventory-category-error" : undefined
											}
										>
											<option value="Feed" className="bg-slate-900">
												사료/조사료
											</option>
											<option value="Medicine" className="bg-slate-900">
												약품/영양제
											</option>
											<option value="Equipment" className="bg-slate-900">
												기자재
											</option>
											<option value="Other" className="bg-slate-900">
												기타
											</option>
										</PremiumSelect>
										{errors.category ? (
											<div
												id="inventory-category-error"
												role="alert"
												style={errorTextStyle}
											>
												{errors.category.message}
											</div>
										) : null}
									</div>

									<div>
										<PremiumLabel htmlFor="inventory-quantity">
											수량
										</PremiumLabel>
										<PremiumInput
											id="inventory-quantity"
											type="number"
											placeholder="수량"
											{...register("quantity")}
											hasError={!!errors.quantity}
											aria-invalid={Boolean(errors.quantity)}
											aria-describedby={
												errors.quantity ? "inventory-quantity-error" : undefined
											}
										/>
										{errors.quantity ? (
											<div
												id="inventory-quantity-error"
												role="alert"
												style={errorTextStyle}
											>
												{errors.quantity.message}
											</div>
										) : null}
									</div>
								</div>

								<div
									style={{
										display: "grid",
										gridTemplateColumns: "1fr 1fr",
										gap: "10px",
									}}
								>
									<div>
										<PremiumLabel htmlFor="inventory-unit">단위</PremiumLabel>
										<PremiumInput
											id="inventory-unit"
											placeholder="단위 (예: kg, 박스)"
											{...register("unit")}
											hasError={!!errors.unit}
											aria-invalid={Boolean(errors.unit)}
											aria-describedby={
												errors.unit ? "inventory-unit-error" : undefined
											}
										/>
										{errors.unit ? (
											<div
												id="inventory-unit-error"
												role="alert"
												style={errorTextStyle}
											>
												{errors.unit.message}
											</div>
										) : null}
									</div>

									<div>
										<PremiumLabel htmlFor="inventory-threshold">
											경고 기준값
										</PremiumLabel>
										<PremiumInput
											id="inventory-threshold"
											type="number"
											placeholder="경고 기준값 (선택)"
											{...register("threshold")}
											hasError={!!errors.threshold}
											aria-invalid={Boolean(errors.threshold)}
											aria-describedby={
												errors.threshold
													? "inventory-threshold-error"
													: undefined
											}
										/>
										{errors.threshold ? (
											<div
												id="inventory-threshold-error"
												role="alert"
												style={errorTextStyle}
											>
												{errors.threshold.message}
											</div>
										) : null}
									</div>
								</div>

								<PremiumButton
									type="submit"
									disabled={isSaving}
									aria-busy={isSaving}
									aria-label={submitButtonLabel}
									title={submitButtonLabel}
									variant="primary"
									glow
									className="w-full py-3 mt-2 rounded-lg"
								>
									{submitButtonText}
								</PremiumButton>
							</div>
						</PremiumCardContent>
					</PremiumCard>
				</form>
			) : null}

			<div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
				{safeInventory.map((item) => {
					const hasQuantity = item.quantity !== null;
					const isLow =
						hasQuantity && item.threshold !== null && item.quantity <= item.threshold;
					const isQuantitySaving = savingQuantityId === item.id;
					const itemQuantitySaveLabel = isQuantitySaving
						? `${item.name} 재고 수량 저장 중`
						: `${item.name} 재고 수량 저장`;
					const itemQuantitySaveText = isQuantitySaving
						? "수량 저장 중..."
						: "수량 저장";

					return (
						<PremiumCard
							key={item.id}
							className={`p-0 ${isLow ? "border-2 border-red-500/50" : ""}`}
						>
							<PremiumCardContent className="p-3.5 relative">
								{isLow ? (
									<div
										style={{
											position: "absolute",
											top: "-10px",
											right: "10px",
											background: "var(--color-danger)",
											color: "white",
											fontSize: "10px",
											padding: "2px 8px",
											borderRadius: "10px",
											fontWeight: 700,
										}}
									>
										부족 경고
									</div>
								) : null}

								<div
									style={{
										display: "flex",
										justifyContent: "space-between",
										alignItems: "center",
									}}
								>
									<div>
										<div
											style={{
												fontSize: "11px",
												color: "var(--color-text-muted)",
												marginBottom: "2px",
											}}
										>
											{categories[item.category] || item.category}
										</div>
										<div
											style={{
												fontWeight: 700,
												fontSize: "15px",
												color: "var(--color-text)",
											}}
										>
											{item.name}
										</div>
									</div>

									<div style={{ textAlign: "right" }}>
										{editId === item.id ? (
											<div
												style={{
													display: "flex",
													alignItems: "center",
													gap: "4px",
												}}
											>
												<PremiumInput
													type="number"
													value={editQty}
													onChange={(event) => setEditQty(event.target.value)}
													disabled={isQuantitySaving}
													aria-label={`${item.name} 재고 수량 입력`}
													title={`${item.name} 재고 수량 입력`}
													className="w-[80px] px-2 py-1.5 h-auto text-sm bg-slate-900 border-slate-700"
													autoFocus
													hasError={false}
												/>
												<PremiumButton
													variant="secondary"
													onClick={() => handleUpdate(item.id)}
													disabled={isQuantitySaving}
													aria-busy={isQuantitySaving}
													aria-label={itemQuantitySaveLabel}
													title={itemQuantitySaveLabel}
													className="px-2 py-1.5 h-auto text-xs"
												>
													{itemQuantitySaveText}
												</PremiumButton>
											</div>
										) : (
											<button
												type="button"
												aria-label={`${item.name} 재고 수량 수정`}
												title={`${item.name} 재고 수량 수정`}
												onClick={() => {
													setEditId(item.id);
													setEditQty(hasQuantity ? String(item.quantity) : "");
												}}
												style={{
													fontSize: "16px",
													fontWeight: 800,
													color: isLow
														? "var(--color-danger)"
														: "var(--color-text)",
													cursor: "pointer",
													background: "none",
													border: "none",
													padding: 0,
												}}
											>
												{hasQuantity ? item.quantity : "수량 미등록"}{" "}
												{hasQuantity ? (
													<span style={{ fontSize: "12px", fontWeight: 400 }}>
														{item.unit}
													</span>
												) : null}
											</button>
										)}
									</div>
								</div>
							</PremiumCardContent>
						</PremiumCard>
					);
				})}

				{safeInventory.length === 0 ? (
					<EmptyState
						icon={PackagePlus}
						title="등록된 재고가 없습니다"
						description="사료, 약품, 기자재를 등록하면 부족 경고와 오늘 브리프에서 먼저 챙길 항목을 보여줍니다."
						actionLabel="재고 등록"
						onAction={() => setIsAdding(true)}
					/>
				) : null}
			</div>
		</div>
	);
}
