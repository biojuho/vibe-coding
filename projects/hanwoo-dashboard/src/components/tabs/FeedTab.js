'use client';

import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

import { useAppFeedback } from '@/components/feedback/FeedbackProvider';
import { BREED_STATUS_OPTIONS, BUILDINGS } from '@/lib/constants';
import { createFeedRecordValues, feedRecordSchema } from '@/lib/formSchemas';
import { PremiumButton } from '@/components/ui/premium-button';
import { PremiumInput, PremiumTextarea, PremiumLabel } from '@/components/ui/premium-input';

const errorTextStyle = {
  fontSize: '12px',
  marginTop: '6px',
  color: 'var(--color-danger)',
  fontWeight: 600,
};

function FilterChip({ active, children, onClick }) {
  return (
    <PremiumButton
      variant={active ? "primary" : "secondary"}
      size="sm"
      onClick={onClick}
      className={`rounded-full px-4 py-2 font-bold text-[13px] whitespace-nowrap shadow-sm ${active ? "shadow-[var(--shadow-button-primary)] text-white" : ""}`}
    >
      {children}
    </PremiumButton>
  );
}

export default function FeedTab({ cattle, feedStandards = [], feedHistory = [], onRecordFeed, buildings = BUILDINGS }) {
  const [selectedBuilding, setSelectedBuilding] = useState(null);
  const { notify } = useAppFeedback();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(feedRecordSchema),
    defaultValues: createFeedRecordValues(),
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
    if (!selectedBuilding) {
      return cattle;
    }

    return cattle.filter((row) => row.buildingId === selectedBuilding);
  }, [cattle, selectedBuilding]);

  const chartData = useMemo(() => {
    const grouped = {};
    const sorted = [...feedHistory].sort((first, second) => new Date(first.date) - new Date(second.date));

    sorted.forEach((record) => {
      const key = new Date(record.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
      if (!grouped[key]) {
        grouped[key] = { date: key, roughage: 0, concentrate: 0 };
      }
      grouped[key].roughage += record.roughage;
      grouped[key].concentrate += record.concentrate;
    });

    return Object.values(grouped);
  }, [feedHistory]);

  const roughageGuide = selectedBuilding
    ? filteredCattle.reduce((sum, row) => sum + (standardsMap[row.status]?.roughageKg || 0), 0).toFixed(1)
    : totalStandardRoughage;
  const concentrateGuide = selectedBuilding
    ? filteredCattle.reduce((sum, row) => sum + (standardsMap[row.status]?.concentrateKg || 0), 0).toFixed(1)
    : totalStandardConcentrate;

  const submitFeedRecord = (values) => {
    if (!selectedBuilding) {
      notify({
        title: '축사를 먼저 선택해 주세요.',
        description: '급여 기록은 특정 축사 기준으로 저장됩니다.',
        variant: 'warning',
      });
      return;
    }

    onRecordFeed({
      ...values,
      buildingId: selectedBuilding,
    });

    reset({
      ...createFeedRecordValues(),
      date: values.date,
    });
  };

  return (
    <div>
      <div className="section-header" style={{ marginBottom: '16px' }}>
        <span className="section-header-icon">🌾</span>
        <h2 className="section-header-title">사료 급여 모니터링</h2>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', overflowX: 'auto', paddingBottom: '4px' }}>
        <FilterChip active={!selectedBuilding} onClick={() => setSelectedBuilding(null)}>
          전체
        </FilterChip>
        {buildings.map((building) => (
          <FilterChip key={building.id} active={selectedBuilding === building.id} onClick={() => setSelectedBuilding(building.id)}>
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
          <span>
            오늘 급여 가이드 {selectedBuilding ? `(${buildings.find((row) => row.id === selectedBuilding)?.name})` : '(전체)'}
          </span>
          <span>{filteredCattle.length}두</span>
        </div>
        <div style={{ display: 'flex', gap: '20px' }}>
          <div>
            <div style={{ fontSize: '24px', fontWeight: 800, fontFamily: 'var(--font-display-custom)' }}>{roughageGuide}kg</div>
            <div style={{ fontSize: '11px', opacity: 0.82 }}>조사료 권장량</div>
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: 800, fontFamily: 'var(--font-display-custom)' }}>{concentrateGuide}kg</div>
            <div style={{ fontSize: '11px', opacity: 0.82 }}>배합사료 권장량</div>
          </div>
        </div>
      </div>

      {selectedBuilding ? (
        <form
          onSubmit={handleSubmit(submitFeedRecord)}
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
            오늘 급여 기록
            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text-muted)', marginLeft: '8px' }}>
              {buildings.find((row) => row.id === selectedBuilding)?.name}
            </span>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <PremiumLabel htmlFor="feed-date">
              기록 날짜
            </PremiumLabel>
            <PremiumInput
              id="feed-date"
              type="date"
              {...register('date')}
              hasError={!!errors.date}
            />
            {errors.date ? <div style={errorTextStyle}>{errors.date.message}</div> : null}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            <Field
              label="조사료"
              suffix="kg"
              error={errors.roughage?.message}
              inputProps={register('roughage')}
            />
            <Field
              label="배합사료"
              suffix="kg"
              error={errors.concentrate?.message}
              inputProps={register('concentrate')}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <PremiumLabel htmlFor="feed-note">
              특이사항 메모
            </PremiumLabel>
            <PremiumTextarea
              id="feed-note"
              {...register('note')}
              placeholder="사료 상태, 날씨 변화, 축사 메모를 적어 주세요."
              hasError={!!errors.note}
              className="h-[82px]"
            />
            {errors.note ? <div style={errorTextStyle}>{errors.note.message}</div> : null}
          </div>

          <PremiumButton
            type="submit"
            className="w-full py-4 text-lg mt-3 bg-linear-to-b from-blue-500 to-blue-600 border-none shadow-(--shadow-button-primary) font-bold"
            glow={true}
          >
            급여 기록 저장하기
          </PremiumButton>
        </form>
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
        <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '16px', color: 'var(--color-text)' }}>최근 급여 추이</div>
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
            <Line
              type="monotone"
              dataKey="concentrate"
              name="배합사료"
              stroke="var(--chart-clay-2)"
              strokeWidth={3}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
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
                    {buildings.find((row) => row.id === record.buildingId)?.name}
                  </span>
                </div>
                {record.note ? <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px' }}>{record.note}</div> : null}
              </div>
              <div style={{ fontSize: '12px', fontWeight: 700 }}>
                <span style={{ color: 'var(--chart-clay-1)' }}>조 {record.roughage}</span> ·{' '}
                <span style={{ color: 'var(--chart-clay-2)' }}>배 {record.concentrate}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Field({ label, suffix, error, inputProps }) {
  return (
    <div style={{ position: 'relative' }}>
      <PremiumLabel>
        {label}
      </PremiumLabel>
      <div style={{ position: 'relative' }}>
        <PremiumInput
          type="number"
          placeholder="0.0"
          {...inputProps}
          hasError={!!error}
          className="text-[16px] font-bold font-['var(--font-display-custom)']"
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
      {error ? <div style={errorTextStyle}>{error}</div> : null}
    </div>
  );
}
