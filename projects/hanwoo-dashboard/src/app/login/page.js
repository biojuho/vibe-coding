"use client";

import {
	Eye,
	EyeOff,
	Loader2,
	LockKeyhole,
	ShieldCheck,
	UserRound,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import { useEffect, useRef, useState } from "react";
import { getSafeLoginRedirectTarget } from "@/lib/login-redirect.mjs";

const LOGIN_NAVIGATION_ERROR_MESSAGE =
	"로그인은 완료됐지만 대시보드로 이동하지 못했습니다. 새로고침 후 다시 시도해 주세요.";

export default function LoginPage() {
	const router = useRouter();
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState("");
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [showPassword, setShowPassword] = useState(false);
	const submitInFlightRef = useRef(false);

	const canSubmit =
		username.trim().length > 0 && password.length > 0 && !isSubmitting;
	const loginSubmitLabel = isSubmitting
		? "로그인 확인 중"
		: username.trim().length === 0
			? "아이디를 입력하면 로그인할 수 있습니다"
			: password.length === 0
				? "비밀번호를 입력하면 로그인할 수 있습니다"
				: "한우 대시보드 열기";
	const passwordToggleLabel = showPassword ? "비밀번호 숨기기" : "비밀번호 보기";
	const loginErrorId = "login-error-message";
	const usernameInputId = "login-username";
	const passwordInputId = "login-password";
	const isMountedRef = useRef(false);

	useEffect(() => {
		isMountedRef.current = true;
		return () => {
			isMountedRef.current = false;
			submitInFlightRef.current = false;
		};
	}, []);

	const handleSubmit = async (event) => {
		event.preventDefault();
		if (submitInFlightRef.current || !canSubmit) return;

		submitInFlightRef.current = true;
		setError("");
		setShowPassword(false);
		setIsSubmitting(true);

		try {
			const result = await signIn("credentials", {
				username: username.trim(),
				password,
				redirect: false,
			});

			if (result?.error) {
				if (isMountedRef.current) {
					setError("아이디 또는 비밀번호를 다시 확인해 주세요.");
				}
				return;
			}

			try {
				const redirectTarget = getSafeLoginRedirectTarget(window.location.href);
				router.push(redirectTarget);
				router.refresh();
			} catch (navigationError) {
				console.error("Login dashboard navigation failed:", navigationError);
				if (isMountedRef.current) {
					setError(LOGIN_NAVIGATION_ERROR_MESSAGE);
				}
			}
		} catch {
			if (isMountedRef.current) {
				setError("로그인을 완료하지 못했습니다. 네트워크 상태를 확인해 주세요.");
			}
		} finally {
			submitInFlightRef.current = false;
			if (isMountedRef.current) {
				setIsSubmitting(false);
			}
		}
	};

	return (
		<main className="login-shell">
			<section id="login" className="login-card" aria-labelledby="login-title">
				<div className="login-brand">
					<div className="login-mark" aria-hidden="true">
						<ShieldCheck size={26} strokeWidth={2.2} aria-hidden="true" />
					</div>
					<div>
						<p className="login-eyebrow">Joolife 한우 운영</p>
						<h1 id="login-title" className="login-title">
							한우 대시보드
						</h1>
					</div>
				</div>

				<p className="login-copy">
					오늘의 사육, 재고, 출하 업무를 이어서 관리해 주세요.
				</p>

				{/* 운영자 계정 안내 */}
				<div style={{
					backgroundColor: "rgba(99, 102, 241, 0.08)",
					border: "1px solid rgba(99, 102, 241, 0.2)",
					borderRadius: "8px",
					padding: "12px 16px",
					marginBottom: "20px",
					fontSize: "14px",
					color: "#818cf8",
					display: "flex",
					flexDirection: "column",
					gap: "4px"
				}}>
					<div style={{ fontWeight: "bold", display: "flex", alignItems: "center", gap: "6px" }}>
						<ShieldCheck size={16} strokeWidth={2.2} aria-hidden="true" /> 운영자 계정 안내
					</div>
					<div>발급된 관리자 아이디와 비밀번호로 로그인해 주세요.</div>
				</div>

				<form className="login-form" onSubmit={handleSubmit}>
					<div className="login-field">
						<label className="login-label" htmlFor={usernameInputId}>
							아이디
						</label>
						<span className="login-input-wrap">
							<UserRound
								className="login-input-icon"
								size={18}
								aria-hidden="true"
							/>
							<input
								id={usernameInputId}
								name="username"
								type="text"
								value={username}
								onChange={(event) => setUsername(event.target.value)}
								autoComplete="username"
								inputMode="text"
								placeholder="관리자 아이디"
								aria-label="아이디"
								aria-invalid={Boolean(error)}
								aria-describedby={error ? loginErrorId : undefined}
								className="login-input"
							/>
						</span>
					</div>

					<div className="login-field">
						<label className="login-label" htmlFor={passwordInputId}>
							비밀번호
						</label>
						<span className="login-input-wrap">
							<LockKeyhole
								className="login-input-icon"
								size={18}
								aria-hidden="true"
							/>
							<input
								id={passwordInputId}
								name="password"
								type={showPassword ? "text" : "password"}
								value={password}
								onChange={(event) => setPassword(event.target.value)}
								autoComplete="current-password"
								placeholder="비밀번호"
								aria-label="비밀번호"
								aria-invalid={Boolean(error)}
								aria-describedby={error ? loginErrorId : undefined}
								className="login-input login-input-password"
							/>
							<button
								type="button"
								className="login-password-toggle"
								onClick={() => setShowPassword((current) => !current)}
								aria-label={passwordToggleLabel}
								title={passwordToggleLabel}
							>
								{showPassword ? (
									<EyeOff size={18} aria-hidden="true" />
								) : (
									<Eye size={18} aria-hidden="true" />
								)}
							</button>
						</span>
					</div>

					{error ? (
						<div id={loginErrorId} className="login-error" role="alert">
							{error}
						</div>
					) : null}

					<button
						type="submit"
						className="login-submit"
						disabled={!canSubmit}
						aria-busy={isSubmitting}
						aria-label={loginSubmitLabel}
						title={loginSubmitLabel}
					>
						{isSubmitting ? (
							<Loader2 className="animate-spin" size={18} aria-hidden="true" />
						) : null}
						{isSubmitting ? "로그인 확인 중..." : "대시보드 열기"}
					</button>
				</form>

				<div className="login-status-row" aria-label="운영 상태">
					<span>보안 세션</span>
					<span>모바일 최적화</span>
					<span>오프라인 대기열</span>
				</div>
			</section>
		</main>
	);
}
