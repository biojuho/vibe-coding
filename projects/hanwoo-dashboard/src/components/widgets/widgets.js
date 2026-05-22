import {
	BarChart3,
	Boxes,
	CalendarDays,
	Home,
	Settings,
	Sprout,
	Stethoscope,
	Truck,
} from "lucide-react";
import { PremiumCard, PremiumCardContent } from "@/components/ui/premium-card";
import {
	calcTHI,
	formatForecastDateLabel,
	getLivestockWeatherAlerts,
	getTHILevel,
	getWeatherDesc,
	getWeatherIcon,
	toFiniteNumber,
} from "@/lib/utils";

export function TabBar({ activeTab, onTabChange }) {
	const tabs = [
		{ id: "home", label: "홈", icon: Home },
		{ id: "feed", label: "사료", icon: Sprout },
		{ id: "calving", label: "분만", icon: Stethoscope },
		{ id: "sales", label: "출하", icon: Truck },
		{ id: "inventory", label: "재고", icon: Boxes },
		{ id: "analysis", label: "분석", icon: BarChart3 },
		{ id: "schedule", label: "일정", icon: CalendarDays },
		{ id: "settings", label: "설정", icon: Settings },
	];
	return (
		<nav className="tab-bar" aria-label="대시보드 메뉴">
			{tabs.map((t) => {
				const isActive = activeTab === t.id;
				const Icon = t.icon;
				return (
					<button
						key={t.id}
						type="button"
						onClick={() => onTabChange(t.id)}
						className={`tab-item ${isActive ? "active" : ""}`}
						aria-current={isActive ? "page" : undefined}
						style={{
							color: isActive
								? "var(--color-primary-custom)"
								: "var(--color-text-muted)",
						}}
					>
						<span
							className="tab-icon"
							style={{
								transform: isActive
									? "scale(1.2) translateY(-3px)"
									: "scale(1)",
								transition: "transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)",
								filter: isActive
									? "drop-shadow(0 2px 4px rgba(0,0,0,0.15))"
									: "none",
							}}
						>
							<Icon
								size={22}
								strokeWidth={isActive ? 2.5 : 2}
								aria-hidden="true"
							/>
						</span>
						<span
							className="tab-label"
							style={{
								opacity: isActive ? 1 : 0.65,
								transition: "opacity 0.25s ease, font-weight 0.15s ease",
							}}
						>
							{t.label}
						</span>
					</button>
				);
			})}
		</nav>
	);
}

function normalizeWeatherForecast(forecast) {
	return Array.isArray(forecast)
		? forecast.filter((day) => day && typeof day === "object")
		: [];
}

