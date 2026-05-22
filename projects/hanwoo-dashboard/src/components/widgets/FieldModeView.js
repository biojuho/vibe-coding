import {
	AlertTriangle,
	ArrowLeft,
	Camera,
	CheckCircle2,
	ClipboardList,
	Clock,
	Search,
	ShieldAlert,
	Sparkles,
	Thermometer,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
	playTactileClick,
	playTriumphantChime,
	triggerVibration,
} from "@/lib/audio";
import EarTagScannerModal from "./EarTagScannerModal";

const DEFAULT_CHECKLIST = [
	{
		id: "feed_check",
		title: "우사 급이통 청소 및 사료 배부 확인",
		icon: "🌾",
		detail: "오전 급여 후 남은 찌꺼기 및 사료 변질 여부",
	},
	{
		id: "bedding_check",
		title: "우방 깔짚(톱밥) 수분 상태 점검",
		icon: "🧹",
		detail: "축사 바닥 톱밥 오염도 측정 및 추가 보충 여부",
	},
	{
		id: "thi_monitor",
		title: "온습도 및 가축 열지수(THI) 모니터링",
		icon: "🌬️",
		detail: "THI 경보 확인 후 환풍기 풍량 및 안개분무 작동",
	},
	{
		id: "health_scan",
		title: "개체 거동 및 활력 관찰 (건강 점검)",
		icon: "🩺",
		detail: "절뚝임, 호흡 급박, 사료 섭취 거부 개체 식별",
	},
	{
		id: "breeding_focus",
		title: "임신/분만 예정우 상태 밀착 관찰",
		icon: "🍼",
		detail: "유방 팽창, 외음부 부종, 진통 개시 징후 점검",
	},
];

