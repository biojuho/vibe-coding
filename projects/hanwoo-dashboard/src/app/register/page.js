"use client";

import { Loader2, LockKeyhole, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

const FIELD_STYLE = {
	width: "100%",
	padding: "12px 14px 12px 44px",
	border: "1.5px solid var(--color-surface-stroke)",
	borderRadius: "12px",
	background: "var(--color-surface-elevated)",
	color: "var(--color-text)",
	fontSize: "15px",
	outline: "none",
	boxSizing: "border-box",
};

const LABEL_STYLE = {
	display: "block",
	fontSize: "13px",
	fontWeight: 700,
	color: "var(--color-text-secondary)",
	marginBottom: "6px",
};

export default function RegisterPage() {
	const router = useRouter();
	const [username, setUsername] = useState("");
	const [password, setPassword] = useState("");
	const [confirm, setConfirm] = useState("");
	const [error, setError] = useState("");
	const [loading, setLoading] = useState(false);

	const handleSubmit = async (e) => {
		e.preventDefault();
		setError("");

		if (password !== confirm) {
			setError("비밀번호가 일치하지 않습니다.");
			return;
		}

		setLoading(true);
		try {
			const res = await fetch("/api/auth/register", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ username, password }),
			});
			const data = await res.json();
			if (!res.ok) {
				setError(data.error || "회원가입에 실패했습니다.");
				return;
			}
			router.push("/login?registered=1");
		} catch {
			setError("네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
		} finally {
			setLoading(false);
		}
	};

	return (
		<div
			style={{
				minHeight: "100dvh",
				display: "flex",
				alignItems: "center",
				justifyContent: "center",
				background: "var(--color-background)",
				padding: "24px",
			}}
		>
			<div
				style={{
					width: "100%",
					maxWidth: "400px",
					background: "var(--color-surface-elevated)",
					border: "1px solid var(--color-surface-stroke)",
					borderRadius: "24px",
					padding: "40px 32px",
				}}
			>
				<div style={{ textAlign: "center", marginBottom: "32px" }}>
					<div style={{ fontSize: "36px", marginBottom: "8px" }} aria-hidden="true">
						🐄
					</div>
					<h1
						style={{
							fontFamily: "var(--font-display-custom)",
							fontSize: "22px",
							fontWeight: 800,
							color: "var(--color-text)",
							marginBottom: "6px",
							letterSpacing: "0.04em",
						}}
					>
						Joolife 한우 시작하기
					</h1>
					<p style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>
						계정을 만들고 농장 관리를 시작하세요
					</p>
				</div>

				<form onSubmit={handleSubmit} noValidate>
					<div style={{ marginBottom: "16px" }}>
						<label htmlFor="reg-username" style={LABEL_STYLE}>
							아이디
						</label>
						<div style={{ position: "relative" }}>
							<UserRound
								size={16}
								style={{
									position: "absolute",
									left: "14px",
									top: "50%",
									transform: "translateY(-50%)",
									color: "var(--color-text-secondary)",
									pointerEvents: "none",
								}}
								aria-hidden="true"
							/>
							<input
								id="reg-username"
								type="text"
								autoComplete="username"
								autoCapitalize="none"
								spellCheck="false"
								placeholder="영문 소문자·숫자·밑줄, 3~30자"
								value={username}
								onChange={(e) => setUsername(e.target.value)}
								required
								style={FIELD_STYLE}
							/>
						</div>
					</div>

					<div style={{ marginBottom: "16px" }}>
						<label htmlFor="reg-password" style={LABEL_STYLE}>
							비밀번호
						</label>
						<div style={{ position: "relative" }}>
							<LockKeyhole
								size={16}
								style={{
									position: "absolute",
									left: "14px",
									top: "50%",
									transform: "translateY(-50%)",
									color: "var(--color-text-secondary)",
									pointerEvents: "none",
								}}
								aria-hidden="true"
							/>
							<input
								id="reg-password"
								type="password"
								autoComplete="new-password"
								placeholder="8자 이상"
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								required
								style={FIELD_STYLE}
							/>
						</div>
					</div>

					<div style={{ marginBottom: "24px" }}>
						<label htmlFor="reg-confirm" style={LABEL_STYLE}>
							비밀번호 확인
						</label>
						<div style={{ position: "relative" }}>
							<LockKeyhole
								size={16}
								style={{
									position: "absolute",
									left: "14px",
									top: "50%",
									transform: "translateY(-50%)",
									color: "var(--color-text-secondary)",
									pointerEvents: "none",
								}}
								aria-hidden="true"
							/>
							<input
								id="reg-confirm"
								type="password"
								autoComplete="new-password"
								placeholder="비밀번호 재입력"
								value={confirm}
								onChange={(e) => setConfirm(e.target.value)}
								required
								style={FIELD_STYLE}
							/>
						</div>
					</div>

					{error && (
						<div
							role="alert"
							style={{
								background: "color-mix(in srgb, var(--color-danger) 12%, transparent)",
								border: "1px solid color-mix(in srgb, var(--color-danger) 35%, transparent)",
								borderRadius: "10px",
								padding: "10px 14px",
								fontSize: "13px",
								color: "var(--color-danger)",
								marginBottom: "16px",
							}}
						>
							{error}
						</div>
					)}

					<button
						type="submit"
						disabled={loading}
						style={{
							width: "100%",
							padding: "13px",
							background: loading
								? "color-mix(in srgb, var(--color-primary-custom) 60%, transparent)"
								: "var(--color-primary-custom)",
							color: "#fff",
							border: "none",
							borderRadius: "12px",
							fontSize: "15px",
							fontWeight: 800,
							cursor: loading ? "not-allowed" : "pointer",
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
							gap: "8px",
						}}
					>
						{loading ? (
							<>
								<Loader2 size={16} className="animate-spin" aria-hidden="true" />
								계정 만드는 중...
							</>
						) : (
							"계정 만들기"
						)}
					</button>
				</form>

				<p
					style={{
						textAlign: "center",
						marginTop: "20px",
						fontSize: "13px",
						color: "var(--color-text-secondary)",
					}}
				>
					이미 계정이 있으신가요?{" "}
					<Link
						href="/login"
						style={{
							color: "var(--color-primary-custom)",
							fontWeight: 700,
							textDecoration: "none",
						}}
					>
						로그인
					</Link>
				</p>
			</div>
		</div>
	);
}
