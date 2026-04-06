'use client';

import { useEffect, useRef, useState } from 'react';
import { loadPaymentWidget } from '@tosspayments/payment-widget-sdk';
import { fetchWithTimeout, isTimeoutError, TimeoutError } from '@/lib/fetchWithTimeout';

const PAYMENT_WIDGET_TIMEOUT_MS = 15000;
const PAYMENT_PREPARE_TIMEOUT_MS = 10000;

function withTimeout(promise, timeoutMs, message) {
  let timeoutId = null;

  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = setTimeout(() => reject(new TimeoutError(message, timeoutMs)), timeoutMs);
  });

  return Promise.race([promise, timeoutPromise]).finally(() => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  });
}

export default function PaymentWidget({
  clientKey,
  customerKey,
  amount,
  orderName,
  customerName,
  customerEmail,
}) {
  const paymentWidgetRef = useRef(null);
  const [price] = useState(amount);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isWidgetReady, setIsWidgetReady] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let cancelled = false;

    paymentWidgetRef.current = null;
    setIsWidgetReady(false);
    setErrorMessage('');

    void (async () => {
      try {
        const paymentWidget = await withTimeout(
          loadPaymentWidget(clientKey, customerKey),
          PAYMENT_WIDGET_TIMEOUT_MS,
          'Payment widget initialization timed out.',
        );
        if (cancelled) {
          return;
        }

        paymentWidget.renderPaymentMethods(
          '#payment-widget',
          { value: price },
          { variantKey: 'DEFAULT' },
        );

        paymentWidget.renderAgreement('#agreement', { variantKey: 'AGREEMENT' });
        paymentWidgetRef.current = paymentWidget;
        setIsWidgetReady(true);
      } catch (error) {
        if (cancelled) {
          return;
        }

        console.error('Payment widget initialization failed', error);
        setErrorMessage(
          isTimeoutError(error)
            ? 'Payment widget initialization timed out. Please refresh and try again.'
            : 'Could not load the payment widget. Please refresh and try again.',
        );
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [clientKey, customerKey, price]);

  const handlePayment = async () => {
    try {
      setErrorMessage('');

      const paymentWidget = paymentWidgetRef.current;
      if (!paymentWidget) {
        throw new Error('Payment widget is still loading.');
      }

      setIsSubmitting(true);

      const prepareResponse = await fetchWithTimeout(
        '/api/payments/prepare',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            amount: price,
            customerKey,
            orderName,
            customerName,
            customerEmail,
          }),
        },
        {
          timeoutMs: PAYMENT_PREPARE_TIMEOUT_MS,
          errorMessage: 'Payment preparation timed out.',
        },
      );

      const preparedPayment = await prepareResponse.json();
      if (!prepareResponse.ok || !preparedPayment.success) {
        throw new Error(preparedPayment.message || 'Failed to prepare payment request.');
      }

      const requestPayload = {
        orderId: preparedPayment.orderId,
        orderName: preparedPayment.orderName,
        customerName: preparedPayment.customerName,
        successUrl: `${window.location.origin}/subscription/success`,
        failUrl: `${window.location.origin}/subscription/fail`,
      };

      if (preparedPayment.customerEmail) {
        requestPayload.customerEmail = preparedPayment.customerEmail;
      }

      await paymentWidget.requestPayment(requestPayload);
    } catch (error) {
      console.error('Payment Request Failed', error);
      setErrorMessage(error.message || 'Payment request failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        padding: '24px',
        background: 'var(--surface-gradient)',
        borderRadius: '28px',
        border: '1px solid var(--color-surface-stroke)',
        boxShadow: 'var(--shadow-lg)',
      }}
    >
      <h2 style={{ fontSize: '18px', fontWeight: 700, marginBottom: '20px' }}>
        Subscription checkout
      </h2>
      {errorMessage ? (
        <p
          role="alert"
          style={{
            marginBottom: '16px',
            borderRadius: '16px',
            padding: '12px 14px',
            background: 'color-mix(in srgb, var(--color-danger, #dc2626) 14%, white 86%)',
            color: 'var(--color-danger, #991b1b)',
            fontSize: '14px',
            fontWeight: 600,
          }}
        >
          {errorMessage}
        </p>
      ) : null}
      <div id="payment-widget" />
      <div id="agreement" />
      <button
        type="button"
        onClick={handlePayment}
        disabled={isSubmitting || !isWidgetReady}
        style={{
          width: '100%',
          padding: '16px',
          background: 'var(--surface-gradient-primary)',
          color: 'white',
          fontSize: '16px',
          fontWeight: 700,
          border: '1px solid var(--color-surface-stroke)',
          borderRadius: '18px',
          marginTop: '20px',
          cursor: isSubmitting || !isWidgetReady ? 'wait' : 'pointer',
          boxShadow: 'var(--shadow-button-primary)',
          opacity: isSubmitting || !isWidgetReady ? 0.72 : 1,
        }}
      >
        {isSubmitting
          ? 'Preparing payment...'
          : !isWidgetReady
            ? 'Loading payment methods...'
            : `Pay KRW ${price.toLocaleString()}`}
      </button>
    </div>
  );
}
