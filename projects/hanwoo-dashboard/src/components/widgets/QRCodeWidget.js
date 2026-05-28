"use client";
import { Printer } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useRef, useState } from "react";

const DEFAULT_QR_LABEL = "QR 라벨";

function normalizeQRCodeWidgetOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeQRCodeText(value, fallback) {
	if (typeof value === "string" && value.trim()) {
		return value;
	}

	if (typeof value === "number" && Number.isFinite(value)) {
		return String(value);
	}

	return fallback;
}

export default function QRCodeWidget(options = {}) {
	const { value, label } = normalizeQRCodeWidgetOptions(options);
	const qrLabel = normalizeQRCodeText(label, DEFAULT_QR_LABEL);
	const qrValue = normalizeQRCodeText(value, qrLabel);
	const qrContainerRef = useRef(null);
	const printInFlightRef = useRef(false);
	const isMountedRef = useRef(false);
	const [isPrinting, setIsPrinting] = useState(false);
	const [printStatusMessage, setPrintStatusMessage] = useState("");
	const printButtonLabel = isPrinting
		? `${qrLabel} QR 라벨 인쇄 준비 중`
		: `${qrLabel} QR 라벨 인쇄`;

	const resetPrintState = () => {
		printInFlightRef.current = false;
		if (isMountedRef.current) {
			setIsPrinting(false);
		}
	};

	const updatePrintStatusMessage = (message) => {
		if (isMountedRef.current) {
			setPrintStatusMessage(message);
		}
	};

	useEffect(() => {
		isMountedRef.current = true;

		return () => {
			isMountedRef.current = false;
			printInFlightRef.current = false;
		};
	}, []);

	const closePrintWindow = (printWindow) => {
		try {
			printWindow.close();
		} catch (error) {
			console.error("Failed to close QR print window:", error);
		}
	};

	const schedulePrintFallback = (printWindow, finishPrint) => {
		try {
			printWindow.setTimeout(finishPrint, 120);
			return true;
		} catch (error) {
			console.error("Failed to schedule QR print fallback:", error);
			return false;
		}
	};

	const registerPrintLoadHandler = (printWindow, finishPrint) => {
		try {
			printWindow.addEventListener("load", finishPrint, { once: true });
			return true;
		} catch (error) {
			console.error("Failed to register QR print load handler:", error);
			return false;
		}
	};

	const openPrintWindow = () => {
		try {
			return window.open("", "", "width=600,height=600");
		} catch (error) {
			console.error("Failed to open QR print window:", error);
			return null;
		}
	};

	const handlePrint = () => {
		if (printInFlightRef.current) {
			return;
		}

		printInFlightRef.current = true;
		setIsPrinting(true);
		updatePrintStatusMessage(`${qrLabel} QR 라벨 인쇄 창을 준비하는 중입니다.`);

		const printWindow = openPrintWindow();
		if (!printWindow) {
			resetPrintState();
			updatePrintStatusMessage(
				"팝업 차단으로 QR 인쇄 창을 열지 못했습니다. 브라우저 팝업 허용 후 다시 시도해 주세요.",
			);
			return;
		}

		let printCommitted = false;

		try {
			const doc = printWindow.document;
			doc.title = `${qrLabel} - QR 출력`;

			const style = doc.createElement("style");
			style.textContent =
				"body { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: sans-serif; }" +
				".tag { border: 2px solid #000; padding: 20px; text-align: center; border-radius: 10px; }" +
				".name { font-size: 24px; font-weight: bold; margin-bottom: 10px; }" +
				".info { font-size: 14px; color: #555; margin-top: 10px; }";
			doc.head.appendChild(style);

			const tag = doc.createElement("div");
			tag.className = "tag";

			const name = doc.createElement("div");
			name.className = "name";
			name.textContent = qrLabel;

			const qrContainer = doc.createElement("div");
			const sourceSvg = qrContainerRef.current?.querySelector("svg");
			if (sourceSvg) {
				qrContainer.appendChild(sourceSvg.cloneNode(true));
			}

			const info = doc.createElement("div");
			info.className = "info";
			info.textContent = "Joolife 한우 스마트팜";

			tag.append(name, qrContainer, info);
			doc.body.appendChild(tag);

			const finishPrint = () => {
				if (printCommitted) {
					return;
				}

				if (!isMountedRef.current) {
					printCommitted = true;
					closePrintWindow(printWindow);
					resetPrintState();
					return;
				}

				printCommitted = true;
				try {
					printWindow.focus();
					printWindow.print();
					updatePrintStatusMessage(`${qrLabel} QR 라벨 인쇄 창을 열었습니다.`);
				} catch (error) {
					console.error("Failed to print QR label:", error);
					updatePrintStatusMessage(
						`${qrLabel} QR 라벨 인쇄를 시작하지 못했습니다. 다시 시도해 주세요.`,
					);
				} finally {
					closePrintWindow(printWindow);
					resetPrintState();
				}
			};

			const registeredLoadHandler = registerPrintLoadHandler(
				printWindow,
				finishPrint,
			);
			const scheduledFallback = schedulePrintFallback(printWindow, finishPrint);
			if (!registeredLoadHandler && !scheduledFallback) {
				finishPrint();
			}
			doc.close();
		} catch (error) {
			printCommitted = true;
			console.error("Failed to prepare QR print window:", error);
			closePrintWindow(printWindow);
			resetPrintState();
			updatePrintStatusMessage(
				`${qrLabel} QR 라벨 인쇄 창을 준비하지 못했습니다. 다시 시도해 주세요.`,
			);
		}
	};

	return (
		<div
			style={{
				display: "flex",
				flexDirection: "column",
				alignItems: "center",
				gap: "10px",
			}}
		>
			<div
				ref={qrContainerRef}
				style={{
					background: "white",
					padding: "10px",
					border: "1px solid #EEE",
					borderRadius: "8px",
				}}
			>
				<QRCodeSVG value={qrValue} size={120} />
			</div>
			<button
				type="button"
				onClick={handlePrint}
				disabled={isPrinting}
				aria-busy={isPrinting}
				aria-label={printButtonLabel}
				title={printButtonLabel}
				style={{
					display: "inline-flex",
					alignItems: "center",
					gap: "4px",
					fontSize: "11px",
					padding: "4px 8px",
					background: "#3E2F1C",
					color: "white",
					border: "none",
					borderRadius: "4px",
					cursor: isPrinting ? "wait" : "pointer",
					opacity: isPrinting ? 0.7 : 1,
				}}
			>
				<Printer size={12} aria-hidden="true" />
				<span>{isPrinting ? "QR 라벨 인쇄 준비 중..." : "QR 라벨 인쇄"}</span>
			</button>
			{printStatusMessage && (
				<div
					role="status"
					aria-live="polite"
					aria-atomic="true"
					style={{
						fontSize: "11px",
						color: "var(--color-text-muted)",
						textAlign: "center",
						maxWidth: "180px",
						lineHeight: 1.4,
					}}
				>
					{printStatusMessage}
				</div>
			)}
		</div>
	);
}
