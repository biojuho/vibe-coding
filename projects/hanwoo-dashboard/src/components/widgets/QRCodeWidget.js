"use client";
import { Printer } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useRef, useState } from "react";

export default function QRCodeWidget({ value, label }) {
	const qrContainerRef = useRef(null);
	const printInFlightRef = useRef(false);
	const [isPrinting, setIsPrinting] = useState(false);
	const [printStatusMessage, setPrintStatusMessage] = useState("");
	const printButtonLabel = isPrinting
		? `${label} QR 라벨 인쇄 준비 중`
		: `${label} QR 라벨 인쇄`;

	const handlePrint = () => {
		if (printInFlightRef.current) {
			return;
		}

		printInFlightRef.current = true;
		setIsPrinting(true);
		setPrintStatusMessage(`${label} QR 라벨 인쇄 창을 준비하는 중입니다.`);

		const printWindow = window.open("", "", "width=600,height=600");
		if (!printWindow) {
			printInFlightRef.current = false;
			setIsPrinting(false);
			setPrintStatusMessage(
				"팝업 차단으로 QR 인쇄 창을 열지 못했습니다. 브라우저 팝업 허용 후 다시 시도해 주세요.",
			);
			return;
		}

		const doc = printWindow.document;
		doc.title = `${label} - QR 출력`;

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
		name.textContent = label;

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

		let printCommitted = false;
		const finishPrint = () => {
			if (printCommitted) {
				return;
			}

			printCommitted = true;
			printWindow.focus();
			printWindow.print();
			printWindow.close();
			printInFlightRef.current = false;
			setIsPrinting(false);
			setPrintStatusMessage(`${label} QR 라벨 인쇄 창을 열었습니다.`);
		};

		printWindow.addEventListener("load", finishPrint, { once: true });
		printWindow.setTimeout(finishPrint, 120);
		doc.close();
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
				<QRCodeSVG value={value} size={120} />
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
