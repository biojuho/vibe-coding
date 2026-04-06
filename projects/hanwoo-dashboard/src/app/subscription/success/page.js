'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { fetchWithTimeout } from '@/lib/fetchWithTimeout';

const CONFIRM_RETRY_DELAY_MS = 3000;
const CONFIRM_RETRY_LIMIT = 3;

function SuccessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState('Processing...');

  useEffect(() => {
    const paymentKey = searchParams.get('paymentKey');
    const orderId = searchParams.get('orderId');
    const amount = searchParams.get('amount');

    if (!paymentKey || !orderId || !amount) {
      return;
    }

    let cancelled = false;
    let retryTimer = null;

    const confirmPayment = async (attempt = 0) => {
      try {
        const response = await fetchWithTimeout(
          '/api/payments/confirm',
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paymentKey, orderId, amount: parseInt(amount, 10) }),
          },
          {
            timeoutMs: 15000,
            errorMessage: 'Payment verification timed out.',
          },
        );

        const data = await response.json();
        if (cancelled) {
          return;
        }

        if (data.success) {
          setStatus('Success');
          retryTimer = setTimeout(() => router.push('/'), 3000);
          return;
        }

        if (response.status === 202 && data.pending && attempt < CONFIRM_RETRY_LIMIT) {
          setStatus(`Verification pending. Retrying in ${CONFIRM_RETRY_DELAY_MS / 1000} seconds...`);
          retryTimer = setTimeout(() => {
            void confirmPayment(attempt + 1);
          }, CONFIRM_RETRY_DELAY_MS);
          return;
        }

        setStatus(`Verification Failed: ${data.message}`);
      } catch (error) {
        if (!cancelled) {
          setStatus(`Error: ${error.message}`);
        }
      }
    };

    void confirmPayment();

    return () => {
      cancelled = true;
      if (retryTimer) {
        clearTimeout(retryTimer);
      }
    };
  }, [searchParams, router]);

  return (
    <div
      style={{
        padding: '56px 24px',
        textAlign: 'center',
        fontFamily: 'var(--font-sans-custom)',
        color: 'var(--color-text)',
      }}
    >
      {status === 'Success' ? (
        <div>
          <h1
            style={{
              fontSize: '28px',
              fontWeight: 700,
              color: 'var(--color-success)',
              fontFamily: 'var(--font-display-custom)',
            }}
          >
            Payment confirmed
          </h1>
          <p>Your Joolife subscription is now active.</p>
          <p>Returning to the dashboard in 3 seconds.</p>
        </div>
      ) : (
        <div>
          <h1
            style={{
              fontSize: '28px',
              fontWeight: 700,
              fontFamily: 'var(--font-display-custom)',
            }}
          >
            {status}
          </h1>
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
