import { NextResponse } from 'next/server';
import prisma from '@/lib/db';
import { fetchWithTimeout, isTimeoutError } from '@/lib/fetchWithTimeout';
import { isAuthenticationError, requireAuthenticatedSession } from '@/lib/auth-guard';
import {
  classifyPaymentConfirmationResult,
  PAYMENT_CONFIRMATION_PENDING_MESSAGE,
  readJsonResponseSafely,
} from '@/lib/payment-confirmation.mjs';
import {
  PREMIUM_SUBSCRIPTION,
  addDays,
  buildCustomerKey,
  parseCustomerKeyFromOrderId,
} from '@/lib/subscription';

const TOSS_CONFIRM_TIMEOUT_MS = 15000;

function buildPendingResponse(message = PAYMENT_CONFIRMATION_PENDING_MESSAGE) {
  return NextResponse.json(
    {
      success: false,
      pending: true,
      message,
    },
    { status: 202 }
  );
}

async function markPaymentLogFailed({ orderId, paymentKey, amount }) {
  await prisma.paymentLog.upsert({
    where: { orderId },
    update: {
      paymentKey,
      amount,
      status: 'FAILED',
    },
    create: {
      orderId,
      paymentKey,
      amount,
      status: 'FAILED',
    },
  });
}

export async function POST(req) {
  try {
    const session = await requireAuthenticatedSession();
    const body = await req.json();
    const { paymentKey, orderId } = body;
    const amount = Number(body?.amount);

    if (!paymentKey || !orderId || !Number.isFinite(amount)) {
      return NextResponse.json(
        { success: false, message: 'Missing payment confirmation fields.' },
        { status: 400 }
      );
    }

    const expectedCustomerKey = buildCustomerKey(session.user.id);
    const orderCustomerKey = parseCustomerKeyFromOrderId(orderId);

    if (!orderCustomerKey || orderCustomerKey !== expectedCustomerKey) {
      return NextResponse.json(
        { success: false, message: 'Order does not belong to the current user.' },
        { status: 403 }
      );
    }

    if (amount !== PREMIUM_SUBSCRIPTION.amount) {
      return NextResponse.json(
        { success: false, message: 'Unexpected payment amount.' },
        { status: 400 }
      );
    }

    const secretKey = process.env.TOSS_PAYMENTS_SECRET_KEY;
    if (!secretKey) {
      throw new Error('TOSS_PAYMENTS_SECRET_KEY is not configured.');
    }

    await prisma.paymentLog.upsert({
      where: { orderId },
      update: {
        paymentKey,
        amount,
        status: 'PENDING_CONFIRMATION',
      },
      create: {
        orderId,
        paymentKey,
        amount,
        status: 'PENDING_CONFIRMATION',
      },
    });

    const basicAuth = Buffer.from(`${secretKey}:`).toString('base64');
    let response;

    try {
      response = await fetchWithTimeout(
        'https://api.tosspayments.com/v1/payments/confirm',
        {
          method: 'POST',
          headers: {
            Authorization: `Basic ${basicAuth}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ paymentKey, orderId, amount }),
          cache: 'no-store',
        },
        {
          timeoutMs: TOSS_CONFIRM_TIMEOUT_MS,
          errorMessage: `Payment confirmation timed out after ${TOSS_CONFIRM_TIMEOUT_MS}ms.`,
        },
      );
    } catch (error) {
      if (isTimeoutError(error)) {
        return buildPendingResponse();
      }

      console.error('Payment confirmation request failed before a response was received:', error);
      return buildPendingResponse();
    }

    const { data: paymentData, rawText, parseError } = await readJsonResponseSafely(response);
    const confirmationResult = classifyPaymentConfirmationResult({
      status: response.status,
      payload: paymentData,
      rawText,
      parseError,
      expectedAmount: amount,
    });

    if (confirmationResult.kind === 'pending') {
      if (response.status >= 500 || parseError) {
        console.error('Payment confirmation deferred due to retryable gateway response.', {
          orderId,
          status: response.status,
          parseError: parseError?.message,
        });
      }

      return buildPendingResponse(confirmationResult.message);
    }

    if (confirmationResult.kind === 'failed') {
      await markPaymentLogFailed({ orderId, paymentKey, amount });
      return NextResponse.json(
        { success: false, message: confirmationResult.message },
        { status: confirmationResult.httpStatus }
      );
    }

    const { approvedAt, confirmedAmount, receiptUrl } = confirmationResult;

    await prisma.$transaction(async (tx) => {
      await tx.paymentLog.upsert({
        where: { orderId },
        update: {
          paymentKey,
          amount: confirmedAmount,
          status: 'DONE',
          approvedAt,
          receiptUrl,
        },
        create: {
          orderId,
          paymentKey,
          amount: confirmedAmount,
          status: 'DONE',
          approvedAt,
          receiptUrl,
        },
      });

      await tx.subscription.upsert({
        where: { customerKey: expectedCustomerKey },
        update: {
          userId: session.user.id,
          status: 'ACTIVE',
          planName: PREMIUM_SUBSCRIPTION.planName,
          amount: confirmedAmount,
          nextPaymentDate: addDays(approvedAt, 30),
        },
        create: {
          userId: session.user.id,
          customerKey: expectedCustomerKey,
          status: 'ACTIVE',
          planName: PREMIUM_SUBSCRIPTION.planName,
          amount: confirmedAmount,
          nextPaymentDate: addDays(approvedAt, 30),
        },
      });
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    if (isAuthenticationError(error)) {
      return NextResponse.json({ success: false, message: error.message }, { status: 401 });
    }

    console.error('Payment Confirm Error:', error);
    return NextResponse.json(
      { success: false, message: error.message || 'Payment verification failed.' },
      { status: 500 }
    );
  }
}
