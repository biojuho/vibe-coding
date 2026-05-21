'use client';

import { useEffect, useRef, useState } from 'react';
import { loadPaymentWidget } from '@tosspayments/payment-widget-sdk';
import { fetchWithTimeout, isTimeoutError, TimeoutError } from '@/lib/fetchWithTimeout';
import { buildGatewayErrorMessage, readJsonResponseSafely } from '@/lib/payment-confirmation.mjs';

const PAYMENT_WIDGET_TIMEOUT_MS = 15000;
const PAYMENT_PREPARE_TIMEOUT_MS = 10000;
const PAYMENT_WIDGET_TIMEOUT_MESSAGE = '결제창을 불러오는 시간이 길어지고 있습니다. 새로고침 후 다시 시도해 주세요.';
const PAYMENT_WIDGET_LOAD_ERROR_MESSAGE = '결제창을 불러오지 못했습니다. 새로고침 후 다시 시도해 주세요.';
const PAYMENT_WIDGET_PENDING_MESSAGE = '결제 수단을 불러오는 중입니다.';
const PAYMENT_PREPARING_MESSAGE = '결제를 준비하고 있습니다.';
const PAYMENT_REQUEST_ERROR_MESSAGE = '결제 요청을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.';
const PAYMENT_BUTTON_PREFIX = '결제하기';

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
  const paymentRequestInFlightRef = useRef(false);
  const [price] = useState(amount);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isWidgetReady, setIsWidgetReady] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const paymentButtonLabel = isSubmitting
    ? PAYMENT_PREPARING_MESSAGE
    : !isWidgetReady
      ? PAYMENT_WIDGET_PENDING_MESSAGE
      : `${PAYMENT_BUTTON_PREFIX} ${price.toLocaleString()}원`;

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
          PAYMENT_WIDGET_TIMEOUT_MESSAGE,
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
            ? PAYMENT_WIDGET_TIMEOUT_MESSAGE
            : PAYMENT_WIDGET_LOAD_ERROR_MESSAGE,
        );
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [clientKey, customerKey, price]);

  const handlePayment = async () => {
    if (paymentRequestInFlightRef.current) {
      return;
    }

    paymentRequestInFlightRef.current = true;

    try {
      setErrorMessage('');

      const paymentWidget = paymentWidgetRef.current;
      if (!paymentWidget) {
        throw new Error(PAYMENT_WIDGET_PENDING_MESSAGE);
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
          errorMessage: '결제 준비 시간이 길어지고 있습니다.',
        },
      );

      const { data: preparedPayment, rawText } = await readJsonResponseSafely(prepareResponse);
      if (!prepareResponse.ok || !preparedPayment?.success) {
        throw new Error(
          buildGatewayErrorMessage({
            payload: preparedPayment,
            rawText,
            fallbackMessage: '결제 요청을 준비하지 못했습니다.',
          }),
        );
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
      setErrorMessage(
        error.message === PAYMENT_WIDGET_PENDING_MESSAGE
          ? PAYMENT_WIDGET_PENDING_MESSAGE
          : PAYMENT_REQUEST_ERROR_MESSAGE,
      );
    } finally {
      paymentRequestInFlightRef.current = false;
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
        구독 결제
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
        aria-busy={isSubmitting}
        aria-label={paymentButtonLabel}
        title={paymentButtonLabel}
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
        {paymentButtonLabel}
      </button>
    </div>
  );
}
