'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

function SuccessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState("Processing...");

  useEffect(() => {
    const paymentKey = searchParams.get("paymentKey");
    const orderId = searchParams.get("orderId");
    const amount = searchParams.get("amount");

    if (paymentKey && orderId && amount) {
      fetch("/api/payments/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paymentKey, orderId, amount: parseInt(amount) })
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
            setStatus("Success");
            setTimeout(() => router.push("/"), 3000); 
        } else {
            setStatus("Verification Failed: " + data.message);
        }
      })
      .catch(err => setStatus("Error: " + err.message));
    }
  }, [searchParams, router]);

  return (
    <div style={{ padding: "40px", textAlign: "center", fontFamily: "'Noto Sans KR', sans-serif" }}>
      {status === "Success" ? (
        <div>
            <h1 style={{ fontSize: "24px", fontWeight: 700, color: "#4CAF50" }}>결제 성공! 🎉</h1>
            <p>Joolife 구독이 시작되었습니다.</p>
            <p>3초 후 대시보드로 이동합니다...</p>
        </div>
      ) : (
        <div>
            <h1 style={{ fontSize: "24px", fontWeight: 700 }}>{status}</h1>
        </div>
      )}
    </div>
  );
}

export default function SuccessPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SuccessContent />
    </Suspense>
  );
}
