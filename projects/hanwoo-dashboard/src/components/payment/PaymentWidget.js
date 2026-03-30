'use client';

import { useRef, useEffect, useState } from 'react';
import { loadPaymentWidget } from '@tosspayments/payment-widget-sdk';
import { useRouter } from 'next/navigation';

export default function PaymentWidget({ clientKey, customerKey, amount }) {
  const paymentWidgetRef = useRef(null);
  const paymentMethodsWidgetRef = useRef(null);
  const router = useRouter();
  const [price] = useState(amount);

  useEffect(() => {
    (async () => {
      // Initialize Widget
      const paymentWidget = await loadPaymentWidget(clientKey, customerKey);

      // Render Payment Methods
      const paymentMethodsWidget = paymentWidget.renderPaymentMethods(
        '#payment-widget',
        { value: price },
        { variantKey: 'DEFAULT' }
      );

      // Render Agreement
      paymentWidget.renderAgreement(
        '#agreement',
        { variantKey: 'AGREEMENT' }
      );

      paymentWidgetRef.current = paymentWidget;
      paymentMethodsWidgetRef.current = paymentMethodsWidget;
    })();
  }, [clientKey, customerKey, price]);

  const handlePayment = async () => {
    try {
        const paymentWidget = paymentWidgetRef.current;
        await paymentWidget.requestPayment({
            orderId: `order_${new Date().getTime()}`, // Unique ID
            orderName: "Joolife 프리미엄 구독 (월간)",
            customerName: "박주호", // Should come from user data
            customerEmail: "joolife@joolife.io.kr",
            successUrl: `${window.location.origin}/subscription/success`,
            failUrl: `${window.location.origin}/subscription/fail`,
        });
    } catch (e) {
        console.error("Payment Request Failed", e);
    }
  };

  return (
    <div style={{padding:"24px", background:"var(--surface-gradient)", borderRadius:"28px", border:"1px solid var(--color-surface-stroke)", boxShadow:"var(--shadow-lg)"}}>
      <h2 style={{fontSize:"18px", fontWeight:700, marginBottom:"20px"}}>구독 결제</h2>
      <div id="payment-widget" />
      <div id="agreement" />
      <button 
        onClick={handlePayment}
        style={{
            width:"100%", 
            padding:"16px", 
            background:"var(--surface-gradient-primary)",
            color:"white", 
            fontSize:"16px", 
            fontWeight:700, 
            border:"1px solid var(--color-surface-stroke)", 
            borderRadius:"18px", 
            marginTop:"20px", 
            cursor:"pointer",
            boxShadow:"var(--shadow-button-primary)"
        }}
      >
        {price.toLocaleString()}원 결제하기
      </button>
    </div>
  );
}
