'use client';

import PaymentWidget from '@/components/payment/PaymentWidget';
import { useState } from 'react';

const clientKey = "test_ck_D5GePWvyJnrK0W0k6q8gLzN97Eoq"; // Test Client Key
const customerKey = "customer_123456"; // Should be User ID or unique key

export default function SubscriptionPage() {
  return (
    <div style={{ maxWidth: "600px", margin: "0 auto", padding: "40px 20px", fontFamily: "'Noto Sans KR', sans-serif" }}>
      <h1 style={{ fontSize: "24px", fontWeight: "800", marginBottom: "10px", color: "#3E2F1C" }}>Joolife 프리미엄 구독</h1>
      <p style={{ marginBottom: "30px", color: "#666" }}>월 9,900원으로 스마트한 농장 관리를 시작하세요.</p>
      
      <PaymentWidget 
        clientKey={clientKey}
        customerKey={customerKey}
        amount={9900}
      />
    </div>
  );
}
