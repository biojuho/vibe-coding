import { NextResponse } from 'next/server';
import prisma from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(req) {
  try {
    const body = await req.json();
    const { paymentKey, orderId, amount } = body;

    // 1. Verify payment with Toss Payments API
    const secretKey = process.env.TOSS_PAYMENTS_SECRET_KEY;
    const basicAuth = Buffer.from(secretKey + ":").toString('base64');

    const response = await fetch("https://api.tosspayments.com/v1/payments/confirm", {
      method: "POST",
      headers: {
        Authorization: `Basic ${basicAuth}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ paymentKey, orderId, amount }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Payment verification failed");
    }

    const paymentData = await response.json();

    // 2. Save Payment Log
    await prisma.paymentLog.upsert({
        where: { orderId },
        update: {
            paymentKey,
            status: "DONE",
            approvedAt: new Date(paymentData.approvedAt),
            receiptUrl: paymentData.receipt.url
        },
        create: {
            orderId,
            paymentKey,
            amount,
            status: "DONE",
            approvedAt: new Date(paymentData.approvedAt),
            receiptUrl: paymentData.receipt.url
        }
    });

    // 3. Activate Subscription (Simple Logic for MVP)
    // Assumes orderId contains customerKey or we find via context. 
    // For now, let's assume one user or we derive from orderId format "sub_USERID_TIMESTAMP"
    
    // Determine user/subscription from orderId implied logic or session
    // For MVP, just updating status if we had a subscription record pending

    return NextResponse.json({ success: true });

  } catch (error) {
    console.error("Payment Confirm Error:", error);
    return NextResponse.json({ success: false, message: error.message }, { status: 400 });
  }
}
