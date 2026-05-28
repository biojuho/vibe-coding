"use client";

import {
	createContext,
	useCallback,
	useContext,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";

import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

const FeedbackContext = createContext(null);

const TOAST_STYLES = {
	success: {
		accent: "var(--color-success)",
		background: "color-mix(in srgb, var(--color-success) 12%, white 88%)",
	},
	error: {
		accent: "var(--color-danger)",
		background: "color-mix(in srgb, var(--color-danger) 12%, white 88%)",
	},
	warning: {
		accent: "var(--color-warning)",
		background: "color-mix(in srgb, var(--color-warning) 16%, white 84%)",
	},
	info: {
		accent: "var(--color-primary)",
		background: "color-mix(in srgb, var(--color-primary) 12%, white 88%)",
	},
};

const DEFAULT_CONFIRMATION = {
	open: false,
	title: "",
	description: "",
	confirmLabel: "확인",
	cancelLabel: "취소",
	variant: "default",
};

function normalizeFeedbackProviderOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeToastOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export function FeedbackProvider(options = {}) {
	const { children } = normalizeFeedbackProviderOptions(options);
	const [toasts, setToasts] = useState([]);
	const [confirmation, setConfirmation] = useState(DEFAULT_CONFIRMATION);
	const mountedRef = useRef(true);
	const resolverRef = useRef(null);
	const timeoutIdsRef = useRef(new Map());

	const dismiss = useCallback((id) => {
		const timeoutId = timeoutIdsRef.current.get(id);
		if (timeoutId) {
			try {
				window.clearTimeout(timeoutId);
			} catch {}
			timeoutIdsRef.current.delete(id);
		}

		if (mountedRef.current) {
			setToasts((current) => current.filter((toast) => toast.id !== id));
		}
	}, []);

	const notify = useCallback(
		(options = {}) => {
			if (!mountedRef.current) {
				return;
			}

			const {
				title,
				description = "",
				variant = "info",
				duration = 3600,
			} = normalizeToastOptions(options);
			const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
			setToasts((current) => [...current, { id, title, description, variant }]);

			try {
				const timeoutId = window.setTimeout(() => {
					timeoutIdsRef.current.delete(id);
					if (mountedRef.current) {
						dismiss(id);
					}
				}, duration);
				timeoutIdsRef.current.set(id, timeoutId);
			} catch (error) {
				console.error("Failed to schedule feedback toast dismissal:", error);
			}
		},
		[dismiss],
	);

	useEffect(() => {
		mountedRef.current = true;
		const timeoutIds = timeoutIdsRef.current;
		return () => {
			mountedRef.current = false;
			timeoutIds.forEach((timeoutId) => {
				try {
					window.clearTimeout(timeoutId);
				} catch {}
			});
			timeoutIds.clear();
			if (resolverRef.current) {
				resolverRef.current(false);
				resolverRef.current = null;
			}
		};
	}, []);

	const confirm = useCallback((options) => {
		if (!mountedRef.current) {
			return Promise.resolve(false);
		}

		setConfirmation({
			open: true,
			title: options?.title ?? "계속 진행할까요?",
			description: options?.description ?? "",
			confirmLabel: options?.confirmLabel ?? "확인",
			cancelLabel: options?.cancelLabel ?? "취소",
			variant: options?.variant ?? "default",
		});

		return new Promise((resolve) => {
			resolverRef.current = resolve;
		});
	}, []);

	const closeConfirmation = useCallback((result) => {
		if (resolverRef.current) {
			resolverRef.current(result);
			resolverRef.current = null;
		}
		if (mountedRef.current) {
			setConfirmation(DEFAULT_CONFIRMATION);
		}
	}, []);

	const contextValue = useMemo(
		() => ({
			notify,
			confirm,
		}),
		[confirm, notify],
	);
	const cancelButtonLabel = `${confirmation.cancelLabel}하고 확인 창 닫기`;
	const confirmButtonLabel = `${confirmation.confirmLabel} 실행`;

	return (
		<FeedbackContext.Provider value={contextValue}>
			{children}

			<div className="pointer-events-none fixed inset-x-0 bottom-4 z-[70] flex justify-center px-4 sm:justify-end">
				<div className="flex w-full max-w-sm flex-col gap-3">
					{toasts.map((toast) => {
						const style = TOAST_STYLES[toast.variant] || TOAST_STYLES.info;
						const isUrgent =
							toast.variant === "error" || toast.variant === "warning";
						const toastDismissLabel = `${toast.title} 알림 닫기`;

						return (
							<div
								key={toast.id}
								role={isUrgent ? "alert" : "status"}
								aria-live={isUrgent ? "assertive" : "polite"}
								aria-atomic="true"
								className="pointer-events-auto rounded-[24px] border px-4 py-3 shadow-[var(--shadow-md)] backdrop-blur-md"
								style={{
									borderColor: `color-mix(in srgb, ${style.accent} 24%, transparent)`,
									background: style.background,
								}}
							>
								<div className="flex items-start gap-3">
									<span
										className="mt-1 h-2.5 w-2.5 flex-shrink-0 rounded-full"
										style={{ background: style.accent }}
										aria-hidden="true"
									/>
									<div className="min-w-0 flex-1">
										<div className="text-sm font-bold text-[color:var(--color-text)]">
											{toast.title}
										</div>
										{toast.description ? (
											<div className="mt-1 text-xs text-[color:var(--color-text-muted)]">
												{toast.description}
											</div>
										) : null}
									</div>
									<button
										type="button"
										onClick={() => dismiss(toast.id)}
										aria-label={toastDismissLabel}
										title={toastDismissLabel}
										className="text-xs font-semibold text-[color:var(--color-text-muted)]"
									>
										닫기
									</button>
								</div>
							</div>
						);
					})}
				</div>
			</div>

			<Dialog
				open={confirmation.open}
				onOpenChange={(open) => !open && closeConfirmation(false)}
			>
				<DialogContent className="sm:max-w-md" closeLabel="확인 창 닫기">
					<DialogHeader>
						<DialogTitle>{confirmation.title}</DialogTitle>
						{confirmation.description ? (
							<DialogDescription>{confirmation.description}</DialogDescription>
						) : null}
					</DialogHeader>
					<DialogFooter>
						<Button
							variant="outline"
							onClick={() => closeConfirmation(false)}
							aria-label={cancelButtonLabel}
							title={cancelButtonLabel}
						>
							{confirmation.cancelLabel}
						</Button>
						<Button
							variant={
								confirmation.variant === "destructive"
									? "destructive"
									: "default"
							}
							onClick={() => closeConfirmation(true)}
							aria-label={confirmButtonLabel}
							title={confirmButtonLabel}
						>
							{confirmation.confirmLabel}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>
		</FeedbackContext.Provider>
	);
}

export function useAppFeedback() {
	const context = useContext(FeedbackContext);

	if (!context) {
		throw new Error("useAppFeedback must be used within a FeedbackProvider");
	}

	return context;
}