export function WeatherWidget({ weather }) {
	if (!weather)
		return (
			<div
				className="weather-skeleton animate-fadeInUp"
				style={{ marginBottom: "16px" }}
			>
				{/* Temperature row hint */}
				<div className="skel-row">
					<div
						className="skel-block"
						style={{ width: "80px", height: "52px", borderRadius: "12px" }}
					/>
					<div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
						<div
							className="skel-block"
							style={{ width: "100px", height: "16px" }}
						/>
						<div
							className="skel-block"
							style={{ width: "70px", height: "12px" }}
						/>
					</div>
				</div>
				{/* Stats grid hint */}
				<div className="skel-grid">
					<div className="skel-stat" style={{ animationDelay: "0ms" }} />
					<div className="skel-stat" style={{ animationDelay: "100ms" }} />
					<div className="skel-stat" style={{ animationDelay: "200ms" }} />
					<div className="skel-stat" style={{ animationDelay: "300ms" }} />
				</div>
			</div>
		);
	if (weather.available === false)
		return (
			<div
				className="weather-card animate-fadeInUp"
				style={{ marginBottom: "16px" }}
			>
				<PremiumCard>
					<PremiumCardContent className="p-5">
						<div
							style={{ fontSize: "14px", fontWeight: 700, marginBottom: "8px" }}
						>
							날씨 확인 불가
						</div>
						<div style={{ fontSize: "13px", opacity: 0.82 }}>
							{weather.message || "지금은 날씨 데이터를 확인할 수 없습니다."}
						</div>
						<div style={{ fontSize: "11px", opacity: 0.6, marginTop: "8px" }}>
							{weather.locationName || "서울"}
						</div>
					</PremiumCardContent>
				</PremiumCard>
			</div>
		);
	const temp = toFiniteNumber(weather.temp);
	const humidity = toFiniteNumber(weather.humidity);
	const apparentTemp = toFiniteNumber(weather.apparentTemp, temp);
	const windSpeed = toFiniteNumber(weather.windSpeed);
	const tempMax = toFiniteNumber(weather.tempMax, temp);
	const tempMin = toFiniteNumber(weather.tempMin, temp);
	const precipitation = toFiniteNumber(weather.precipitation);
	const thi = calcTHI(temp, humidity);
	const thiLevel = getTHILevel(thi);
	const icon = getWeatherIcon(weather.weatherCode);
	const desc = getWeatherDesc(weather.weatherCode);
	const safeForecast = normalizeWeatherForecast(weather.forecast);

	return (
		<div style={{ marginBottom: "16px" }} className="animate-fadeInUp">
			<PremiumCard className="overflow-visible">
				<PremiumCardContent className="p-5">
					<div className="weather-icon-bg" aria-hidden="true">
						{icon}
					</div>
					<div
						style={{
							fontSize: "12px",
							opacity: 0.8,
							marginBottom: "8px",
							position: "relative",
						}}
					>
						<span aria-hidden="true">📍</span> {weather.locationName} ·{" "}
						{new Date().toLocaleTimeString("ko-KR", {
							hour: "2-digit",
							minute: "2-digit",
						})}{" "}
						기준
					</div>
					<div
						style={{
							display: "flex",
							alignItems: "flex-end",
							gap: "14px",
							marginBottom: "16px",
							position: "relative",
						}}
					>
						<span
							style={{
								fontSize: "52px",
								fontWeight: 800,
								fontFamily: "var(--font-display)",
								lineHeight: 1,
								textShadow: "0 4px 12px rgba(0,0,0,0.2)",
							}}
						>
							{Math.round(temp)}°
						</span>
						<div style={{ paddingBottom: "6px" }}>
							<div style={{ fontSize: "22px", marginBottom: "2px" }}>
								<span aria-hidden="true">{icon}</span> {desc}
							</div>
							<div style={{ fontSize: "13px", opacity: 0.75 }}>
								체감 {Math.round(apparentTemp)}°C
							</div>
						</div>
					</div>
					<div
						style={{
							display: "grid",
							gridTemplateColumns: "repeat(4,1fr)",
							gap: "10px",
						}}
					>
						{[
							{ i: "💧", l: "습도", v: `${humidity}%` },
							{ i: "🌬️", l: "풍속", v: `${windSpeed}m/s` },
							{
								i: "🌡️",
								l: "최고/최저",
								v: `${Math.round(tempMax)}°/${Math.round(tempMin)}°`,
							},
							{ i: "🌧️", l: "강수", v: `${precipitation}%` },
						].map((item, idx) => (
							<div
								key={idx}
								className="weather-stat"
								style={{ animationDelay: `${idx * 60}ms` }}
							>
								<div
									aria-hidden="true"
									style={{
										fontSize: "18px",
										marginBottom: "3px",
										lineHeight: 1,
									}}
								>
									{item.i}
								</div>
								<div
									style={{
										fontSize: "10px",
										opacity: 0.65,
										marginBottom: "3px",
										letterSpacing: "0.02em",
									}}
								>
									{item.l}
								</div>
								<div
									style={{
										fontSize: "15px",
										fontWeight: 800,
										fontFamily: "var(--font-display)",
										letterSpacing: "-0.02em",
									}}
								>
									{item.v}
								</div>
							</div>
						))}
					</div>
					{weather.message ? (
						<div
							style={{
								marginTop: "12px",
								padding: "10px 12px",
								borderRadius: "12px",
								background: "rgba(255,255,255,0.08)",
								fontSize: "12px",
								opacity: 0.9,
							}}
						>
							{weather.message}
						</div>
					) : null}
				</PremiumCardContent>
			</PremiumCard>
			<div
				style={{
					background: thiLevel.bg,
					borderRadius: "var(--radius-lg)",
					padding: "14px 18px",
					marginTop: "12px",
					border: `2px solid ${thiLevel.color}`,
					display: "flex",
					alignItems: "center",
					gap: "14px",
					transition: "all var(--transition-normal)",
				}}
			>
				<div
					style={{
						width: "52px",
						height: "52px",
						borderRadius: "50%",
						background: `linear-gradient(135deg, ${thiLevel.color}, ${thiLevel.color}dd)`,
						display: "flex",
						flexDirection: "column",
						alignItems: "center",
						justifyContent: "center",
						color: "white",
						flexShrink: 0,
						boxShadow: `0 4px 12px ${thiLevel.color}40`,
					}}
				>
					<span
						style={{
							fontSize: "16px",
							fontWeight: 800,
							fontFamily: "var(--font-display)",
							lineHeight: 1,
						}}
					>
						{Math.round(thi)}
					</span>
					<span style={{ fontSize: "8px", fontWeight: 600, opacity: 0.9 }}>
						THI
					</span>
				</div>
				<div>
					<div
						style={{ fontWeight: 700, fontSize: "15px", color: thiLevel.color }}
					>
						<span aria-hidden="true">🐂</span> 온열지수: {thiLevel.label}
					</div>
					<div
						style={{
							fontSize: "12px",
							color: "var(--color-text-secondary)",
							marginTop: "2px",
						}}
					>
						{thiLevel.desc}
					</div>
				</div>
			</div>

			{/* 3-Day Forecast */}
			{safeForecast.length > 0 && (
				<div
					style={{
						background: "var(--color-bg-card)",
						borderRadius: "var(--radius-lg)",
						padding: "14px 18px",
						marginTop: "12px",
						border: "1px solid var(--color-border)",
					}}
				>
					<div
						style={{
							fontSize: "13px",
							fontWeight: 700,
							color: "var(--color-text)",
							marginBottom: "10px",
						}}
					>
						<span aria-hidden="true">📅</span> 3일 예보
					</div>
					<div
						style={{
							display: "grid",
							gridTemplateColumns: `repeat(${safeForecast.length},1fr)`,
							gap: "10px",
						}}
					>
						{safeForecast.map((day, idx) => {
							const dayLabel =
								idx === 0
									? "오늘"
									: formatForecastDateLabel(day.date, {
											weekday: "short",
											month: "short",
											day: "numeric",
										});
							return (
								<div
									key={day.date}
									style={{
										textAlign: "center",
										padding: "10px 6px",
										background: "var(--color-border-light)",
										borderRadius: "var(--radius-md)",
										transition: "all var(--transition-fast)",
									}}
								>
									<div
										style={{
											fontSize: "11px",
											color: "var(--color-text-muted)",
											marginBottom: "4px",
										}}
									>
										{dayLabel}
									</div>
									<div
										aria-label={getWeatherDesc(day.weatherCode)}
										style={{ fontSize: "24px", marginBottom: "4px" }}
									>
										{getWeatherIcon(day.weatherCode)}
									</div>
									<div
										style={{
											fontSize: "13px",
											fontWeight: 700,
											fontFamily: "var(--font-display)",
											color: "var(--color-text)",
										}}
									>
										{Math.round(toFiniteNumber(day.tempMax))}° /{" "}
										{Math.round(toFiniteNumber(day.tempMin))}°
									</div>
									{day.precipProb > 0 && (
										<div
											style={{
												fontSize: "10px",
												color: "var(--color-info)",
												marginTop: "2px",
											}}
										>
											<span aria-hidden="true">🌧</span> 강수 {day.precipProb}%
										</div>
									)}
								</div>
							);
						})}
					</div>
				</div>
			)}

			{/* Livestock Weather Alerts */}
			{(() => {
				const alerts = getLivestockWeatherAlerts(safeForecast);
				if (alerts.length === 0) return null;
				return (
					<div
						style={{
							background: "var(--color-warning-light)",
							border: "1px solid var(--color-warning)",
							borderRadius: "var(--radius-lg)",
							padding: "12px 16px",
							marginTop: "10px",
						}}
					>
						<div
							style={{
								fontSize: "12px",
								fontWeight: 700,
								color: "var(--color-warning)",
								marginBottom: "6px",
							}}
						>
							<span aria-hidden="true">🐄</span> 가축 기상 경고
						</div>
						{alerts.map((a, i) => (
							<div
								key={i}
								style={{
									fontSize: "12px",
									color: "var(--color-text)",
									padding: "3px 0",
								}}
							>
								<span aria-hidden="true">{a.icon}</span> {a.msg}
							</div>
						))}
					</div>
				);
			})()}
		</div>
	);
}
