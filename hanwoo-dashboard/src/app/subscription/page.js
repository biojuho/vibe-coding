'use client';

import PaymentWidget from '@/components/payment/PaymentWidget';
import { useState } from 'react';

const clientKey = "test_ck_D5GePWvyJnrK0W0k6q8gLzN97Eoq"; // Test Client Key
const customerKey = "customer_123456"; // Should be User ID or unique key

export default function SubscriptionPage() {
  return (
    <div style={{ maxWidth: "640px", margin: "0 auto", padding: "48px 20px 120px", fontFamily: "var(--font-sans-custom)", color: "var(--color-text)" }}>
      <h1 style={{ fontSize: "28px", fontWeight: "800", marginBottom: "10px", color: "var(--color-text)", fontFamily: "var(--font-display-custom)", letterSpacing: "0.04em" }}>Joolife 프리미엄 구독</h1>
      <p style={{ marginBottom: "30px", color: "var(--color-text-secondary)" }}>월 9,900원으로 스마트한 농장 관리를 시작하세요.</p>
      
      <PaymentWidget 
        clientKey={clientKey}
        customerKey={customerKey}
        amount={9900}
      />
    </div>
  );
}
