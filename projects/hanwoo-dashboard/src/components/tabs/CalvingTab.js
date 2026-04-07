'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { useAppFeedback } from '@/components/feedback/FeedbackProvider';
import {
  calvingRecordSchema,
  createCalvingFormValues,
} from '@/lib/formSchemas';
import { BUILDINGS } from '@/lib/constants';
import { getCalvingDate, getDaysUntilCalving, isCalvingAlert, formatDate } from '@/lib/utils';
import { inputStyle, btnPrimary } from '@/components/ui/common';

const errorTextStyle = {
  fontSize: '12px',
  marginTop: '6px',
  color: 'var(--color-danger)',
  fontWeight: 600,
};

export default function CalvingTab({ cattle, onRecordCalving }) {
  const pregnantCows = cattle
    .filter((row) => row.status === '임신우')
    .sort((first, second) => new Date(first.pregnancyDate) - new Date(second.pregnancyDate));

  const [selectedCowId, setSelectedCowId] = useState(null);
  const { notify } = useAppFeedback();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(calvingRecordSchema),
    defaultValues: createCalvingFormValues(),
  });

  const closeCalvingForm = () => {
    setSelectedCowId(null);
    reset(createCalvingFormValues());
  };

  const openCalvingForm = (cowId) => {
    setSelectedCowId(cowId);
    reset(createCalvingFormValues());
  };

  const submitCalving = async (values) => {
    const cow = cattle.find((row) => row.id === selectedCowId);

    if (!cow) {
      notify({
        title: '분만 대상 개체를 찾지 못했습니다.',
        description: '목록을 새로고침한 뒤 다시 시도해 주세요.',
        variant: 'error',
      });
      return;
    }

    const recorded = await onRecordCalving({
      motherId: cow.id,
      calvingDate: values.calvingDate,
      calfGender: values.calfGender,
    });

    if (!recorded) {
      return;
    }

    closeCalvingForm();
  };

  return (
    <div>
      <div className="section-header" style={{ marginBottom: '16px' }}>
        <span className="section-header-icon">🐮</span>
        <h2 className="section-header-title">분만 예정 관리</h2>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {pregnantCows.length === 0 ? (
          <div className="clay-inset rounded-[24px] px-6 py-10 text-center text-sm text-[color:var(--color-text-muted)]">
            현재 임신우가 없습니다.
          </div>
        ) : (
          pregnantCows.map((cow) => {
            const daysLeft = getDaysUntilCalving(cow.pregnancyDate);
            const alert = isCalvingAlert(cow.pregnancyDate);
            const isSelected = selectedCowId === cow.id;
            const buildingName = BUILDINGS.find((row) => row.id === cow.buildingId)?.name;

            return (
              <div
                key={cow.id}
                className="rounded-[26px] border p-5"
                style={{
                  background: alert
                    ? 'color-mix(in srgb, var(--color-warning-light) 78%, var(--color-surface-elevated))'
                    : 'var(--surface-gradient)',
                  borderColor: alert ? 'var(--color-warning)' : 'var(--color-surface-stroke)',
                  boxShadow: isSelected ? 'var(--shadow-md)' : 'var(--shadow-sm)',
                  transition: 'all 0.3s cubic-bezier(0.22,1,0.36,1)',
                }}
              >
                <div className="mb-4 flex items-start justify-between gap-3">
                  <div>
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="text-lg font-extrabold text-[color:var(--color-text)]">{cow.name}</span>
                      <span
                        className="inline-flex rounded-full px-3 py-1 text-[11px] font-bold"
                        style={{
                          background: 'color-mix(in srgb, var(--color-calving) 18%, white 82%)',
                          color: 'var(--color-calving)',
                        }}
                      >
                        임신우
                      </span>
                      {alert ? (
                        <span
                          className="inline-flex rounded-full px-3 py-1 text-[11px] font-bold text-white animate-pulse"
                          style={{ background: 'linear-gradient(145deg, var(--color-warning), color-mix(in srgb, var(--color-warning) 72%, #9b6e40 28%))' }}
                        >
                          임박 D-{daysLeft}
                        </span>
                      ) : null}
                    </div>
                    <div className="text-sm text-[color:var(--color-text-secondary)]">
                      {buildingName} {cow.penNumber}번 · {cow.tagNumber}
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-xs text-[color:var(--color-text-muted)]">예정일</div>
                    <div
                      className="text-2xl font-bold"
                      style={{ color: alert ? 'var(--color-warning)' : 'var(--color-text)', fontFamily: 'var(--font-display-custom)' }}
                    >
                      {formatDate(getCalvingDate(cow.pregnancyDate))}
                    </div>
                  </div>
                </div>

                {isSelected ? (
                  <form
                    onSubmit={handleSubmit(submitCalving)}
                    className="clay-inset rounded-[22px] p-4"
                    style={{ borderColor: 'var(--color-surface-stroke)' }}
                  >
                    <div className="mb-3 text-sm font-bold text-[color:var(--color-text)]">분만 처리</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '14px' }}>
                      <div>
                        <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                          분만일
                        </label>
                        <input
                          type="date"
                          {...register('calvingDate')}
                          style={{ ...inputStyle, width: '100%' }}
                        />
                        {errors.calvingDate ? <div style={errorTextStyle}>{errors.calvingDate.message}</div> : null}
                      </div>
                      <div>
                        <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                          송아지 성별
                        </label>
                        <select
                          {...register('calfGender')}
                          style={{ ...inputStyle, width: '100%' }}
                        >
                          <option value="암">암송아지</option>
                          <option value="수">수송아지</option>
                        </select>
                        {errors.calfGender ? <div style={errorTextStyle}>{errors.calfGender.message}</div> : null}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button type="submit" style={{ ...btnPrimary, flex: 1, padding: '12px' }}>
                        분만 완료 및 송아지 등록
                      </button>
                      <button
                        type="button"
                        onClick={closeCalvingForm}
                        style={{
                          ...btnPrimary,
                          background: 'var(--surface-gradient)',
                          color: 'var(--color-text)',
                          border: '1px solid var(--color-surface-stroke)',
                          boxShadow: 'var(--shadow-sm)',
                          flex: 0.42,
                        }}
                      >
                        취소
                      </button>
                    </div>
                  </form>
                ) : (
                  <button
                    type="button"
                    onClick={() => openCalvingForm(cow.id)}
                    className="clay-pressable w-full rounded-[18px] px-4 py-3 text-sm font-semibold text-[color:var(--color-text-secondary)]"
                  >
                    분만 처리 열기
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
