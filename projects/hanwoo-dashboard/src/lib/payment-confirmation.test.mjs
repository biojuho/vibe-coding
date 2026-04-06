import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildGatewayErrorMessage,
  classifyPaymentConfirmationResult,
  PAYMENT_CONFIRMATION_AMOUNT_MISMATCH_MESSAGE,
  PAYMENT_CONFIRMATION_PENDING_MESSAGE,
  readJsonResponseSafely,
} from './payment-confirmation.mjs';

test('readJsonResponseSafely parses JSON bodies without losing the raw payload', async () => {
  const response = new Response(JSON.stringify({ message: 'Rejected by gateway' }), {
    status: 400,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  const result = await readJsonResponseSafely(response);

  assert.equal(result.parseError, null);
  assert.deepEqual(result.data, { message: 'Rejected by gateway' });
  assert.match(result.rawText, /Rejected by gateway/);
});

test('readJsonResponseSafely captures malformed gateway bodies instead of throwing', async () => {
  const response = new Response('<html><body>Bad Gateway</body></html>', {
    status: 502,
    headers: {
      'Content-Type': 'text/html',
    },
  });

  const result = await readJsonResponseSafely(response);

  assert.equal(result.data, null);
  assert.ok(result.parseError instanceof SyntaxError);
  assert.match(result.rawText, /Bad Gateway/);
});

test('buildGatewayErrorMessage prefers the gateway message when present', () => {
  const message = buildGatewayErrorMessage({
    payload: { code: 'INVALID_ORDER', message: 'Order was already confirmed.' },
    rawText: '',
  });

  assert.equal(message, 'Order was already confirmed.');
});

test('buildGatewayErrorMessage falls back to a safe response snippet for malformed bodies', () => {
  const message = buildGatewayErrorMessage({
    payload: null,
    rawText: '<html><body>Service temporarily unavailable</body></html>',
  });

  assert.match(message, /Payment verification failed\./);
  assert.match(message, /Service temporarily unavailable/);
});

test('classifyPaymentConfirmationResult keeps 5xx gateway failures retryable', () => {
  const result = classifyPaymentConfirmationResult({
    status: 502,
    payload: null,
    rawText: '<html>Bad Gateway</html>',
    parseError: new SyntaxError('Unexpected token <'),
    expectedAmount: 9900,
  });

  assert.equal(result.kind, 'pending');
  assert.equal(result.httpStatus, 202);
  assert.equal(result.message, PAYMENT_CONFIRMATION_PENDING_MESSAGE);
});

test('classifyPaymentConfirmationResult treats malformed 200 responses as pending verification', () => {
  const result = classifyPaymentConfirmationResult({
    status: 200,
    payload: null,
    rawText: 'not-json',
    parseError: new SyntaxError('Unexpected token o'),
    expectedAmount: 9900,
  });

  assert.equal(result.kind, 'pending');
  assert.equal(result.httpStatus, 202);
  assert.equal(result.reason, 'invalid_success_body');
});

test('classifyPaymentConfirmationResult rejects mismatched totals as a definitive failure', () => {
  const result = classifyPaymentConfirmationResult({
    status: 200,
    payload: {
      totalAmount: 8800,
      approvedAt: '2026-04-07T10:00:00.000Z',
    },
    rawText: '',
    parseError: null,
    expectedAmount: 9900,
  });

  assert.equal(result.kind, 'failed');
  assert.equal(result.httpStatus, 400);
  assert.equal(result.message, PAYMENT_CONFIRMATION_AMOUNT_MISMATCH_MESSAGE);
});

test('classifyPaymentConfirmationResult normalizes a successful confirmation payload', () => {
  const fallbackNow = new Date('2026-04-07T12:30:00.000Z');
  const result = classifyPaymentConfirmationResult({
    status: 200,
    payload: {
      totalAmount: 9900,
      approvedAt: 'invalid-date',
      receipt: {
        url: ' https://receipt.example/123 ',
      },
    },
    rawText: '',
    parseError: null,
    expectedAmount: 9900,
    now: () => fallbackNow,
  });

  assert.equal(result.kind, 'confirmed');
  assert.equal(result.confirmedAmount, 9900);
  assert.equal(result.receiptUrl, 'https://receipt.example/123');
  assert.equal(result.approvedAt.toISOString(), fallbackNow.toISOString());
});