export default function FieldModeView({
	cattleList = [],
	buildings = [],
	ensureAllCattleLoaded,
	onSelect,
	onCloseFieldMode,
}) {
	const [searchQuery, setSearchQuery] = useState("");
	const [isScannerOpen, setIsScannerOpen] = useState(false);
	const [checklist, setChecklist] = useState(() => {
		if (typeof window !== "undefined") {
			const d = new Date();
			const todayKey = `joolife-field-checklist-${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
			const saved = localStorage.getItem(todayKey);
			if (saved) {
				try {
					return JSON.parse(saved);
				} catch (err) {
					// Fall through to default mapping
				}
			}
		}
		return DEFAULT_CHECKLIST.map((item) => ({ ...item, checked: false }));
	});
	const [loadingAllCattle, setLoadingAllCattle] = useState(
		!!ensureAllCattleLoaded,
	);
	const [showCelebration, setShowCelebration] = useState(false);
	const celebrationCanvasRef = useRef(null);

	// Get current date string (YYYY-MM-DD) for local checklist key
	const getTodayKey = () => {
		const d = new Date();
		return `joolife-field-checklist-${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
	};

	// Load checklist from localStorage on mount
	useEffect(() => {
		// 1. Fetch all cattle registry in the background to enable global search
		if (ensureAllCattleLoaded) {
			ensureAllCattleLoaded({ silent: true })
				.catch(() => {})
				.finally(() => setLoadingAllCattle(false));
		}

		// 2. Perform daily checklist initialization side effects (cleanup old, write current if missing)
		if (typeof window !== "undefined") {
			const todayKey = getTodayKey();
			const saved = localStorage.getItem(todayKey);
			if (!saved) {
				// Clean up old checklist keys safely without index shifting
				try {
					const keysToRemove = [];
					for (let i = 0; i < localStorage.length; i++) {
						const key = localStorage.key(i);
						if (key && key.startsWith("joolife-field-checklist-")) {
							keysToRemove.push(key);
						}
					}
					keysToRemove.forEach((key) => {
						try {
							localStorage.removeItem(key);
						} catch {}
					});
				} catch {}

				const fresh = DEFAULT_CHECKLIST.map((item) => ({
					...item,
					checked: false,
				}));
				localStorage.setItem(todayKey, JSON.stringify(fresh));
			}
		}
	}, [ensureAllCattleLoaded]);

	// Particle celebration effect for daily checklist 100% completion
	useEffect(() => {
		if (!showCelebration) return;

		const canvas = celebrationCanvasRef.current;
		if (!canvas) return;
		const ctx = canvas.getContext("2d");

		let width = (canvas.width = window.innerWidth);
		let height = (canvas.height = window.innerHeight);

		const handleResize = () => {
			if (!canvas) return;
			width = canvas.width = window.innerWidth;
			height = canvas.height = window.innerHeight;
		};
		window.addEventListener("resize", handleResize);

		const particles = [];
		const colors = [
			"rgba(245, 158, 11, 0.85)", // Gold/Amber
			"rgba(34, 197, 94, 0.85)", // Emerald Green
			"rgba(251, 146, 60, 0.85)", // Orange
			"rgba(252, 211, 77, 0.9)", // Light Amber
		];

		const createFirework = (x, y) => {
			const count = 35;
			for (let i = 0; i < count; i++) {
				const angle = Math.random() * Math.PI * 2;
				const speed = Math.random() * 8 + 3;
				particles.push({
					x: x,
					y: y,
					vx: Math.cos(angle) * speed,
					vy: Math.sin(angle) * speed - 2,
					size: Math.random() * 6 + 3,
					color: colors[Math.floor(Math.random() * colors.length)],
					alpha: 1,
					decay: Math.random() * 0.015 + 0.01,
				});
			}
		};

		createFirework(width / 2, height * 0.85);
		const t1 = setTimeout(
			() => createFirework(width * 0.25, height * 0.6),
			250,
		);
		const t2 = setTimeout(
			() => createFirework(width * 0.75, height * 0.6),
			400,
		);

		let animationId;
		const animate = () => {
			ctx.clearRect(0, 0, width, height);

			for (let i = particles.length - 1; i >= 0; i--) {
				const p = particles[i];
				p.x += p.vx;
				p.y += p.vy;
				p.vy += 0.15;
				p.vx *= 0.98;
				p.alpha -= p.decay;

				if (p.alpha <= 0) {
					particles.splice(i, 1);
					continue;
				}

				ctx.save();
				ctx.globalAlpha = p.alpha;
				ctx.fillStyle = p.color;
				ctx.shadowBlur = 8;
				ctx.shadowColor = p.color;

				ctx.beginPath();
				ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
				ctx.fill();
				ctx.restore();
			}

			if (particles.length > 0) {
				animationId = requestAnimationFrame(animate);
			} else {
				setShowCelebration(false);
			}
		};

		animationId = requestAnimationFrame(animate);

		const timer = setTimeout(() => {
			setShowCelebration(false);
		}, 4500);

		return () => {
			window.removeEventListener("resize", handleResize);
			cancelAnimationFrame(animationId);
			clearTimeout(timer);
			clearTimeout(t1);
			clearTimeout(t2);
		};
	}, [showCelebration]);

	// Handle checklist toggling
	const handleToggleCheck = (itemId) => {
		playTactileClick();
		triggerVibration(30);

		let allCompletedAfterToggle = false;

		const updated = checklist.map((item) => {
			if (item.id === itemId) {
				return { ...item, checked: !item.checked };
			}
			return item;
		});

		const previouslyCompletedAll =
			checklist.length > 0 && checklist.every((item) => item.checked);
		const currentlyCompletedAll =
			updated.length > 0 && updated.every((item) => item.checked);

		if (!previouslyCompletedAll && currentlyCompletedAll) {
			allCompletedAfterToggle = true;
		}

		setChecklist(updated);

		if (typeof window !== "undefined") {
			localStorage.setItem(getTodayKey(), JSON.stringify(updated));
		}

		if (allCompletedAfterToggle) {
			playTriumphantChime();
			triggerVibration(100);
			setShowCelebration(true);
		}
	};

	// Safe global filter: match name or 12-digit tag (specifically matching last 4/5 digits)
	const filteredCattle = useMemo(() => {
		const q = searchQuery.trim().toLowerCase();
		if (!q) return [];

		return cattleList.filter((cow) => {
			const tagStr = String(cow.tagNumber || "");
			const nameStr = String(cow.name || "").toLowerCase();

			// Match full or partial name
			if (nameStr.includes(q)) return true;

			// Match full or partial tag number (especially the suffix)
			if (tagStr.includes(q)) return true;

			// Extract last 4 and 5 digits specifically for farmer shortcut mapping
			const last4 = tagStr.slice(-4);
			const last5 = tagStr.slice(-5);
			if (last4.includes(q) || last5.includes(q)) return true;

			return false;
		});
	}, [cattleList, searchQuery]);

	// Checklist completion statistics
	const checklistStats = useMemo(() => {
		if (checklist.length === 0) return { checked: 0, total: 0, pct: 0 };
		const checked = checklist.filter((item) => item.checked).length;
		const total = checklist.length;
		const pct = Math.round((checked / total) * 100);
		return { checked, total, pct };
	}, [checklist]);

	// Total critical alerts mapping (calving and estrus)
	const statsSummary = useMemo(() => {
		const estrusCount = cattleList.filter((cow) => {
			if (!cow.lastEstrus) return false;
			const days = Math.floor(
				(new Date() - new Date(cow.lastEstrus)) / (1000 * 60 * 60 * 24),
			);
			return days >= 19 && days <= 23; // standard estrus cycle alarm range
		}).length;

		const calvingCount = cattleList.filter(
			(cow) => cow.status === "임신우",
		).length;

		return { estrusCount, calvingCount };
	}, [cattleList]);

	// Format ear-tag display highlighting last 4 digits
	const formatTagNumber = (tag = "") => {
		if (tag.length < 4) return tag;
		const prefix = tag.slice(0, -4);
		const suffix = tag.slice(-4);
		return (
			<span className="font-mono tracking-tight text-xs opacity-75">
				{prefix}
				<strong
					className="text-[var(--color-primary-custom)] font-extrabold text-sm ml-0.5"
					style={{ textShadow: "0 0 8px rgba(245, 158, 11, 0.4)" }}
				>
					{suffix}
				</strong>
			</span>
		);
	};

	return (
		<div
			className="field-mode-wrapper min-h-screen text-amber-50"
			style={{
				background: "radial-gradient(circle at 50% 0%, #1c2b1c, #0a0e0a)",
				fontFamily: "var(--font-sans)",
				paddingBottom: "80px",
			}}
		>
			{/* Top HUD Header with glowing effect */}
			<div
				className="sticky top-0 z-40 px-5 py-4 flex justify-between items-center border-b border-amber-500/20 backdrop-blur-lg"
				style={{ background: "rgba(10, 14, 10, 0.85)" }}
			>
				<button
					type="button"
					onClick={() => {
						playTactileClick();
						onCloseFieldMode();
					}}
					className="flex items-center gap-1.5 px-3 py-2 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-xl text-xs font-bold transition-all hover:bg-amber-500/20 cursor-pointer"
				>
					<ArrowLeft size={14} /> 일반 모드
				</button>

				<div className="text-center">
					<div className="text-[9px] text-amber-500/80 font-black tracking-widest uppercase">
						Smart Field Overlay
					</div>
					<h2 className="text-sm font-black text-amber-300 tracking-tight flex items-center gap-1.5 justify-center">
						현장 스마트 모드{" "}
						<span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-ping" />
					</h2>
				</div>

				<div className="text-xs font-mono text-amber-400 font-bold bg-amber-500/10 border border-amber-500/30 px-3 py-2 rounded-xl">
					{new Date().toLocaleTimeString("ko-KR", {
						hour: "2-digit",
						minute: "2-digit",
					})}
				</div>
			</div>

			<div className="max-w-[540px] mx-auto px-5 pt-6 flex flex-col gap-6">
				{/* Onsite Weather & THI mini card */}
				<div
					className="p-5 rounded-[24px] border border-amber-500/20 flex justify-between items-center relative overflow-hidden"
					style={{
						background:
							"linear-gradient(135deg, rgba(28, 43, 28, 0.7), rgba(10, 14, 10, 0.8))",
					}}
				>
					<div className="flex items-center gap-3">
						<div className="w-12 h-12 rounded-2xl bg-amber-500/15 flex items-center justify-center text-2xl text-amber-400 border border-amber-500/20">
							🌡️
						</div>
						<div>
							<div className="text-xs text-amber-400/80 font-bold">
								농장 온습도 지수
							</div>
							<h3 className="text-base font-extrabold text-foreground mt-0.5">
								현장 기동성 극대화
							</h3>
						</div>
					</div>
					<div className="text-right">
						<span className="text-[10px] text-amber-500 block font-bold">
							오프라인 자가생존
						</span>
						<span className="text-xs px-2.5 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-full font-bold inline-block mt-1">
							정상 연결
						</span>
					</div>
				</div>

				{/* Global Search and Camera OCR Box */}
				<section
					aria-labelledby="global-search-title"
					className="flex flex-col gap-3"
				>
					<h3 id="global-search-title" className="sr-only">
						개체 초고속 검색
					</h3>
					<div className="flex gap-2">
						<div className="relative flex-1">
							<input
								type="text"
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								placeholder="이표번호 4자리 또는 소이름..."
								className="w-full pl-12 pr-4 py-4 rounded-[20px] bg-amber-950/20 border-2 border-amber-500/30 focus:border-amber-400 text-foreground placeholder:text-amber-500/60 font-bold text-sm focus:outline-none shadow-md transition-colors"
								style={{
									caretColor: "var(--color-primary-custom)",
								}}
							/>
							<Search
								className="absolute left-4 top-4.5 text-amber-500"
								size={18}
							/>

							{searchQuery && (
								<button
									type="button"
									onClick={() => {
										playTactileClick();
										setSearchQuery("");
									}}
									className="absolute right-4 top-4.5 text-xs text-amber-500 hover:text-amber-300 font-bold px-1.5 py-0.5 rounded"
								>
									지우기
								</button>
							)}
						</div>

						<button
							type="button"
							onClick={() => {
								playTactileClick();
								setIsScannerOpen(true);
							}}
							className="p-4 bg-amber-500 text-black border border-amber-400 rounded-[20px] hover:bg-amber-400 active:scale-95 transition-all shadow-md flex items-center justify-center flex-shrink-0 cursor-pointer"
							title="가상 이표 스캐너 열기"
							aria-label="가상 이표 스캐너 열기"
						>
							<Camera size={20} strokeWidth={2.5} />
						</button>
					</div>

					{/* Search Result Overlay List */}
					{searchQuery && (
						<div
							className="rounded-[24px] border border-amber-500/30 overflow-hidden shadow-xl"
							style={{ background: "rgba(10, 14, 10, 0.95)" }}
						>
							<div className="px-4.5 py-3 border-b border-amber-500/10 bg-amber-500/5 flex justify-between items-center">
								<span className="text-[11px] text-amber-400 font-black">
									검색 매칭 개체 ({filteredCattle.length}두)
								</span>
								{loadingAllCattle && (
									<span className="text-[10px] text-amber-400 animate-pulse">
										전체 로드 중...
									</span>
								)}
							</div>
							<div className="max-h-[300px] overflow-y-auto scrollbar-thin divide-y divide-amber-500/10">
								{filteredCattle.length > 0 ? (
									filteredCattle.map((cow) => (
										<button
											key={cow.id}
											type="button"
											onClick={() => {
												playTactileClick();
												onSelect(cow);
											}}
											className="w-full px-5 py-4 text-left hover:bg-amber-500/10 flex justify-between items-center transition-colors cursor-pointer group"
										>
											<div>
												<div className="flex items-center gap-2 mb-1.5">
													<span className="font-extrabold text-sm text-amber-200">
														{cow.name}
													</span>
													<span
														className="text-[10px] font-bold px-2 py-0.5 rounded-full border"
														style={{
															background: "rgba(245, 158, 11, 0.1)",
															borderColor: "rgba(245, 158, 11, 0.3)",
															color: "rgb(252, 211, 77)",
														}}
													>
														{cow.status}
													</span>
												</div>
												<div className="flex items-center gap-1.5 text-xs text-amber-400/70">
													<span>{formatTagNumber(cow.tagNumber)}</span>
													<span>·</span>
													<span>{cow.weight}kg</span>
													<span>·</span>
													<span>
														{cow.buildingId ? `${cow.buildingId}동` : "미지정"}{" "}
														{cow.penNumber ? `${cow.penNumber}번 칸` : ""}
													</span>
												</div>
											</div>
											<span className="text-amber-500 text-lg opacity-60 group-hover:opacity-100 group-hover:translate-x-1 transition-all">
												›
											</span>
										</button>
									))
								) : (
									<div className="px-5 py-8 text-center text-xs text-amber-500/50">
										<AlertTriangle
											size={20}
											className="mx-auto mb-2 text-amber-500/40"
										/>
										매칭되는 개체가 존재하지 않습니다.
									</div>
								)}
							</div>
						</div>
					)}
				</section>

				{/* Checklist Widget */}
				<section
					aria-labelledby="checklist-title"
					className="flex flex-col gap-3"
				>
					<div
						className="p-5 rounded-[28px] border border-amber-500/20 flex flex-col gap-4"
						style={{
							background:
								"linear-gradient(135deg, rgba(28, 43, 28, 0.6), rgba(10, 14, 10, 0.85))",
						}}
					>
						<div className="flex justify-between items-start">
							<div>
								<div className="text-[10px] text-amber-500 font-bold uppercase tracking-wide">
									Tactile stables list
								</div>
								<h3
									id="checklist-title"
									className="text-base font-extrabold text-amber-300 mt-0.5"
								>
									오늘의 축사 일일 점검
								</h3>
							</div>
							<div className="text-right">
								<span className="text-xl font-black text-amber-300">
									{checklistStats.pct}%
								</span>
								<span className="text-[10px] text-amber-500 block">
									완료 ({checklistStats.checked}/{checklistStats.total})
								</span>
							</div>
						</div>

						{/* Glowing progress track */}
						<div
							className="w-full h-2.5 bg-amber-950/40 rounded-full border border-amber-500/10 overflow-hidden relative"
							aria-hidden="true"
						>
							<span
								className="absolute left-0 top-0 h-full bg-amber-400 rounded-full transition-all duration-500 ease-out shadow-[0_0_10px_rgba(245,158,11,0.5)]"
								style={{ width: `${checklistStats.pct}%` }}
							/>
						</div>

						{/* Checklist tactile rows */}
						<div className="flex flex-col gap-2.5 mt-1">
							{checklist.map((item) => (
								<button
									key={item.id}
									type="button"
									onClick={() => handleToggleCheck(item.id)}
									className={`w-full text-left p-4.5 rounded-2xl border transition-all flex items-center justify-between gap-4 cursor-pointer group ${
										item.checked
											? "bg-amber-500/10 border-amber-500/40 shadow-inner"
											: "bg-white/5 border-white/5 hover:border-amber-500/20"
									}`}
								>
									<div className="flex items-center gap-3.5 flex-1 min-w-0">
										<span className="text-xl flex-shrink-0" aria-hidden="true">
											{item.icon}
										</span>
										<div className="min-w-0">
											<h4
												className={`text-[13px] font-bold tracking-tight leading-normal ${item.checked ? "text-amber-400 line-through opacity-65" : "text-foreground"}`}
											>
												{item.title}
											</h4>
											<p className="text-[11px] text-amber-500/60 mt-0.5 leading-relaxed truncate group-hover:text-amber-500/80 transition-colors">
												{item.detail}
											</p>
										</div>
									</div>
									<div
										className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
											item.checked
												? "bg-amber-500 border-amber-500 text-black font-black"
												: "border-amber-500/30"
										}`}
										aria-hidden="true"
									>
										{item.checked ? (
											<CheckCircle2 size={14} strokeWidth={3.5} />
										) : null}
									</div>
								</button>
							))}
						</div>
					</div>
				</section>

				{/* High-visibility counters block */}
				<section
					aria-labelledby="status-counters-title"
					className="grid grid-cols-2 gap-3.5"
				>
					<h3 id="status-counters-title" className="sr-only">
						축사 개체 모니터 카운터
					</h3>

					<div
						className="p-4.5 rounded-[24px] border border-amber-500/20"
						style={{
							background:
								"linear-gradient(135deg, rgba(28, 43, 28, 0.4), rgba(10, 14, 10, 0.8))",
						}}
					>
						<div className="text-[10px] text-amber-500/80 font-bold">
							전체 사육개체
						</div>
						<div className="text-2xl font-black text-amber-300 mt-1 font-mono tracking-tight">
							{cattleList.length}두
						</div>
						<div className="text-[10px] text-amber-500/60 mt-1">
							이표 검수 100% 완료
						</div>
					</div>

					<div
						className="p-4.5 rounded-[24px] border border-amber-500/20"
						style={{
							background:
								"linear-gradient(135deg, rgba(28, 43, 28, 0.4), rgba(10, 14, 10, 0.8))",
						}}
					>
						<div className="text-[10px] text-amber-500/80 font-bold">
							임신/분만 대기
						</div>
						<div className="text-2xl font-black text-amber-300 mt-1 font-mono tracking-tight">
							{statsSummary.calvingCount}두
						</div>
						<div className="text-[10px] text-amber-500/60 mt-1">
							가축 기상 경보 확인 요망
						</div>
					</div>
				</section>
			</div>

			{/* Embedded Ear Tag Scanner Modal */}
			<EarTagScannerModal
				isOpen={isScannerOpen}
				onClose={() => setIsScannerOpen(false)}
				cattleList={cattleList}
				onSelect={onSelect}
			/>

			{showCelebration && (
				<canvas
					ref={celebrationCanvasRef}
					className="fixed inset-0 pointer-events-none z-50 w-full h-full"
					style={{ mixBlendMode: "screen" }}
					aria-hidden="true"
				/>
			)}
		</div>
	);
}
