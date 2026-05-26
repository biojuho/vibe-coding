"use client";

import { Download } from "lucide-react";
import { useRef, useState } from "react";

import { useAppFeedback } from "@/components/feedback/FeedbackProvider";
import { PremiumButton } from "@/components/ui/premium-button";
import { buildCattleCsvRows } from "@/lib/cattle-csv-export.mjs";

const EXCEL_EXPORT_ERROR_MESSAGE =
	"내보내기 파일을 만들지 못했습니다. 잠시 후 다시 시도해 주세요.";

export default function ExcelExportButton({
	cattleList = [],
	resolveCattleList = null,
}) {
	const { notify } = useAppFeedback();
	const [isPreparing, setIsPreparing] = useState(false);
	const preparingRef = useRef(false);

	const handleDownload = async () => {
		if (preparingRef.current) return;

		preparingRef.current = true;
		setIsPreparing(true);

		try {
			const rows =
				typeof resolveCattleList === "function"
					? await resolveCattleList()
					: cattleList;

			if (!rows || rows.length === 0) {
				notify({
					title: "다운로드할 개체 데이터가 없습니다.",
					description: "등록된 개체를 확인한 뒤 다시 시도해 주세요.",
					variant: "warning",
				});
				return;
			}

			const csvContent = buildCattleCsvRows(rows);
			const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.setAttribute("href", url);
			link.setAttribute(
				"download",
				`hanwoo_data_${new Date().toISOString().slice(0, 10)}.csv`,
			);
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			URL.revokeObjectURL(url);
		} catch (error) {
			console.error("Failed to export cattle CSV:", error);
			notify({
				title: "엑셀 내보내기에 실패했습니다.",
				description: EXCEL_EXPORT_ERROR_MESSAGE,
				variant: "error",
			});
		} finally {
			preparingRef.current = false;
			setIsPreparing(false);
		}
	};

	return (
		<PremiumButton
			variant="secondary"
			size="sm"
			onClick={handleDownload}
			disabled={isPreparing}
			aria-busy={isPreparing}
			aria-label={
				isPreparing ? "개체 엑셀 다운로드 준비 중" : "개체 엑셀 다운로드"
			}
			title={
				isPreparing ? "개체 엑셀 다운로드 준비 중" : "개체 엑셀 다운로드"
			}
			className="gap-1.5 font-bold shadow-md"
		>
			<Download size={14} className="text-[#1D6F42]" aria-hidden="true" />
			{isPreparing ? "개체 엑셀 다운로드 준비 중..." : "개체 엑셀 다운로드"}
		</PremiumButton>
	);
}
