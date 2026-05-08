import { NextResponse } from 'next/server';

import { requireAuthenticatedSession, isAuthenticationError } from '@/lib/auth-guard';
import { PREMIUM_SUBSCRIPTION, buildCustomerKey, buildOrderId } from '@/lib/subscription';


export async function POST(req) {
  try {
    const session = await requireAuthenticatedSession();
    const body = await req.json();
    const amount = Number(body?.amount ?? PREMIUM_SUBSCRIPTION.amount);
    const customerKey = buildCustomerKey(session.user.id);

    if (customerKey !== body?.customerKey) {
      return NextResponse.json(
        { success: false, message: 'Customer key mismatch.' },
        { status: 403 }
      );
    }

    if (amount !== PREMIUM_SUBSCRIPTION.amount) {
      return NextResponse.json(
        { success: false, message: 'Unexpected payment amount.' },
        { status: 400 }
      );
    }

    return NextResponse.json({
      success: true,
      orderId: buildOrderId(customerKey),
      orderName: body?.orderName || PREMIUM_SUBSCRIPTION.displayName,
      customerName: body?.customerName || session.user.name || 'Joolife User',
      customerEmail: body?.customerEmail || null,
      amount,
    });
  } catch (error) {
    if (isAuthenticationError(error)) {
      return NextResponse.json({ success: false, message: error.message }, { status: 401 });
    }

    console.error('Payment Prepare Error:', error);
    return NextResponse.json(
      { success: false, message: error.message || 'Payment preparation failed.' },
      { status: 400 }
    );
  }
}
