'use client';

const TYPE_STYLES = {
  estrus: {
    accent: 'var(--color-estrus)',
    surface: 'color-mix(in srgb, var(--color-estrus) 14%, var(--color-surface-elevated))',
    iconSurface: 'color-mix(in srgb, var(--color-estrus) 18%, white 82%)',
    icon: '🫀',
    label: '번식 알림',
  },
  calving: {
    accent: 'var(--color-calving)',
    surface: 'color-mix(in srgb, var(--color-calving) 14%, var(--color-surface-elevated))',
    iconSurface: 'color-mix(in srgb, var(--color-calving) 18%, white 82%)',
    icon: '🐮',
    label: '분만 알림',
  },
  urgent: {
    accent: 'var(--chart-clay-4)',
    surface: 'color-mix(in srgb, var(--chart-clay-4) 14%, var(--color-surface-elevated))',
    iconSurface: 'color-mix(in srgb, var(--chart-clay-4) 18%, white 82%)',
    icon: '🚨',
    label: '긴급 알림',
  },
  default: {
    accent: 'var(--chart-clay-5)',
    surface: 'color-mix(in srgb, var(--chart-clay-5) 14%, var(--color-surface-elevated))',
    iconSurface: 'color-mix(in srgb, var(--chart-clay-5) 18%, white 82%)',
    icon: '🔔',
    label: '운영 알림',
  },
};

export default function NotificationWidget({ notifications = [] }) {
  if (notifications.length === 0) return null;

  return (
    <section className="animate-fadeInDown mb-6">
      <div className="mb-3 flex items-center gap-3">
        <div className="clay-page-eyebrow">Priority Alerts</div>
        <div className="clay-stat-chip">{notifications.length}건</div>
      </div>

      <div className="grid gap-3">
        {notifications.map((note) => {
          const style = TYPE_STYLES[note.type] || TYPE_STYLES.default;

          return (
            <div
              key={note.id}
              className="rounded-[24px] border p-4"
              style={{
                background: style.surface,
                borderColor: 'color-mix(in srgb, var(--color-surface-stroke) 80%, transparent)',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div className="flex items-start gap-3">
                <div
                  className="flex h-11 w-11 items-center justify-center rounded-full text-lg"
                  style={{
                    background: style.iconSurface,
                    color: style.accent,
                    boxShadow: 'var(--shadow-sm)',
                  }}
                >
                  {style.icon}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <span className="text-sm font-bold text-[color:var(--color-text)]">{note.title}</span>
                    <span
                      className="inline-flex rounded-full border px-2 py-0.5 text-[10px] font-bold"
                      style={{
                        borderColor: 'color-mix(in srgb, var(--color-surface-border) 80%, transparent)',
                        color: style.accent,
                      }}
                    >
                      {style.label}
                    </span>
                    {note.level === 'critical' ? (
                      <span className="animate-pulse text-[10px] font-bold text-[color:var(--color-danger)]">긴급</span>
                    ) : null}
                  </div>

                  <p className="m-0 text-sm leading-6 text-[color:var(--color-text-secondary)]">{note.message}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
