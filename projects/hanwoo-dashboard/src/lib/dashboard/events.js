import prisma from '../db';

export const DASHBOARD_EVENT_TOPICS = Object.freeze({
  cattleCreated: 'CATTLE_CREATED',
  cattleUpdated: 'CATTLE_UPDATED',
  cattleArchived: 'CATTLE_ARCHIVED',
  saleRecorded: 'SALE_RECORDED',
  expenseRecorded: 'EXPENSE_RECORDED',
  feedRecorded: 'FEED_RECORDED',
  farmSettingsUpdated: 'FARM_SETTINGS_UPDATED',
  marketPriceRefreshed: 'MARKET_PRICE_REFRESHED',
  paymentConfirmed: 'PAYMENT_CONFIRMED',
});

function resolveClient(client) {
  return client ?? prisma;
}

export async function createOutboxEvent(input, client) {
  const db = resolveClient(client);

  return db.outboxEvent.create({
    data: {
      topic: input.topic,
      aggregateId: input.aggregateId ?? null,
      payload: input.payload ?? {},
      availableAt: input.availableAt ?? new Date(),
      status: input.status ?? 'PENDING',
    },
  });
}

export async function listPendingOutboxEvents(limit = 50, client) {
  const db = resolveClient(client);

  return db.outboxEvent.findMany({
    where: {
      status: 'PENDING',
      availableAt: {
        lte: new Date(),
      },
    },
    orderBy: [
      { availableAt: 'asc' },
      { createdAt: 'asc' },
    ],
    take: limit,
  });
}

export async function markOutboxEventProcessing(id, client) {
  const db = resolveClient(client);

  return db.outboxEvent.update({
    where: { id },
    data: {
      status: 'PROCESSING',
      attempts: {
        increment: 1,
      },
    },
  });
}

export async function markOutboxEventDone(id, client) {
  const db = resolveClient(client);

  return db.outboxEvent.update({
    where: { id },
    data: {
      status: 'DONE',
    },
  });
}

export async function rescheduleOutboxEvent(id, delaySeconds = 30, client) {
  const db = resolveClient(client);
  const availableAt = new Date(Date.now() + delaySeconds * 1000);

  return db.outboxEvent.update({
    where: { id },
    data: {
      status: 'PENDING',
      availableAt,
    },
  });
}

export async function markOutboxEventFailed(id, client) {
  const db = resolveClient(client);

  return db.outboxEvent.update({
    where: { id },
    data: {
      status: 'FAILED',
    },
  });
}
