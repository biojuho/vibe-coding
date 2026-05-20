import Link from 'next/link';
import { Compass } from 'lucide-react';

export const metadata = {
  title: '페이지를 찾을 수 없어요 · Joolife',
};

export default function NotFound() {
  return (
    <main className="login-shell">
      <section className="login-card status-card" aria-labelledby="not-found-title">
        <div className="login-brand">
          <div className="login-mark" aria-hidden="true">
            <Compass size={26} strokeWidth={2.2} aria-hidden="true" />
          </div>
          <div>
            <p className="login-eyebrow">Joolife 한우 운영</p>
            <h1 id="not-found-title" className="login-title">페이지를 찾을 수 없어요</h1>
          </div>
        </div>

        <p className="login-copy">
          주소가 바뀌었거나 삭제된 화면일 수 있어요. 대시보드로 돌아가 오늘의 사육, 재고, 출하
          업무를 이어서 관리하세요.
        </p>

        <div className="status-actions">
          <Link href="/" className="login-submit status-submit-link">
            대시보드로 돌아가기
          </Link>
        </div>
      </section>
    </main>
  );
}
