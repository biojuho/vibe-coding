export const PAYMENT_CONFIRMATION_PENDING_MESSAGE =
  'Payment confirmation is still being verified. Please retry in a few seconds.';

export const PAYMENT_CONFIRMATION_FAILURE_MESSAGE = 'Payment verification failed.';

export const PAYMENT_CONFIRMATION_AMOUNT_MISMATCH_MESSAGE =
  'Confirmed payment amount does not match the expected amount.';

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function buildGatewaySnippet(rawText) {
  if (typeof rawText !== 'string') {
    return '';
  }

  return rawText.replace(/\s+/g, ' ').trim().slice(0, 160);
}

export async function readJsonResponseSafely(response) {
  const rawText = await response.text();

  if (!rawText.trim()) {
    return {
      data: null,
      rawText,
      parseError: null,
    };
  }

  try {
    return {
      data: JSON.parse(rawText),
      rawText,
      parseError: null,
    };
  } catch (error) {
    return {
      data: null,
      rawText,
      parseError: error,
    };
  }
}

export function buildGatewayErrorMessage({
  payload,
  rawText,
  fallbackMessage = PAYMENT_CONFIRMATION_FAILURE_MESSAGE,
}) {
  if (isPlainObject(payload)) {
    if (typeof payload.message === 'string' && payload.message.trim()) {
      return payload.message.trim();
    }

    if (typeof payload.code === 'string' && payload.code.trim()) {
      return `${fallbackMessage} (${payload.code.trim()}).`;
    }
  }

  const snippet = buildGatewaySnippet(rawText);
  if (snippet) {
    return `${fallbackMessage} Gateway response: ${snippet}`;
  }

  return fallbackMessage;
}

export function classifyPaymentConfirmationResult({
  status,
  payload,
  rawText,
  parseError,
  expectedAmount,
  now = () => new Date(),
}) {
  if (status >= 500) {
    return {
      kind: 'pending',
      httpStatus: 202,
      message: PAYMENT_CONFIRMATION_PENDING_MESSAGE,
      reason: 'gateway_unavailable',
    };
  }

  if (status >= 400) {
    return {
      kind: 'failed',
      httpStatus: 400,
      message: buildGatewayErrorMessage({ payload, rawText }),
      reason: 'gateway_rejected',
    };
  }

  if (!isPlainObject(payload)) {
    return {
      kind: 'pending',
      httpStatus: 202,
      message: PAYMENT_CONFIRMATION_PENDING_MESSAGE,
      reason: parseError ? 'invalid_success_body' : 'empty_success_body',
    };
  }

  const confirmedAmount = Number(payload.totalAmount ?? expectedAmount);
  if (!Number.isFinite(confirmedAmount) || confirmedAmount !== expectedAmount) {
    return {
      kind: 'failed',
      httpStatus: 400,
      message: PAYMENT_CONFIRMATION_AMOUNT_MISMATCH_MESSAGE,
      reason: 'amount_mismatch',
    };
  }

  const approvedAtCandidate = payload.approvedAt ? new Date(payload.approvedAt) : null;
  const approvedAt =
    approvedAtCandidate instanceof Date && Number.isFinite(approvedAtCandidate.getTime())
      ? approvedAtCandidate
      : now();

  const receiptUrl =
    typeof payload?.receipt?.url === 'string' && payload.receipt.url.trim()
      ? payload.receipt.url.trim()
      : null;

  return {
    kind: 'confirmed',
    httpStatus: 200,
    confirmedAmount,
    approvedAt,
    receiptUrl,
    reason: 'confirmed',
  };
}
