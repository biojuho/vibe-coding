#!/usr/bin/env node
/**
 * Outbox Worker — consumes pending OutboxEvents and refreshes read-model snapshots.
 *
 * Usage:
 *   node scripts/outbox-worker.mjs              # run one poll cycle then exit
 *   node scripts/outbox-worker.mjs --daemon      # poll every 10s
 *   node scripts/outbox-worker.mjs --daemon --interval 5000
 */

import { PrismaClient } from '../src/generated/prisma/client.js';
import { PrismaPg } from '@prisma/adapter-pg';
import { buildDashboardSummaryPayload } from '../src/lib/dashboard/summary-service.js';

// ── Config ───────────────────────────────────────────────────────────────────

const POLL_BATCH = 50;
const DEFAULT_INTERVAL_MS = 10_000;
const RETRY_DELAY_SEC = 60;
const MAX_ATTEMPTS = 5;
const ESTRUS_CYCLE_DAYS = 21;
const ESTRUS_ALERT_WINDOW = 3;
const CALVING_DAYS = 285;
const CALVING_ALERT_WINDOW = 14;

// ── Prisma singleton ─────────────────────────────────────────────────────────

let _prisma;
function getPrisma() {
  if (!_prisma) {
    const adapter = new PrismaPg({
      connectionString: process.env.DATABASE_URL,
      ssl: process.env.DATABASE_URL?.includes('localhost') ? undefined : { rejectUnauthorized: false },
      pool: { max: 3, idleTimeout: 20 },
    });
    _prisma = new PrismaClient({ adapter, log: ['error'] });
  }
  return _prisma;
}

// ── Notification helpers (mirrors src/lib/notifications.js + utils.js) ──────

function getNextEstrusDate(lastEstrus) {
  if (!lastEstrus) return null;
  const today = new Date();
  const next = new Date(lastEstrus);
  while (next <= today) next.setDate(next.getDate() + ESTRUS_CYCLE_DAYS);
  return next;
}

function getDaysUntilEstrus(lastEstrus) {
  const next = getNextEstrusDate(lastEstrus);
  return next ? Math.ceil((next - new Date()) / 86400000) : null;
}

function isEstrusAlert(lastEstrus) {
  const days = getDaysUntilEstrus(lastEstrus);
  return days !== null && days >= 0 && days <= ESTRUS_ALERT_WINDOW;
}

function getCalvingDate(pregnancyDate) {
  if (!pregnancyDate) return null;
  return new Date(new Date(pregnancyDate).getTime() + CALVING_DAYS * 86400000);
}

function getDaysUntilCalving(pregnancyDate) {
  const calvingDate = getCalvingDate(pregnancyDate);
  return calvingDate ? Math.ceil((calvingDate - new Date()) / 86400000) : null;
}

function isCalvingAlert(pregnancyDate) {
  const days = getDaysUntilCalving(pregnancyDate);
  return days !== null && days >= 0 && days <= CALVING_ALERT_WINDOW;
}

function buildNotifications(cattle) {
  const notifications = [];
  for (const cow of cattle) {
    if ((cow.status === '번식우' || cow.status === '육성우') && cow.lastEstrus && isEstrusAlert(cow.lastEstrus)) {
      const daysLeft = getDaysUntilEstrus(cow.lastEstrus);
      notifications.push({
        id: `estrus-${cow.id}`, type: 'estrus',
        level: daysLeft <= 1 ? 'critical' : 'warning',
        title: daysLeft === 0 ? '오늘 발정 예정' : '발정 임박',
        message: `${cow.name} (${cow.tagNumber}) 발정 예정일이 ${daysLeft}일 남았습니다.`,
        date: new Date().toISOString(),
      });
    }
    if (cow.status === '임신우' && cow.pregnancyDate && isCalvingAlert(cow.pregnancyDate)) {
      const daysLeft = getDaysUntilCalving(cow.pregnancyDate);
      notifications.push({
        id: `calving-${cow.id}`, type: 'calving',
        level: daysLeft <= 3 ? 'critical' : 'warning',
        title: daysLeft === 0 ? '오늘 분만 예정' : '분만 임박',
        message: `${cow.name} (${cow.tagNumber}) 분만 예정일�� ${daysLeft}일 남���습니다.`,
        date: new Date().toISOString(),
      });
    }
  }
  notifications.sort((a, b) => (a.level === 'critical' ? -1 : 0) - (b.level === 'critical' ? -1 : 0));
  return notifications;
}

// ── Read-model refresh handlers ──────���───────────────────────────────────────

