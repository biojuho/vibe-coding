export function buildCattleCsvRows(cattleList) {
  const headers = ['개체 번호', '이름', '이력번호', '생년월일', '성별', '상태', '축사 번호', '칸 번호', '메모'];

  const rows = cattleList.map((cattle) => [
    cattle.id,
    cattle.name,
    cattle.tagNumber,
    cattle.birthDate ? new Date(cattle.birthDate).toLocaleDateString('ko-KR') : '',
    cattle.gender || '',
    cattle.status || '',
    cattle.buildingId || '',
    cattle.penNumber || '',
    (cattle.memo || '').replace(/,/g, ' ').replace(/\s+/g, ' ').trim(),
  ]);

  return ['\uFEFF' + headers.join(','), ...rows.map((row) => row.map(formatCsvCell).join(','))].join('\n');
}

function formatCsvCell(value) {
  const text = String(value ?? '');
  if (!/[",\r\n]/.test(text)) {
    return text;
  }
  return `"${text.replace(/"/g, '""')}"`;
}
