import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { BREED_STATUS_OPTIONS } from '@/lib/constants';
import { inputStyle, labelStyle, btnPrimary, btnSecondary, BackIcon } from '@/components/ui/common';
import { lookupCattleTag } from '@/lib/actions';
import { cattleFormSchema, createCattleFormValues } from '@/lib/formSchemas';

const errorTextStyle = {
  fontSize: '12px',
  marginTop: '6px',
  color: 'var(--color-danger)',
  fontWeight: 600,
};

export default function CattleForm({ cattle, buildings = [], onSubmit, onCancel }) {
  const dialogRef = useRef(null);
  const lookupInFlightRef = useRef(false);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupMsg, setLookupMsg] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const tagNumberErrorId = 'cattle-tag-number-error';
  const tagLookupMessageId = 'cattle-tag-lookup-message';

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    getValues,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(cattleFormSchema),
    defaultValues: createCattleFormValues(cattle, buildings),
  });

  useEffect(() => {
    reset(createCattleFormValues(cattle, buildings));
    setLookupMsg(null);
    setIsSaving(false);
  }, [buildings, cattle, reset]);

  useEffect(() => {
    dialogRef.current?.focus();
  }, [cattle?.id]);

  const handleDialogKeyDown = (event) => {
    if (event.key === 'Escape') {
      onCancel();
    }
  };

  const handleLookup = async () => {
    if (lookupInFlightRef.current) {
      return;
    }

    const tagNumber = getValues('tagNumber');

    if (!tagNumber) {
      setLookupMsg({ ok: false, text: '이력번호를 입력해 주세요.' });
      return;
    }

    lookupInFlightRef.current = true;
    setLookupLoading(true);
    setLookupMsg(null);

    try {
      const res = await lookupCattleTag(tagNumber);

      if (res.success && res.data) {
        const data = res.data;

        if (data.birthDate) {
          const raw = data.birthDate.replace(/[-/]/g, '');
          if (raw.length === 8) {
            setValue('birthDate', `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`, {
              shouldDirty: true,
              shouldValidate: true,
            });
          }
        }

        if (data.gender) {
          setValue('gender', data.gender, { shouldDirty: true, shouldValidate: true });
        }

        setLookupMsg({ ok: true, text: `조회 완료 (${data.breed || '한우'})` });
      } else {
        setLookupMsg({ ok: false, text: res.message || '조회에 실패했습니다.' });
      }
    } catch {
      setLookupMsg({ ok: false, text: '조회 중 오류가 발생했습니다.' });
    } finally {
      lookupInFlightRef.current = false;
      setLookupLoading(false);
    }
  };

  const submitForm = async (values) => {
    setIsSaving(true);

    try {
      await onSubmit({
        ...values,
        id: cattle ? cattle.id : `new_${Date.now()}`,
        birthDate: new Date(values.birthDate).toISOString(),
        weight: Number(values.weight),
        weightHistory: cattle ? cattle.weightHistory : [],
        lastEstrus: cattle?.lastEstrus ?? null,
        pregnancyDate: cattle?.pregnancyDate ?? null,
        purchasePrice: values.purchasePrice ?? null,
        purchaseDate: values.purchaseDate ? new Date(values.purchaseDate).toISOString() : null,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const tagNumberDescriptionIds = [
    errors.tagNumber ? tagNumberErrorId : null,
    lookupMsg ? tagLookupMessageId : null,
  ].filter(Boolean).join(' ') || undefined;

  return (
    <div className="modal-overlay" style={{ alignItems: 'flex-start', paddingTop: '20px' }}>
      <div
        ref={dialogRef}
        className="animate-slideInUp"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cattle-form-title"
        tabIndex={-1}
        onKeyDown={handleDialogKeyDown}
        style={{
          background: 'var(--color-bg)',
          width: '100%',
          maxWidth: '500px',
          minHeight: '100vh',
          padding: '20px',
          overflowY: 'auto',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            marginBottom: '28px',
            gap: '14px',
          }}
        >
          <button
            type="button"
            onClick={onCancel}
            aria-label="개체 목록으로 돌아가기"
            title="개체 목록으로 돌아가기"
            className="btn btn-ghost btn-icon"
            style={{ width: '42px', height: '42px' }}
          >
            <BackIcon />
          </button>
          <div>
            <div id="cattle-form-title" style={{ fontSize: '22px', fontWeight: 800, color: 'var(--color-text)', letterSpacing: '-0.02em' }}>
              {cattle ? '개체 정보 수정' : '새 개체 등록'}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--color-text-muted)', marginTop: '3px' }}>
              {cattle ? '정보를 수정하고 저장하세요' : '새 개체의 기본 정보를 입력하세요'}
            </div>
          </div>
        </div>

        <form
          onSubmit={handleSubmit(submitForm)}
          className="card animate-fadeInUp"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '18px',
            padding: '24px',
          }}
        >
          <input type="hidden" {...register('geneticInfo.grade')} />

          <div>
            <label htmlFor="cattle-name" style={labelStyle}>이름 (별명)</label>
            <input
              id="cattle-name"
              className="input"
              style={inputStyle}
              placeholder="예: 순심이"
              aria-invalid={Boolean(errors.name)}
              aria-describedby={errors.name ? "cattle-name-error" : undefined}
              {...register('name')}
            />
            {errors.name ? <div id="cattle-name-error" role="alert" style={errorTextStyle}>{errors.name.message}</div> : null}
          </div>

          <div>
            <label htmlFor="cattle-tag-number" style={labelStyle}>이력번호</label>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <input
                id="cattle-tag-number"
                className="input"
                style={{ ...inputStyle, flex: 1 }}
                placeholder="002082037849"
                aria-invalid={Boolean(errors.tagNumber)}
                aria-describedby={tagNumberDescriptionIds}
                {...register('tagNumber')}
              />
              <button
                type="button"
                onClick={handleLookup}
                disabled={lookupLoading}
                aria-busy={lookupLoading}
                style={{
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-primary)',
                  background: 'var(--color-primary)',
                  color: 'white',
                  fontSize: '13px',
                  fontWeight: 700,
                  cursor: lookupLoading ? 'wait' : 'pointer',
                  whiteSpace: 'nowrap',
                  opacity: lookupLoading ? 0.7 : 1,
                  transition: 'all var(--transition-fast)',
                }}
              >
                {lookupLoading ? '조회 중...' : '태그 조회'}
              </button>
            </div>
            {errors.tagNumber ? <div id={tagNumberErrorId} role="alert" style={errorTextStyle}>{errors.tagNumber.message}</div> : null}
            {lookupMsg ? (
              <div
                id={tagLookupMessageId}
                role={lookupMsg.ok ? 'status' : 'alert'}
                aria-live={lookupMsg.ok ? 'polite' : 'assertive'}
                style={{
                  fontSize: '12px',
                  marginTop: '6px',
                  color: lookupMsg.ok ? 'var(--color-success)' : 'var(--color-danger)',
                  fontWeight: 600,
                }}
              >
                {lookupMsg.text}
              </div>
            ) : null}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <label htmlFor="cattle-building" style={labelStyle}>축사</label>
              <select id="cattle-building" className="input" style={inputStyle} aria-invalid={Boolean(errors.buildingId)} aria-describedby={errors.buildingId ? "cattle-building-error" : undefined} {...register('buildingId')}>
                {buildings.map((building) => (
                  <option key={building.id} value={building.id}>
                    {building.name}
                  </option>
                ))}
              </select>
              {errors.buildingId ? <div id="cattle-building-error" role="alert" style={errorTextStyle}>{errors.buildingId.message}</div> : null}
            </div>

            <div>
              <label htmlFor="cattle-pen-number" style={labelStyle}>칸 번호</label>
              <select id="cattle-pen-number" className="input" style={inputStyle} aria-invalid={Boolean(errors.penNumber)} aria-describedby={errors.penNumber ? "cattle-pen-number-error" : undefined} {...register('penNumber')}>
                {[...Array(12)].map((_, index) => (
                  <option key={index + 1} value={index + 1}>
                    {index + 1}번 칸
                  </option>
                ))}
              </select>
              {errors.penNumber ? <div id="cattle-pen-number-error" role="alert" style={errorTextStyle}>{errors.penNumber.message}</div> : null}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <label htmlFor="cattle-gender" style={labelStyle}>성별</label>
              <select id="cattle-gender" className="input" style={inputStyle} aria-invalid={Boolean(errors.gender)} aria-describedby={errors.gender ? "cattle-gender-error" : undefined} {...register('gender')}>
                <option value="암">암</option>
                <option value="수">수</option>
              </select>
              {errors.gender ? <div id="cattle-gender-error" role="alert" style={errorTextStyle}>{errors.gender.message}</div> : null}
            </div>

            <div>
              <label htmlFor="cattle-status" style={labelStyle}>상태</label>
              <select id="cattle-status" className="input" style={inputStyle} aria-invalid={Boolean(errors.status)} aria-describedby={errors.status ? "cattle-status-error" : undefined} {...register('status')}>
                {BREED_STATUS_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              {errors.status ? <div id="cattle-status-error" role="alert" style={errorTextStyle}>{errors.status.message}</div> : null}
            </div>
          </div>

          <div>
            <label htmlFor="cattle-birth-date" style={labelStyle}>생년월일</label>
            <input id="cattle-birth-date" type="date" className="input" style={inputStyle} aria-invalid={Boolean(errors.birthDate)} aria-describedby={errors.birthDate ? "cattle-birth-date-error" : undefined} {...register('birthDate')} />
            {errors.birthDate ? <div id="cattle-birth-date-error" role="alert" style={errorTextStyle}>{errors.birthDate.message}</div> : null}
          </div>

          <div>
            <label htmlFor="cattle-weight" style={labelStyle}>현재 체중 (kg)</label>
            <input id="cattle-weight" type="number" className="input" style={inputStyle} aria-invalid={Boolean(errors.weight)} aria-describedby={errors.weight ? "cattle-weight-error" : undefined} {...register('weight')} />
            {errors.weight ? <div id="cattle-weight-error" role="alert" style={errorTextStyle}>{errors.weight.message}</div> : null}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <label htmlFor="cattle-purchase-price" style={labelStyle}>구입가격 (원)</label>
              <input
                id="cattle-purchase-price"
                type="number"
                className="input"
                style={inputStyle}
                placeholder="예: 3500000"
                aria-invalid={Boolean(errors.purchasePrice)}
                aria-describedby={errors.purchasePrice ? "cattle-purchase-price-error" : undefined}
                {...register('purchasePrice')}
              />
              {errors.purchasePrice ? <div id="cattle-purchase-price-error" role="alert" style={errorTextStyle}>{errors.purchasePrice.message}</div> : null}
            </div>

            <div>
              <label htmlFor="cattle-purchase-date" style={labelStyle}>구입일자</label>
              <input id="cattle-purchase-date" type="date" className="input" style={inputStyle} aria-invalid={Boolean(errors.purchaseDate)} aria-describedby={errors.purchaseDate ? "cattle-purchase-date-error" : undefined} {...register('purchaseDate')} />
              {errors.purchaseDate ? <div id="cattle-purchase-date-error" role="alert" style={errorTextStyle}>{errors.purchaseDate.message}</div> : null}
            </div>
          </div>

          <div
            style={{
              background: 'var(--color-border-light)',
              padding: '18px',
              borderRadius: 'var(--radius-md)',
              marginTop: '6px',
            }}
          >
            <div
              style={{
                fontSize: '14px',
                fontWeight: 700,
                marginBottom: '14px',
                color: 'var(--color-primary-light)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              혈통 정보 (선택)
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label htmlFor="cattle-genetic-father" style={labelStyle}>부 (KPN)</label>
                <input
                  id="cattle-genetic-father"
                  className="input"
                  style={{ ...inputStyle, padding: '10px 12px' }}
                  aria-invalid={Boolean(errors.geneticInfo?.father)}
                  aria-describedby={errors.geneticInfo?.father ? "cattle-genetic-father-error" : undefined}
                  {...register('geneticInfo.father')}
                />
                {errors.geneticInfo?.father ? (
                  <div id="cattle-genetic-father-error" role="alert" style={errorTextStyle}>{errors.geneticInfo.father.message}</div>
                ) : null}
              </div>
              <div>
                <label htmlFor="cattle-genetic-mother" style={labelStyle}>모 (이력)</label>
                <input
                  id="cattle-genetic-mother"
                  className="input"
                  style={{ ...inputStyle, padding: '10px 12px' }}
                  aria-invalid={Boolean(errors.geneticInfo?.mother)}
                  aria-describedby={errors.geneticInfo?.mother ? "cattle-genetic-mother-error" : undefined}
                  {...register('geneticInfo.mother')}
                />
                {errors.geneticInfo?.mother ? (
                  <div id="cattle-genetic-mother-error" role="alert" style={errorTextStyle}>{errors.geneticInfo.mother.message}</div>
                ) : null}
              </div>
            </div>
          </div>

          <div>
            <label htmlFor="cattle-memo" style={labelStyle}>메모</label>
            <textarea
              id="cattle-memo"
              className="input"
              style={{ ...inputStyle, height: '90px', resize: 'none' }}
              aria-invalid={Boolean(errors.memo)}
              aria-describedby={errors.memo ? "cattle-memo-error" : undefined}
              {...register('memo')}
            />
            {errors.memo ? <div id="cattle-memo-error" role="alert" style={errorTextStyle}>{errors.memo.message}</div> : null}
          </div>

          <div style={{ display: 'flex', gap: '12px', marginTop: '28px', paddingTop: '20px', borderTop: '1px solid color-mix(in srgb, var(--color-border-custom) 35%, transparent)' }}>
            <button type="button" onClick={onCancel} disabled={isSaving} className="btn btn-secondary" style={{...btnSecondary, transition: 'all 0.2s cubic-bezier(0.22,1,0.36,1)'}}>
              취소
            </button>
            <button type="submit" disabled={isSaving} aria-busy={isSaving} className="btn btn-primary" style={{...btnPrimary, transition: 'all 0.2s cubic-bezier(0.22,1,0.36,1)'}}>
              저장하기
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
