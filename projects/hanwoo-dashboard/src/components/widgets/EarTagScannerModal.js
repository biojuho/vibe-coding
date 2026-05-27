import { AlertTriangle, Camera, Check, Eye, RefreshCw, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { PremiumButton } from "@/components/ui/premium-button";
import {
	playScanFailure,
	playScanSuccess,
	playTactileClick,
	triggerVibration,
} from "@/lib/audio";

function formatScannerBirthDate(value) {
	if (!value) {
		return "생년월일 미등록";
	}

	const date = new Date(value);
	return Number.isNaN(date.getTime())
		? "생년월일 미등록"
		: date.toLocaleDateString("ko-KR");
}

function scheduleScannerFrame(callback) {
	try {
		return window.requestAnimationFrame(callback);
	} catch (error) {
		console.error("Failed to schedule ear tag scanner frame:", error);
		return null;
	}
}

function cancelScannerFrame(animationId) {
	if (animationId === null) {
		return;
	}

	try {
		window.cancelAnimationFrame(animationId);
	} catch {}
}

function deferScannerTask(callback) {
	try {
		queueMicrotask(callback);
	} catch {
		Promise.resolve().then(callback);
	}
}

function deferScannerNoMatch(setScanStatus, shouldApply = () => true) {
	const applyNoMatch = () => {
		if (shouldApply()) {
			setScanStatus("no_match");
		}
	};

	deferScannerTask(applyNoMatch);
}

export default function EarTagScannerModal({
	isOpen,
	onClose,
	cattleList = [],
	onSelect,
}) {
	const canvasRef = useRef(null);
	const animationRef = useRef(null);
	const [scanStatus, setScanStatus] = useState("scanning"); // 'scanning', 'success', 'no_match'
	const [matchedCow, setMatchedCow] = useState(null);
	const [scannedTag, setScannedTag] = useState("");
	const [targetCandidate, setTargetCandidate] = useState(null);

	// Initialize random target from cattleList on open to scan
	useEffect(() => {
		if (isOpen && cattleList.length > 0) {
			let cancelled = false;

			deferScannerTask(() => {
				if (cancelled) {
					return;
				}

				// Pick a random cow as the simulated target
				const idx = Math.floor(Math.random() * cattleList.length);
				setTargetCandidate(cattleList[idx]);
				setScanStatus("scanning");
				setMatchedCow(null);
				setScannedTag("");
			});

			return () => {
				cancelled = true;
			};
		}

		return undefined;
	}, [isOpen, cattleList]);

	// Canvas retro-futuristic HUD animation
	useEffect(() => {
		if (!isOpen || scanStatus !== "scanning") {
			cancelScannerFrame(animationRef.current);
			animationRef.current = null;
			return;
		}

		let cancelled = false;
		const canvas = canvasRef.current;
		if (!canvas) return;
		const ctx = canvas.getContext("2d");
		if (!ctx) {
			deferScannerNoMatch(setScanStatus, () => !cancelled);
			return () => {
				cancelled = true;
			};
		}

		const width = (canvas.width = canvas.offsetWidth || 320);
		const height = (canvas.height = canvas.offsetHeight || 320);
		let laserY = 50;
		let laserDirection = 1;
		let frameCount = 0;

		// OCR digits rolling
		const ocrCodes = [
			"0025184",
			"3910582",
			"8273910",
			"0029314",
			"7491028",
			"1947201",
		];

		const render = () => {
			frameCount++;
			ctx.clearRect(0, 0, width, height);

			// 1. Draw camera view simulation background
			// Simulated static grids and noise
			ctx.fillStyle = "rgba(16, 24, 16, 0.85)";
			ctx.fillRect(0, 0, width, height);

			// Fine tech grid
			ctx.strokeStyle = "rgba(34, 197, 94, 0.08)";
			ctx.lineWidth = 1;
			const gridSize = 20;
			for (let x = 0; x < width; x += gridSize) {
				ctx.beginPath();
				ctx.moveTo(x, 0);
				ctx.lineTo(x, height);
				ctx.stroke();
			}
			for (let y = 0; y < height; y += gridSize) {
				ctx.beginPath();
				ctx.moveTo(0, y);
				ctx.lineTo(width, y);
				ctx.stroke();
			}

			// 2. Draw mock cow shape/silhouette outline in the center (vector pulse)
			ctx.save();
			ctx.translate(width / 2, height / 2 - 10);
			ctx.strokeStyle = "rgba(34, 197, 94, 0.15)";
			ctx.lineWidth = 2.5;
			ctx.beginPath();
			// Draw a cow/cattle ear tag silhouette block
			ctx.moveTo(-45, -25);
			ctx.lineTo(45, -25);
			ctx.lineTo(35, 30);
			ctx.lineTo(-35, 30);
			ctx.closePath();
			ctx.stroke();

			// Drawing dynamic scanning anchor circles
			ctx.fillStyle =
				frameCount % 30 < 15
					? "rgba(34, 197, 94, 0.3)"
					: "rgba(34, 197, 94, 0.1)";
			ctx.beginPath();
			ctx.arc(20, 5, 4, 0, Math.PI * 2);
			ctx.fill();
			ctx.restore();

			// 3. Draw scanning frame brackets (rugged camera corners)
			const pad = 40;
			const len = 25;
			ctx.strokeStyle = "rgba(34, 197, 94, 0.8)";
			ctx.lineWidth = 3;

			// Top Left
			ctx.beginPath();
			ctx.moveTo(pad, pad + len);
			ctx.lineTo(pad, pad);
			ctx.lineTo(pad + len, pad);
			ctx.stroke();

			// Top Right
			ctx.beginPath();
			ctx.moveTo(width - pad, pad + len);
			ctx.lineTo(width - pad, pad);
			ctx.lineTo(width - pad - len, pad);
			ctx.stroke();

			// Bottom Left
			ctx.beginPath();
			ctx.moveTo(pad, height - pad - len);
			ctx.lineTo(pad, height - pad);
			ctx.lineTo(pad + len, height - pad);
			ctx.stroke();

			// Bottom Right
			ctx.beginPath();
			ctx.moveTo(width - pad, height - pad - len);
			ctx.lineTo(width - pad, height - pad);
			ctx.lineTo(width - pad - len, height - pad);
			ctx.stroke();

			// 4. Draw glowing laser scanner line
			ctx.shadowColor = "rgba(34, 197, 94, 0.95)";
			ctx.shadowBlur = 12;
			ctx.strokeStyle = "rgba(34, 197, 94, 0.9)";
			ctx.lineWidth = 3.5;
			ctx.beginPath();
			ctx.moveTo(pad - 10, laserY);
			ctx.lineTo(width - pad + 10, laserY);
			ctx.stroke();

			// Reset shadow
			ctx.shadowColor = "transparent";
			ctx.shadowBlur = 0;

			// Laser movement
			laserY += 3.2 * laserDirection;
			if (laserY >= height - pad - 10) {
				laserDirection = -1;
			} else if (laserY <= pad + 10) {
				laserDirection = 1;
			}

			// 5. Draw running OCR digits and scanning indicators
			ctx.fillStyle = "rgba(34, 197, 94, 0.9)";
			ctx.font = "bold 11px monospace";
			ctx.fillText("SYS_STATUS: ACTIVE", pad, pad - 15);
			ctx.fillText("LIVESTOCK_OCR_AUTO_SCAN", width - pad - 150, pad - 15);

			const dots = ".".repeat((frameCount / 15) % 4);
			ctx.fillText(`SCANNING_TAG${dots}`, pad, height - pad + 20);

			// OCR Rolling text on bottom-right
			const ocrIndex = Math.floor(frameCount / 12) % ocrCodes.length;
			ctx.fillStyle = "rgba(34, 197, 94, 0.65)";
			ctx.fillText(
				`MOCK_RAW: ${ocrCodes[ocrIndex]}${Math.floor(Math.random() * 10)}`,
				width - pad - 130,
				height - pad + 20,
			);

			animationRef.current = scheduleScannerFrame(render);
			if (animationRef.current === null && !cancelled) {
				setScanStatus("no_match");
			}
		};

		animationRef.current = scheduleScannerFrame(render);
		if (animationRef.current === null) {
			deferScannerNoMatch(setScanStatus, () => !cancelled);
		}

		return () => {
			cancelled = true;
			cancelScannerFrame(animationRef.current);
			animationRef.current = null;
		};
	}, [isOpen, scanStatus]);

	if (!isOpen) return null;

	// Function to simulate scanner completion
	const triggerMockScanSuccess = () => {
		if (!targetCandidate) {
			setScanStatus("no_match");
			playScanFailure();
			triggerVibration(150);
			return;
		}

		// Simulate OCR Lock
		setScanStatus("success");
		setMatchedCow(targetCandidate);
		setScannedTag(targetCandidate.tagNumber);
		playScanSuccess();
		triggerVibration(80);
	};

	// Function to select another cow manually from simulated dropdown
	const handleSelectCowManually = (cowId) => {
		const cow = cattleList.find((c) => c.id === cowId);
		if (cow) {
			setMatchedCow(cow);
			setScannedTag(cow.tagNumber);
			setScanStatus("success");
			playScanSuccess();
			triggerVibration(80);
		}
	};

	// Close and open cow details modal in background
	const handleConfirm = () => {
		playTactileClick();
		if (matchedCow) {
			onSelect(matchedCow);
		}
		onClose();
	};

	const handleRetry = () => {
		playTactileClick();
		if (cattleList.length > 0) {
			const idx = Math.floor(Math.random() * cattleList.length);
			setTargetCandidate(cattleList[idx]);
		}
		setScanStatus("scanning");
		setMatchedCow(null);
		setScannedTag("");
	};

	return (
		<div
			className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn"
			role="dialog"
			aria-modal="true"
			aria-labelledby="scanner-modal-title"
			aria-describedby="scanner-modal-description"
		>
			<div
				className="w-full max-w-[480px] clay-surface rounded-[32px] overflow-hidden border border-emerald-500/30 flex flex-col shadow-[0_24px_50px_rgba(0,0,0,0.5)] animate-scaleIn"
				style={{
					background: "linear-gradient(135deg, var(--color-card), #162416)",
				}}
			>
				{/* Header */}
				<div className="flex justify-between items-center px-6 py-5 border-b border-emerald-500/10">
					<div className="flex items-center gap-2.5">
						<div className="p-2 rounded-xl bg-emerald-500/15 text-emerald-400">
							<Camera size={18} className="animate-pulse" aria-hidden="true" />
						</div>
						<h2
							id="scanner-modal-title"
							className="text-base font-extrabold text-foreground tracking-tight"
						>
							가상 이표 인식 스캐너
						</h2>
					</div>
					<button
						type="button"
						onClick={() => {
							playTactileClick();
							onClose();
						}}
						className="p-2 text-muted-foreground hover:text-foreground rounded-full hover:bg-white/10 transition-colors"
						title="이표 스캐너 닫기"
						aria-label="이표 스캐너 닫기"
					>
						<X size={18} aria-hidden="true" />
					</button>
				</div>

				<p id="scanner-modal-description" className="sr-only">
					이표번호를 스캔하거나 목록에서 개체를 선택해 상세 정보를 엽니다.
				</p>

				{/* Viewfinder block */}
				<div className="p-6 flex flex-col items-center justify-center flex-1">
					{scanStatus === "scanning" ? (
						<div className="relative w-full aspect-square max-w-[280px] rounded-2xl overflow-hidden border border-emerald-500/40 shadow-inner">
							<canvas
								ref={canvasRef}
								className="w-full h-full block"
								aria-hidden="true"
							/>

							{/* Scan Trigger Button overlayed on top of simulator */}
							<button
								type="button"
								onClick={triggerMockScanSuccess}
								aria-label="이표 자동 인식 실행"
								title="이표 자동 인식 실행"
								className="absolute inset-0 w-full h-full bg-transparent hover:bg-emerald-500/5 transition-colors cursor-pointer flex flex-col items-center justify-end pb-8 group"
							>
								<div className="px-5 py-2.5 bg-emerald-600/90 text-white rounded-full text-xs font-bold shadow-lg border border-emerald-400/30 group-hover:scale-105 transition-transform flex items-center gap-1.5 backdrop-blur-sm">
									<Camera size={14} aria-hidden="true" /> 이표 자동 인식
								</div>
							</button>
						</div>
					) : scanStatus === "success" ? (
						<div
							className="w-full text-center py-4 flex flex-col items-center animate-fadeIn"
							role="status"
							aria-live="polite"
							aria-atomic="true"
						>
							<div className="w-20 h-20 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-5 border border-emerald-500/40 shadow-[0_0_20px_rgba(16,185,129,0.3)] animate-scaleIn">
								<Check size={36} strokeWidth={3} aria-hidden="true" />
							</div>
							<h3 className="text-lg font-black text-emerald-400 mb-1.5">
								이표 인식 완료!
							</h3>
							<p className="text-[12px] text-muted-foreground mb-5">
								농림축산검역본부 표준 개체 감지
							</p>

							{/* Matched Cow Premium Display Card */}
							<div className="w-full p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-left mb-6 relative overflow-hidden shadow-md">
								<div className="absolute right-4 top-4 text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-500/25 text-emerald-300">
									{matchedCow?.gender === "암" ? "암소 ♀" : "수소 ♂"}
								</div>
								<div className="text-[13px] text-emerald-400 font-bold mb-1">
									이표번호: {matchedCow?.tagNumber}
								</div>
								<h4 className="text-xl font-bold text-foreground mb-3">
									{matchedCow?.name}
								</h4>
								<div className="grid grid-cols-2 gap-3 text-xs border-t border-emerald-500/20 pt-3">
									<div>
										<span className="text-muted-foreground block">상태</span>
										<span className="font-semibold text-foreground">
											{matchedCow?.status}
										</span>
									</div>
									<div>
										<span className="text-muted-foreground block">위치</span>
										<span className="font-semibold text-foreground">
											{matchedCow?.buildingId
												? `${matchedCow?.buildingId}동`
												: "미배정"}{" "}
											{matchedCow?.penNumber
												? `${matchedCow?.penNumber}번 칸`
												: ""}
										</span>
									</div>
									<div>
										<span className="text-muted-foreground block">
											현재 체중
										</span>
										<span className="font-semibold text-foreground">
											{matchedCow?.weight}kg
										</span>
									</div>
									<div>
										<span className="text-muted-foreground block">
											생년월일
										</span>
										<span className="font-semibold text-foreground">
											{formatScannerBirthDate(matchedCow?.birthDate)}
										</span>
									</div>
								</div>
							</div>
						</div>
					) : (
						<div
							className="w-full text-center py-6 flex flex-col items-center animate-fadeIn"
							role="status"
							aria-live="polite"
							aria-atomic="true"
						>
							<div className="w-16 h-16 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center mb-4 border border-amber-500/30">
								<AlertTriangle size={28} aria-hidden="true" />
							</div>
							<h3 className="text-base font-bold text-foreground mb-2">
								인식된 개체 정보가 없습니다
							</h3>
							<p className="text-xs text-muted-foreground max-w-xs mb-6 leading-relaxed">
								스캐너 프레임 안에 이표번호가 정확히 위치하지 않았거나 농장에
								등록되지 않은 번호입니다. 다시 스캔해 주세요.
							</p>
						</div>
					)}
				</div>

				{/* Dynamic drop-down for manual simulation choice */}
				{scanStatus === "scanning" && cattleList.length > 0 && (
					<div className="px-6 pb-2 text-center">
						<span className="text-[10px] text-muted-foreground block mb-2">
							시뮬레이션 전용: 강제 타겟 설정
						</span>
						<div className="flex gap-1.5 justify-center flex-wrap max-h-20 overflow-y-auto pb-2 scrollbar-thin">
							{cattleList.slice(0, 5).map((cow) => {
								const manualChoiceLabel = `${cow.name} 이표번호 끝자리 ${String(cow.tagNumber).slice(-4)} 개체로 스캐너 결과 지정`;
								return (
								<button
									key={cow.id}
									type="button"
									onClick={() => handleSelectCowManually(cow.id)}
									aria-label={manualChoiceLabel}
									title={manualChoiceLabel}
									className="px-2.5 py-1.5 bg-white/5 border border-white/10 hover:border-emerald-500/40 rounded-lg text-[10px] font-medium text-foreground hover:text-emerald-400 transition-all cursor-pointer"
								>
									{cow.name} ({String(cow.tagNumber).slice(-4)})
								</button>
								);
							})}
						</div>
					</div>
				)}

				{/* Footer actions */}
				<div className="px-6 py-5 bg-black/40 border-t border-emerald-500/10 flex gap-3">
					{scanStatus === "scanning" ? (
						<>
							<PremiumButton
								type="button"
								variant="ghost"
								onClick={() => {
									playTactileClick();
									onClose();
								}}
								aria-label="이표 스캐너 닫기"
								title="이표 스캐너 닫기"
								className="flex-1 text-xs py-3 border border-white/10 rounded-[16px] text-muted-foreground hover:text-foreground font-bold hover:bg-white/5"
							>
								닫기
							</PremiumButton>
							<PremiumButton
								type="button"
								onClick={triggerMockScanSuccess}
								aria-label="모의 이표 스캔 실행"
								title="모의 이표 스캔 실행"
								className="flex-1 text-xs py-3 bg-emerald-600 border border-emerald-400/30 rounded-[16px] text-white font-bold shadow-[0_4px_12px_rgba(16,185,129,0.2)] hover:bg-emerald-500"
							>
								모의 스캔 수행
							</PremiumButton>
						</>
					) : (
						<>
							<PremiumButton
								type="button"
								variant="ghost"
								onClick={handleRetry}
								aria-label="이표 다시 스캔하기"
								title="이표 다시 스캔하기"
								className="flex-1 text-xs py-3 border border-white/10 rounded-[16px] text-foreground hover:text-emerald-400 font-bold hover:bg-white/5 flex items-center justify-center gap-1.5"
							>
								<RefreshCw size={13} aria-hidden="true" /> 다시 스캔
							</PremiumButton>
							{scanStatus === "success" && (
								<PremiumButton
									type="button"
									onClick={handleConfirm}
									aria-label={`${matchedCow?.name ?? "선택한 개체"} 상세 정보 보기`}
									title={`${matchedCow?.name ?? "선택한 개체"} 상세 정보 보기`}
									className="flex-1 text-xs py-3 bg-emerald-600 border border-emerald-400/30 rounded-[16px] text-white font-bold shadow-[0_4px_12px_rgba(16,185,129,0.2)] hover:bg-emerald-500 flex items-center justify-center gap-1.5"
								>
									<Eye size={13} aria-hidden="true" /> 정보 상세 보기
								</PremiumButton>
							)}
						</>
					)}
				</div>
			</div>
		</div>
	);
}
