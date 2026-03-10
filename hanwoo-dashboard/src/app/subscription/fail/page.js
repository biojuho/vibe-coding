'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { Suspense } from 'react';

function FailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  return (
    <div style={{ padding: "40px", textAlign: "center", fontFamily: "'Noto Sans KR', sans-serif" }}>
      <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#D32F2F" }}>결제 실패 😢</h1>
      <p style={{ marginTop: "10px", color: "#666" }}>{searchParams.get("message") || "알 수 없는 오류가 발생했습니다."}</p>
      <p style={{ marginTop: "4px", fontSize: "12px", color: "#999" }}>Code: {searchParams.get("code")}</p>
      
      <button 
        onClick={() => router.back()}
        style={{ marginTop: "20px", padding: "10px 20px", background: "#333", color: "white", borderRadius: "8px", border: "none", cursor: "pointer" }}
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
