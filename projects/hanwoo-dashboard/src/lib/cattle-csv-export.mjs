export function buildCattleCsvRows(cattleList) {
  const headers = ['ID', '이름', '이력번호', '생년월일', '성별', '상태', '축사 ID', '칸 번호', '메모'];

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

  return ['\uFEFF' + headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
}
