'use client';

import { useState } from 'react';

import { useAppFeedback } from '@/components/feedback/FeedbackProvider';
import { PremiumButton } from '@/components/ui/premium-button';

function buildCsvRows(cattleList) {
  const headers = ['ID', 'Name', 'Tag Number', 'Birth Date', 'Gender', 'Status', 'Building ID', 'Pen Number', 'Memo'];

  const rows = cattleList.map((cattle) => [
    cattle.id,
    cattle.name,
    cattle.tagNumber,
    cattle.birthDate ? new Date(cattle.birthDate).toLocaleDateString() : '',
    cattle.gender || '',
    cattle.status || '',
    cattle.buildingId || '',
    cattle.penNumber || '',
    (cattle.memo || '').replace(/,/g, ' '),
  ]);

  return ['\uFEFF' + headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
}

export default function ExcelExportButton({ cattleList = [], resolveCattleList = null }) {
  const { notify } = useAppFeedback();
  const [isPreparing, setIsPreparing] = useState(false);

  const handleDownload = async () => {
    setIsPreparing(true);

    try {
      const rows =
        typeof resolveCattleList === 'function'
          ? await resolveCattleList()
          : cattleList;

      if (!rows || rows.length === 0) {
        notify({
          title: '다운로드할 개체 데이터가 없습니다.',
          description: '등록된 개체를 확인한 뒤 다시 시도해 주세요.',
          variant: 'warning',
        });
        return;
      }

      const csvContent = buildCsvRows(rows);
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `hanwoo_data_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      notify({
        title: '엑셀 내보내기에 실패했습니다.',
        description: error instanceof Error ? error.message : '잠시 후 다시 시도해 주세요.',
        variant: 'error',
      });
    } finally {
      setIsPreparing(false);
    }
  };

  return (
    <PremiumButton
      variant="secondary"
      size="sm"
      onClick={handleDownload}
      disabled={isPreparing}
      className="gap-1.5 font-bold shadow-md"
    >
      <span className="text-[#1D6F42] text-[14px]">?</span>
      {isPreparing ? '준비 중...' : '엑셀 다운로드'}
    </PremiumButton>
  );
}
