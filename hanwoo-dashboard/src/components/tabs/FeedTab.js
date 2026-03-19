import { useMemo, useState } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { BREED_STATUS_OPTIONS, BUILDINGS } from '@/lib/constants';

function FilterChip({ active, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: '8px 16px',
        borderRadius: '999px',
        border: '1px solid var(--color-surface-stroke)',
        background: active ? 'var(--surface-gradient-primary)' : 'var(--surface-gradient)',
        color: active ? 'white' : 'var(--color-text)',
        fontWeight: 700,
        fontSize: '13px',
        cursor: 'pointer',
        whiteSpace: 'nowrap',
        boxShadow: active ? 'var(--shadow-button-primary)' : 'var(--shadow-sm)',
      }}
    >
      {children}
    </button>
  );
}

export default function FeedTab({ cattle, feedStandards = [], feedHistory = [], onRecordFeed }) {
  const [selectedBuilding, setSelectedBuilding] = useState(null);
  const [recordForm, setRecordForm] = useState({
    date: new Date().toISOString().split('T')[0],
    roughage: '',
    concentrate: '',
    note: '',
  });

  const standardsMap = useMemo(() => {
    const map = {};
    feedStandards.forEach((standard) => {
      map[standard.status] = standard;
    });
    return map;
  }, [feedStandards]);

  const feedSummary = useMemo(() => {
    const summary = {};

    BREED_STATUS_OPTIONS.forEach((status) => {
      const count = cattle.filter((row) => row.status === status).length;
      const standard = standardsMap[status];

      if (count > 0 && standard) {
        summary[status] = {
          count,
          roughageTotal: (standard.roughageKg * count).toFixed(1),
          concentrateTotal: (standard.concentrateKg * count).toFixed(1),
          roughage: standard.roughage,
          concentrate: standard.concentrate,
        };
      }
    });

    return summary;
  }, [cattle, standardsMap]);

  const totalStandardRoughage = Object.values(feedSummary)
    .reduce((sum, value) => sum + parseFloat(value.roughageTotal), 0)
    .toFixed(1);
  const totalStandardConcentrate = Object.values(feedSummary)
    .reduce((sum, value) => sum + parseFloat(value.concentrateTotal), 0)
    .toFixed(1);

  const filteredCattle = useMemo(() => {
    if (!selectedBuilding) return cattle;
    return cattle.filter((row) => row.buildingId === selectedBuilding);
  }, [cattle, selectedBuilding]);

  const chartData = useMemo(() => {
    const grouped = {};
    const sorted = [...feedHistory].sort((first, second) => new Date(first.date) - new Date(second.date));

    sorted.forEach((record) => {
      const key = new Date(record.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
      if (!grouped[key]) grouped[key] = { date: key, roughage: 0, concentrate: 0 };
      grouped[key].roughage += record.roughage;
      grouped[key].concentrate += record.concentrate;
    });

    return Object.values(grouped);
  }, [feedHistory]);

  const handleSubmit = () => {
    if (!recordForm.roughage || !recordForm.concentrate) {
      alert('급여량을 입력해 주세요.');
      return;
    }

    if (!selectedBuilding) {
      alert('축사를 먼저 선택해 주세요.');
      return;
    }

    onRecordFeed({
      ...recordForm,
      buildingId: selectedBuilding,
    });

    setRecordForm((previous) => ({ ...previous, roughage: '', concentrate: '', note: '' }));
  };

  const roughageGuide = selectedBuilding
    ? filteredCattle.reduce((sum, row) => sum + (standardsMap[row.status]?.roughageKg || 0), 0).toFixed(1)
    : totalStandardRoughage;
  const concentrateGuide = selectedBuilding
    ? filteredCattle.reduce((sum, row) => sum + (standardsMap[row.status]?.concentrateKg || 0), 0).toFixed(1)
    : totalStandardConcentrate;

  return (
    <div>
      <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--color-text)', marginBottom: '14px' }}>
        🪴 사료 급여 모니터링
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', overflowX: 'auto', paddingBottom: '4px' }}>
        <FilterChip active={!selectedBuilding} onClick={() => setSelectedBuilding(null)}>
          전체
        </FilterChip>
        {BUILDINGS.map((building) => (
          <FilterChip
            key={building.id}
            active={selectedBuilding === building.id}
            onClick={() => setSelectedBuilding(building.id)}
          >
            {building.name}
          </FilterChip>
        ))}
      </div>

      <div
        style={{
          background:
            'linear-gradient(145deg, color-mix(in srgb, var(--chart-clay-1) 78%, white 22%), color-mix(in srgb, var(--chart-clay-1) 76%, #5a734f 24%))',
          borderRadius: '24px',
          padding: '18px',
          color: 'white',
          marginBottom: '20px',
          boxShadow: 'var(--shadow-md)',
        }}
      >
        <div
          style={{
            fontSize: '13px',
            opacity: 0.9,
            marginBottom: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <span>오늘의 급여 가이드 {selectedBuilding ? `(${BUILDINGS.find((row) => row.id === selectedBuilding)?.name})` : '(전체)'}</span>
          <span>{filteredCattle.length}두</span>
        </div>
        <div style={{ display: 'flex', gap: '20px' }}>
          <div>
            <div style={{ fontSize: '24px', fontWeight: 800, fontFamily: 'var(--font-display-custom)' }}>{roughageGuide}kg</div>
            <div style={{ fontSize: '11px', opacity: 0.82 }}>조사료 권장량</div>
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: 800, fontFamily: 'var(--font-display-custom)' }}>
              {concentrateGuide}kg
            </div>
            <div style={{ fontSize: '11px', opacity: 0.82 }}>농후사료 권장량</div>
          </div>
        </div>
      </div>

      {selectedBuilding ? (
        <div
          style={{
            background: 'var(--surface-gradient)',
            borderRadius: '24px',
            padding: '24px',
            marginBottom: '20px',
            border: '1px solid var(--color-surface-stroke)',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <div style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-text)' }}>
            📝 오늘 급여 기록
            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text-muted)', marginLeft: '8px' }}>
              {BUILDINGS.find((row) => row.id === selectedBuilding)?.name}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            <Field
              label="조사료"
              suffix="kg"
              value={recordForm.roughage}
              onChange={(value) => setRecordForm({ ...recordForm, roughage: value })}
            />
            <Field
              label="농후사료"
              suffix="kg"
              value={recordForm.concentrate}
              onChange={(value) => setRecordForm({ ...recordForm, concentrate: value })}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label
              htmlFor="feed-note"
              style={{ fontSize: '12px', color: 'var(--color-text-secondary)', fontWeight: 600, marginBottom: '6px', display: 'block' }}
            >
              특이사항 메모
            </label>
            <textarea
              id="feed-note"
              placeholder="사료 상태나 섭취량 변화, 축사 메모를 남겨 두세요."
              value={recordForm.note}
              onChange={(event) => setRecordForm({ ...recordForm, note: event.target.value })}
              style={{
                width: '100%',
                padding: '14px',
                borderRadius: '16px',
                border: '1px solid var(--color-surface-border)',
                fontFamily: 'inherit',
                fontSize: '14px',
                resize: 'none',
                height: '82px',
                outline: 'none',
                background: 'var(--surface-gradient)',
                color: 'var(--color-text)',
                boxShadow: 'var(--shadow-inset-soft)',
              }}
            />
          </div>

          <button
            type="button"
            onClick={handleSubmit}
            style={{
              width: '100%',
              background: 'var(--surface-gradient-primary)',
              color: 'white',
              padding: '16px',
              borderRadius: '18px',
              fontWeight: 700,
              fontSize: '15px',
              border: '1px solid color-mix(in srgb, white 18%, transparent)',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-button-primary)',
            }}
          >
            급여 기록 저장하기
          </button>
        </div>
      ) : null}

      <div
        style={{
          background: 'var(--surface-gradient)',
          borderRadius: '24px',
          padding: '16px',
          border: '1px solid var(--color-surface-stroke)',
          height: '300px',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-text)' }}>
          최근 급여 추이
        </div>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                borderRadius: 18,
                border: '1px solid var(--color-surface-stroke)',
                boxShadow: 'var(--shadow-md)',
                background: 'var(--surface-gradient)',
              }}
            />
            <Legend />
            <Line type="monotone" dataKey="roughage" name="조사료" stroke="var(--chart-clay-1)" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            <Line type="monotone" dataKey="concentrate" name="농후사료" stroke="var(--chart-clay-2)" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ marginTop: '20px' }}>
        <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '10px', color: 'var(--color-text)' }}>최근 기록</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {feedHistory.slice(0, 5).map((record) => (
            <div
              key={record.id}
              style={{
                background: 'var(--surface-gradient)',
                borderRadius: '18px',
                padding: '12px 14px',
                border: '1px solid var(--color-surface-stroke)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text)' }}>
                  {new Date(record.date).toLocaleDateString()}
                  <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontWeight: 400, marginLeft: '6px' }}>
                    {BUILDINGS.find((row) => row.id === record.buildingId)?.name}
                  </span>
                </div>
                {record.note ? (
                  <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px' }}>{record.note}</div>
                ) : null}
              </div>
              <div style={{ fontSize: '12px', fontWeight: 700 }}>
                <span style={{ color: 'var(--chart-clay-1)' }}>조 {record.roughage}</span> ·{' '}
                <span style={{ color: 'var(--chart-clay-2)' }}>농 {record.concentrate}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Field({ label, suffix, value, onChange }) {
  return (
    <div style={{ position: 'relative' }}>
      <label
        style={{ fontSize: '12px', color: 'var(--color-text-secondary)', fontWeight: 600, marginBottom: '6px', display: 'block' }}
      >
        {label}
      </label>
      <div style={{ position: 'relative' }}>
        <input
          type="number"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="0.0"
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '16px',
            border: '1px solid var(--color-surface-border)',
            fontSize: '16px',
            fontWeight: 700,
            fontFamily: 'var(--font-display-custom)',
            color: 'var(--color-text)',
            background: 'var(--surface-gradient)',
            outline: 'none',
            boxShadow: 'var(--shadow-inset-soft)',
          }}
        />
        <span
          style={{
            position: 'absolute',
            right: '14px',
            top: '50%',
            transform: 'translateY(-50%)',
            fontSize: '12px',
            color: 'var(--color-text-muted)',
            fontWeight: 600,
          }}
        >
          {suffix}
        </span>
      </div>
    </div>
  );
}
