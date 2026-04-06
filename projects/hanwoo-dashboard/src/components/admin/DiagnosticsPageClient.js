'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Activity, ArrowLeft, Cpu, Database } from 'lucide-react';

import { useAppFeedback } from '@/components/feedback/FeedbackProvider';
import { getRawData, getSystemDiagnostics } from '@/lib/actions';

const STATUS_STYLES = {
  good: {
    accent: 'var(--chart-clay-1)',
    background: 'color-mix(in srgb, var(--chart-clay-1) 18%, var(--color-surface-elevated))',
  },
  bad: {
    accent: 'var(--chart-clay-4)',
    background: 'color-mix(in srgb, var(--chart-clay-4) 18%, var(--color-surface-elevated))',
  },
  neutral: {
    accent: 'var(--chart-clay-5)',
    background: 'color-mix(in srgb, var(--chart-clay-5) 18%, var(--color-surface-elevated))',
  },
};

const EMPTY_DIAGNOSTICS = {
  success: false,
  database: {
    status: 'Unavailable',
    latency: 'n/a',
    recordCounts: {},
  },
  nodeVersion: 'Unavailable',
  uptime: 0,
  memory: {
    heapUsed: 0,
    heapTotal: 0,
  },
};

export default function DiagnosticsPageClient() {
  const router = useRouter();
  const { notify } = useAppFeedback();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState('cattle');
  const [rawData, setRawData] = useState(null);
  const [dataLoading, setDataLoading] = useState(true);
  const diagnosticsRequestRef = useRef(0);
  const rawDataRequestRef = useRef(0);

  const recordCounts = useMemo(
    () => (stats?.database?.recordCounts ? Object.entries(stats.database.recordCounts) : []),
    [stats]
  );

  useEffect(() => {
    let cancelled = false;
    const requestId = ++diagnosticsRequestRef.current;
    setLoading(true);

    void (async () => {
      try {
        const result = await getSystemDiagnostics();
        if (cancelled || requestId !== diagnosticsRequestRef.current) {
          return;
        }

        setStats(result);
      } catch (error) {
        if (cancelled || requestId !== diagnosticsRequestRef.current) {
          return;
        }

        setStats(EMPTY_DIAGNOSTICS);
        notify({
          title: 'Could not load diagnostics.',
          description: error.message || 'Please try again in a moment.',
          variant: 'error',
        });
      } finally {
        if (!cancelled && requestId === diagnosticsRequestRef.current) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [notify]);

  useEffect(() => {
    let cancelled = false;
    const requestId = ++rawDataRequestRef.current;
    setDataLoading(true);
    setRawData(null);

    void (async () => {
      try {
        const result = await getRawData(selectedModel);
        if (cancelled || requestId !== rawDataRequestRef.current) {
          return;
        }

        if (result.success) {
          setRawData(result.data);
        } else {
          notify({
            title: 'Could not load data.',
            description: result.message || 'Please try again in a moment.',
            variant: 'error',
          });
        }
      } catch (error) {
        if (cancelled || requestId !== rawDataRequestRef.current) {
          return;
        }

        notify({
          title: 'Could not load data.',
          description: error.message || 'Please try again in a moment.',
          variant: 'error',
        });
      } finally {
        if (!cancelled && requestId === rawDataRequestRef.current) {
          setDataLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [notify, selectedModel]);

  if (loading) {
    return (
      <div className="clay-shell">
        <div className="clay-page-card p-8 text-center">
          <div className="clay-page-eyebrow mb-4">Diagnostics</div>
          <h1 className="clay-page-title mb-3">Running diagnostics</h1>
          <p className="clay-page-subtitle">Checking database connectivity and runtime health.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="clay-shell">
      <div className="clay-page-card p-6 md:p-8">
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <div className="clay-page-eyebrow mb-4">System Diagnostics</div>
            <h1 className="clay-page-title mb-3">Operations diagnostics</h1>
            <p className="clay-page-subtitle">
              Review database status, memory use, and raw records from a single screen.
            </p>
          </div>

          <button
            type="button"
            onClick={() => router.push('/')}
            className="clay-pressable inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold text-[color:var(--color-text)]"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to dashboard
          </button>
        </div>

        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <StatusCard
            title="Database Status"
            value={stats.database.status}
            sub={stats.database.latency}
            icon={<Database className="h-5 w-5" />}
            status={stats.success ? 'good' : 'bad'}
          />
          <StatusCard
            title="Node.js Runtime"
            value={stats.nodeVersion}
            sub={`Uptime ${Math.floor(stats.uptime / 60)}m`}
            icon={<Cpu className="h-5 w-5" />}
            status="neutral"
          />
          <StatusCard
            title="Memory Usage"
            value={`${Math.round(stats.memory.heapUsed / 1024 / 1024)} MB`}
            sub={`Total ${Math.round(stats.memory.heapTotal / 1024 / 1024)} MB`}
            icon={<Activity className="h-5 w-5" />}
            status="neutral"
          />
        </div>

        <section className="clay-page-section mb-6 p-5 md:p-6">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <div className="clay-page-eyebrow mb-3">Database Ledger</div>
              <h2 className="text-xl font-bold text-[color:var(--color-text)]">Database record overview</h2>
            </div>
            <div className="clay-stat-chip">{recordCounts.length} models</div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {recordCounts.map(([key, value]) => (
              <div
                key={key}
                className="clay-inset rounded-[22px] p-4"
                style={{ borderColor: 'var(--color-surface-stroke)' }}
              >
                <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-[color:var(--color-text-muted)]">
                  {key}
                </div>
                <div
                  className="text-3xl font-bold"
                  style={{ color: 'var(--color-primary-custom)', fontFamily: 'var(--font-display-custom)' }}
                >
                  {value}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="clay-page-section p-5 md:p-6">
          <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="clay-page-eyebrow mb-3">Raw Data</div>
              <h2 className="text-xl font-bold text-[color:var(--color-text)]">Record inspector</h2>
            </div>

            <select
              value={selectedModel}
              onChange={(event) => setSelectedModel(event.target.value)}
              className="clay-inset rounded-full px-4 py-3 text-sm font-medium text-[color:var(--color-text)] outline-none"
            >
              <option value="cattle">Cattle</option>
              <option value="salesRecord">Sales</option>
              <option value="feedRecord">Feed</option>
              <option value="scheduleEvent">Schedule</option>
              <option value="inventoryItem">Inventory</option>
              <option value="building">Buildings</option>
              <option value="farmSettings">Settings</option>
            </select>
          </div>

          {dataLoading ? (
            <div className="clay-inset rounded-[24px] px-6 py-14 text-center text-sm text-[color:var(--color-text-muted)]">
              Loading records.
            </div>
          ) : (
            <div className="clay-console h-96 overflow-auto p-5 text-sm leading-6">
              <pre className="m-0 whitespace-pre-wrap break-all">{JSON.stringify(rawData, null, 2)}</pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function StatusCard({ title, value, sub, icon, status }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.neutral;

  return (
    <div
      className="rounded-[26px] border p-5"
      style={{
        background: style.background,
        borderColor: 'color-mix(in srgb, var(--color-surface-stroke) 84%, transparent)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-semibold text-[color:var(--color-text-secondary)]">{title}</span>
        <span
          className="inline-flex h-10 w-10 items-center justify-center rounded-full"
          style={{
            background: `color-mix(in srgb, ${style.accent} 16%, white 84%)`,
            color: style.accent,
          }}
        >
          {icon}
        </span>
      </div>
      <div
        className="mb-1 text-3xl font-bold text-[color:var(--color-text)]"
        style={{ fontFamily: 'var(--font-display-custom)' }}
      >
        {value}
      </div>
      <div className="text-xs font-medium text-[color:var(--color-text-muted)]">{sub}</div>
    </div>
  );
}
