'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { Suspense } from 'react';

function FailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  return (
    <div style={{ padding: "56px 24px", textAlign: "center", fontFamily: "var(--font-sans-custom)", color: "var(--color-text)" }}>
      <h1 style={{ fontSize: "28px", fontWeight: 700, color: "var(--color-danger)", fontFamily: "var(--font-display-custom)" }}>결제 실패 😢</h1>
      <p style={{ marginTop: "10px", color: "var(--color-text-secondary)" }}>{searchParams.get("message") || "알 수 없는 오류가 발생했습니다."}</p>
      <p style={{ marginTop: "4px", fontSize: "12px", color: "var(--color-text-muted)" }}>Code: {searchParams.get("code")}</p>
      
      <button 
        onClick={() => router.back()}
        style={{ marginTop: "20px", padding: "12px 22px", background: "var(--surface-gradient-primary)", color: "white", borderRadius: "18px", border: "1px solid var(--color-surface-stroke)", cursor: "pointer", boxShadow: "var(--shadow-button-primary)" }}
      >
        다시 시도하기
      </button>
    </div>
  );
}

export default function FailPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <FailContent />
        </Suspense>
    );
}
