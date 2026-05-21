const ORDER_PREFIX = "sub";
const CUSTOMER_PREFIX = "user";

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

export function parseCustomerKeyFromOrderId(orderId) {
  const match = /^sub_(.+)_(\d+)$/.exec(String(orderId || ""));
  return match ? match[1] : null;
}

export function addDays(baseDate, days) {
  const next = baseDate instanceof Date ? new Date(baseDate.getTime()) : new Date(baseDate);
  const safeDate = Number.isFinite(next.getTime()) ? next : new Date();
  const safeDays = Number.isFinite(Number(days)) ? Number(days) : 0;

  safeDate.setDate(safeDate.getDate() + safeDays);
  return safeDate;
}
