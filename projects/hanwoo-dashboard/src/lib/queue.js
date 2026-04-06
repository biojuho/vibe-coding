import { Queue, QueueEvents } from 'bullmq';
import { createRedisClient, getRedisClient, getRedisKeyPrefix, isRedisConfigured } from './redis.js';

const DEFAULT_QUEUE_PREFIX = 'jobs';

const globalForQueue = globalThis;

export const DASHBOARD_QUEUE_NAMES = Object.freeze({
  snapshotRefresh: 'dashboard.snapshot.refresh',
  notificationsRefresh: 'dashboard.notifications.refresh',
  marketPriceRefresh: 'dashboard.market-price.refresh',
  cacheWarm: 'dashboard.cache.warm',
  paymentsPostConfirm: 'payments.post-confirm',
});

export const DEFAULT_JOB_OPTIONS = Object.freeze({
  attempts: 5,
  backoff: {
    type: 'exponential',
    delay: 3000,
  },
  removeOnComplete: 500,
  removeOnFail: 1000,
});

function getQueuePrefix() {
  return process.env.BULLMQ_PREFIX ?? `${getRedisKeyPrefix()}:${DEFAULT_QUEUE_PREFIX}`;
}

function getQueueStore() {
  globalForQueue.__hanwooBullQueues ??= new Map();
  return globalForQueue.__hanwooBullQueues;
}

function getQueueEventsStore() {
  globalForQueue.__hanwooBullQueueEvents ??= new Map();
  return globalForQueue.__hanwooBullQueueEvents;
}

function assertQueueConfigured() {
  if (!isRedisConfigured()) {
    throw new Error('REDIS_URL (or BULLMQ_REDIS_URL) is required before using BullMQ queues.');
  }
}

function buildQueueCacheKey(name, prefix) {
  return `${prefix}:${name}`;
}

export function isQueueConfigured() {
  return isRedisConfigured();
}

export function getQueue(name, options = {}) {
  assertQueueConfigured();

  const prefix = options.prefix ?? getQueuePrefix();
  const cacheKey = buildQueueCacheKey(name, prefix);
  const queueStore = getQueueStore();
  const existing = queueStore.get(cacheKey);

  if (existing) {
    return existing;
  }

  const queue = new Queue(name, {
    connection: getRedisClient('producer'),
    defaultJobOptions: {
      ...DEFAULT_JOB_OPTIONS,
      ...options.defaultJobOptions,
    },
    prefix,
  });

  queueStore.set(cacheKey, queue);
  return queue;
}

export function getQueueEvents(name, options = {}) {
  assertQueueConfigured();

  const prefix = options.prefix ?? getQueuePrefix();
  const cacheKey = buildQueueCacheKey(name, prefix);
  const queueEventsStore = getQueueEventsStore();
  const existing = queueEventsStore.get(cacheKey);

  if (existing) {
    return existing;
  }

  const queueEvents = new QueueEvents(name, {
    connection: createRedisClient('events'),
    prefix,
  });

  queueEventsStore.set(cacheKey, queueEvents);
  return queueEvents;
}

export async function enqueueJob(queueName, data, options = {}) {
  const queue = getQueue(queueName, options.queueOptions);
  const jobName = options.jobName ?? queueName;

  return queue.add(jobName, data, options.jobOptions);
}

export async function closeQueues() {
  const queueStore = getQueueStore();
  const queueEventsStore = getQueueEventsStore();

  for (const queue of queueStore.values()) {
    await queue.close();
  }

  for (const queueEvents of queueEventsStore.values()) {
    await queueEvents.close();
  }

  queueStore.clear();
  queueEventsStore.clear();
}