const CATTLE_TOPICS = new Set([
  'CATTLE_CREATED', 'CATTLE_UPDATED', 'CATTLE_ARCHIVED',
]);

const SALE_TOPICS = new Set(['SALE_RECORDED']);

async function refreshNotificationSummary(prisma) {
  const cattle = await prisma.cattle.findMany({ where: { isArchived: false } });
  const notifications = buildNotifications(cattle);
  const key = 'dashboard:notifications:v1:default';

  await prisma.notificationSummary.upsert({
    where: { key },
    update: { payload: notifications, generatedAt: new Date() },
    create: { key, payload: notifications },
  });
  return notifications.length;
}

async function refreshDashboardSummary(prisma) {
  const payload = await buildDashboardSummaryPayload({ client: prisma });

  const key = 'dashboard:summary:v1:default';
  const staleAt = new Date(Date.now() + 30 * 1000);
  await prisma.dashboardSnapshot.upsert({
    where: { key },
    update: { payload, staleAt, generatedAt: new Date() },
    create: { key, payload, staleAt },
  });
  return payload;
}

// ── Event dispatcher ─────────────────────────────────────────────────────────

async function processEvent(prisma, event) {
  const { topic } = event;

  if (CATTLE_TOPICS.has(topic)) {
    await refreshNotificationSummary(prisma);
    await refreshDashboardSummary(prisma);
    return;
  }

  if (SALE_TOPICS.has(topic)) {
    await refreshDashboardSummary(prisma);
    return;
  }

  if (topic === 'EXPENSE_RECORDED') {
    await refreshDashboardSummary(prisma);
    return;
  }

  if (topic === 'FARM_SETTINGS_UPDATED') {
    await refreshDashboardSummary(prisma);
    return;
  }

  if (topic === 'MARKET_PRICE_REFRESHED') {
    // Market price is already saved by the action — no extra work needed
    return;
  }

  // Unknown topic: still mark as done (don't block the queue)
  console.warn(`[worker] unknown topic: ${topic}, marking done`);
}

// ── Poll cycle ─────────���─────────────────────────────────────────────────────

async function pollOnce() {
  const prisma = getPrisma();

  const events = await prisma.outboxEvent.findMany({
    where: { status: 'PENDING', availableAt: { lte: new Date() } },
    orderBy: [{ availableAt: 'asc' }, { createdAt: 'asc' }],
    take: POLL_BATCH,
  });

  if (events.length === 0) return 0;

  let processed = 0;
  for (const event of events) {
    // Mark processing
    await prisma.outboxEvent.update({
      where: { id: event.id },
      data: { status: 'PROCESSING', attempts: { increment: 1 } },
    });

    try {
      await processEvent(prisma, event);
      await prisma.outboxEvent.update({
        where: { id: event.id },
        data: { status: 'DONE' },
      });
      processed++;
    } catch (err) {
      console.error(`[worker] event ${event.id} (${event.topic}) failed:`, err.message);
      const attempts = (event.attempts ?? 0) + 1;
      if (attempts >= MAX_ATTEMPTS) {
        await prisma.outboxEvent.update({
          where: { id: event.id },
          data: { status: 'FAILED' },
        });
      } else {
        await prisma.outboxEvent.update({
          where: { id: event.id },
          data: {
            status: 'PENDING',
            availableAt: new Date(Date.now() + RETRY_DELAY_SEC * 1000),
          },
        });
      }
    }
  }

  return processed;
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  const isDaemon = args.includes('--daemon');
  const intervalIdx = args.indexOf('--interval');
  const intervalMs = intervalIdx >= 0 ? parseInt(args[intervalIdx + 1], 10) : DEFAULT_INTERVAL_MS;

  console.log(`[outbox-worker] mode=${isDaemon ? 'daemon' : 'once'} interval=${intervalMs}ms`);

  if (!isDaemon) {
    const count = await pollOnce();
    console.log(`[outbox-worker] processed ${count} event(s)`);
    await _prisma?.$disconnect();
    process.exit(0);
  }

  // Daemon mode: poll loop
  const shutdown = async () => {
    console.log('[outbox-worker] shutting down...');
    await _prisma?.$disconnect();
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  while (true) {
    try {
      const count = await pollOnce();
      if (count > 0) console.log(`[outbox-worker] processed ${count} event(s)`);
    } catch (err) {
      console.error('[outbox-worker] poll error:', err.message);
    }
    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }
}

main().catch(err => {
  console.error('[outbox-worker] fatal:', err);
  process.exit(1);
});
