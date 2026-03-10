'use client';

export default function ExcelExportButton({ cattleList = [] }) {
  const handleDownload = () => {
    if(!cattleList || cattleList.length === 0) return alert("다운로드할 데이터가 없습니다.");

    // 1. Create CSV Header
    const headers = ["ID", "이름", "이력번호", "출생일", "성별", "품종", "축사(ID)", "칸 번호", "어미소", "아비소", "비고"];
    
    // 2. Create CSV Rows
    const rows = cattleList.map(c => [
        c.id,
        c.name,
        c.tagNumber,
        c.birthDate ? new Date(c.birthDate).toLocaleDateString() : "",
        c.gender,
        c.breed,
        c.buildingId,
        c.penNumber,
        c.motherId || "-",
        c.fatherId || "-",
        (c.notes || "").replace(/,/g, " ") // Escape commas
    ]);

    // 3. Combine to CSV String
    const csvContent = [
        "\uFEFF" + headers.join(","), // Add BOM for Excel UTF-8
        ...rows.map(r => r.join(","))
    ].join("\n");

    // 4. Create Blob and Link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `hanwoo_data_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <button 
        onClick={handleDownload}
        style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            borderRadius: "8px",
            padding: "8px 12px",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            cursor: "pointer",
            fontSize: "12px",
            color: "var(--color-text)",
            fontWeight: 600,
            boxShadow: "var(--shadow-sm)"
        }}
    >
        <span style={{color:"#1D6F42", fontSize:"14px"}}>📑</span> 엑셀 다운로드
    </button>
  );
}
