import { useState } from 'react';
import { BUILDINGS } from '@/lib/constants';
import { getCalvingDate, getDaysUntilCalving, isCalvingAlert, toInputDate, formatDate } from '@/lib/utils';
import { inputStyle, btnPrimary } from '@/components/ui/common';

export default function CalvingTab({ cattle, onUpdateCattle, onCreateCattle }) {
  const pregnantCows = cattle
    .filter((row) => row.status === '임신우')
    .sort((first, second) => new Date(first.pregnancyDate) - new Date(second.pregnancyDate));

  const [selectedCowId, setSelectedCowId] = useState(null);
  const [calvingDate, setCalvingDate] = useState('');
  const [calfGender, setCalfGender] = useState('암');

  const handleCalving = () => {
    if (!calvingDate) {
      alert('분만일을 입력해 주세요.');
      return;
    }

    const cow = cattle.find((row) => row.id === selectedCowId);
    if (!cow) return;

    const updatedMother = {
      ...cow,
      status: '번식우',
      pregnancyDate: null,
      lastEstrus: null,
      memo: cow.memo
        ? `${cow.memo}\n[분만] ${calvingDate} ${calfGender} 송아지 분만`
        : `[분만] ${calvingDate} ${calfGender} 송아지 분만`,
    };

    onUpdateCattle(updatedMother);

    if (onCreateCattle) {
      onCreateCattle({
        tagNumber: `KR0000-${String(Math.floor(Math.random() * 900000) + 100000)}`,
        name: `${cow.name}의 송아지`,
        buildingId: cow.buildingId,
        penNumber: cow.penNumber,
        gender: calfGender,
        birthDate: new Date(calvingDate).toISOString(),
        weight: 25,
        status: '송아지',
        geneticInfo: { father: cow.geneticFather || '미상', mother: cow.tagNumber, grade: '-' },
        memo: `모체 ${cow.tagNumber} (${cow.name})`,
      });
    }

    setSelectedCowId(null);
  };

  return (
    <div>
      <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--color-text)', marginBottom: '14px' }}>
        🐮 분만 예정 관리
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
                  <div
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
                          value={calvingDate}
                          onChange={(event) => setCalvingDate(event.target.value)}
                          style={{ ...inputStyle, width: '100%' }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                          송아지 성별
                        </label>
                        <select value={calfGender} onChange={(event) => setCalfGender(event.target.value)} style={{ ...inputStyle, width: '100%' }}>
                          <option value="암">암송아지</option>
                          <option value="수">수송아지</option>
                        </select>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button type="button" onClick={handleCalving} style={{ ...btnPrimary, flex: 1, padding: '12px' }}>
                        분만 완료 및 송아지 등록
                      </button>
                      <button
                        type="button"
                        onClick={() => setSelectedCowId(null)}
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
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedCowId(cow.id);
                      setCalvingDate(toInputDate(new Date()));
                    }}
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
