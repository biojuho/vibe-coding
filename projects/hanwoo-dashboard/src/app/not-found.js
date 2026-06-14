/* eslint-disable @next/next/no-html-link-for-pages -- Dashboard recovery must use document navigation so auth proxy redirect fragments are preserved. */
import { Compass } from "lucide-react";

export const metadata = {
	title: "페이지를 찾을 수 없습니다 · Joolife",
};

export default function NotFound() {
	return (
		<main className="login-shell" id="main-content">
			<section
				className="login-card status-card"
				aria-labelledby="not-found-title"
			>
				<div className="login-brand">
					<div className="login-mark" aria-hidden="true">
						<Compass size={26} strokeWidth={2.2} aria-hidden="true" />
					</div>
					<div>
						<p className="login-eyebrow">Joolife 한우 운영</p>
						<h1 id="not-found-title" className="login-title">
							페이지를 찾을 수 없습니다
						</h1>
					</div>
				</div>

				<p className="login-copy">
					주소가 바뀌었거나 삭제된 화면일 수 있습니다. 대시보드로 돌아가 오늘의
					사육, 재고, 출하 업무를 이어서 관리해 주세요.
				</p>

				<div className="status-actions">
					{/* Use document navigation so the auth proxy owns protected redirects. */}
					<a
						href="/"
						aria-label="대시보드로 돌아가기"
						title="대시보드로 돌아가기"
						className="login-submit status-submit-link"
					>
						대시보드로 돌아가기
					</a>
				</div>
			</section>
		</main>
	);
}
