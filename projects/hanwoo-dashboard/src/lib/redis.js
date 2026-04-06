import IORedis from 'ioredis';

const DEFAULT_REDIS_KEY_PREFIX = 'hd';

const REDIS_ROLE_OPTIONS = Object.freeze({
  cache: {
    maxRetriesPerRequest: 1,
    enableOfflineQueue: false,
  },
  producer: {
    maxRetriesPerRequest: 1,
    enableOfflineQueue: false,
  },
  worker: {
    maxRetriesPerRequest: null,
    enableOfflineQueue: true,
  },
  events: {
    maxRetriesPerRequest: null,
    enableOfflineQueue: true,
  },
});

const REDIS_GLOBAL_KEYS = Object.freeze({
  cache: '__hanwooRedisCache',
  producer: '__hanwooRedisProducer',
});

const globalForRedis = globalThis;

function getRoleOptions(role) {
  return REDIS_ROLE_OPTIONS[role] ?? REDIS_ROLE_OPTIONS.cache;
}

function getSingletonKey(role) {
  return REDIS_GLOBAL_KEYS[role] ?? null;
}

function getRedisUrl() {
  return process.env.REDIS_URL ?? process.env.BULLMQ_REDIS_URL ?? null;
}

function createRetryStrategy(attempt) {
  return Math.min(attempt * 1000, 20000);
}

function attachErrorLogger(client, role) {
  client.on('error', (error) => {
    console.error(`[redis:${role}]`, error);
  });
}

export function isRedisConfigured() {
  return Boolean(getRedisUrl());
}

export function getRedisKeyPrefix() {
  return process.env.REDIS_KEY_PREFIX ?? DEFAULT_REDIS_KEY_PREFIX;
}

export function createRedisClient(role = 'cache') {
  const redisUrl = getRedisUrl();

  if (!redisUrl) {
    return null;
  }

  const options = {
    ...getRoleOptions(role),
    connectionName: `hanwoo-dashboard:${role}`,
    lazyConnect: true,
    retryStrategy: createRetryStrategy,
  };

  if (role === 'cache') {
    options.keyPrefix = `${getRedisKeyPrefix()}:`;
  }

  const client = new IORedis(redisUrl, options);

  attachErrorLogger(client, role);
  return client;
}

export function getRedisClient(role = 'cache') {
  if (!isRedisConfigured()) {
    return null;
  }

  const singletonKey = getSingletonKey(role);

  if (!singletonKey) {
    return createRedisClient(role);
  }

  const existing = globalForRedis[singletonKey];
  if (existing) {
    return existing;
  }

  const client = createRedisClient(role);
  globalForRedis[singletonKey] = client;
  return client;
}

export async function ensureRedisConnection(role = 'cache') {
  const client = getRedisClient(role);

  if (!client) {
    return null;
  }

  if (client.status === 'wait') {
    await client.connect();
  }

  return client;
}

export async function closeRedisClients() {
  for (const singletonKey of Object.values(REDIS_GLOBAL_KEYS)) {
    const client = globalForRedis[singletonKey];
    if (!client) {
      continue;
    }

    await client.quit();
    delete globalForRedis[singletonKey];
  }
}
