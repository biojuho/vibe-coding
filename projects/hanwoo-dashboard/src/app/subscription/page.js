import PaymentWidget from '@/components/payment/PaymentWidget';
import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { PREMIUM_SUBSCRIPTION, buildCustomerKey } from '@/lib/subscription';

const clientKey =
  process.env.NEXT_PUBLIC_TOSS_PAYMENTS_CLIENT_KEY || 'test_ck_D5GePWvyJnrK0W0k6q8gLzN97Eoq';

export const dynamic = 'force-dynamic';

export default async function SubscriptionPage() {
  const session = await requireAuthenticatedSession({ redirectToLogin: true });
  const customerKey = buildCustomerKey(session.user.id);

  return (
    <div
      style={{
        maxWidth: '640px',
        margin: '0 auto',
        padding: '48px 20px 120px',
        fontFamily: 'var(--font-sans-custom)',
        color: 'var(--color-text)',
      }}
    >
      <h1
        style={{
          fontSize: '28px',
          fontWeight: '800',
          marginBottom: '10px',
          color: 'var(--color-text)',
          fontFamily: 'var(--font-display-custom)',
          letterSpacing: '0.04em',
        }}
      >
        Joolife Premium Subscription
      </h1>
      <p style={{ marginBottom: '30px', color: 'var(--color-text-secondary)' }}>
        Start smarter farm management for KRW 9,900 per month.
      </p>

      <PaymentWidget
        clientKey={clientKey}
        customerKey={customerKey}
        amount={PREMIUM_SUBSCRIPTION.amount}
        orderName={PREMIUM_SUBSCRIPTION.displayName}
        customerName={session.user.name || session.user.username || 'Joolife User'}
      />
    </div>
  );
}
