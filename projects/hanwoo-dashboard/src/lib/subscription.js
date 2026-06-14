const ORDER_PREFIX = "sub";
const CUSTOMER_PREFIX = "user";
const PAYMENT_ORDER_ID_PATTERN = /^[A-Za-z0-9_-]{6,64}$/;
const PAYMENT_KEY_MAX_LENGTH = 200;

export const PREMIUM_SUBSCRIPTION = {
	amount: 9900,
	displayName: "Joolife 프리미엄 구독 (월간)",
	planName: "PREMIUM",
};

export function buildCustomerKey(userId) {
	return `${CUSTOMER_PREFIX}_${userId}`;
}

export function buildOrderId(customerKey, timestamp = Date.now()) {
	return `${ORDER_PREFIX}_${customerKey}_${timestamp}`;
}

export function normalizePaymentOrderId(value) {
	if (typeof value !== "string") {
		return "";
	}

	const orderId = value.trim();
	return PAYMENT_ORDER_ID_PATTERN.test(orderId) ? orderId : "";
}

export function normalizePaymentKey(value) {
	if (typeof value !== "string") {
		return "";
	}

	const paymentKey = value.trim();
	if (
		paymentKey.length === 0 ||
		paymentKey.length > PAYMENT_KEY_MAX_LENGTH ||
		/\s/.test(paymentKey)
	) {
		return "";
	}

	return paymentKey;
}

export function parseCustomerKeyFromOrderId(orderId) {
	const match = /^sub_(.+)_(\d+)$/.exec(normalizePaymentOrderId(orderId));
	return match ? match[1] : null;
}

export const TRIAL_DAYS = 14;

export function addDays(baseDate, days) {
	const next =
		baseDate instanceof Date
			? new Date(baseDate.getTime())
			: new Date(baseDate);
	const safeDate = Number.isFinite(next.getTime()) ? next : new Date();
	const safeDays = Number.isFinite(Number(days)) ? Number(days) : 0;

	safeDate.setDate(safeDate.getDate() + safeDays);
	return safeDate;
}
