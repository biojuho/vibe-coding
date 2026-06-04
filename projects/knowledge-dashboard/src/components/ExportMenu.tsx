"use client";

import { Check, Download } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import type { DashboardData, GithubRepo, Notebook } from "@/lib/dashboard-types";
import {
	buildNotebooksCsv,
	buildReposCsv,
	buildSummaryText,
} from "@/lib/dashboard-export";

interface ExportMenuProps {
	data: DashboardData;
	filteredGithub: GithubRepo[];
	filteredNotebooks: Notebook[];
}

function downloadFile(filename: string, content: string, mime: string) {
	const blob = new Blob([content], { type: `${mime};charset=utf-8` });
	const url = URL.createObjectURL(blob);
	const anchor = document.createElement("a");
	anchor.href = url;
	anchor.download = filename;
	document.body.appendChild(anchor);
	anchor.click();
	anchor.remove();
	URL.revokeObjectURL(url);
}

export default function ExportMenu({
	data,
	filteredGithub,
	filteredNotebooks,
}: ExportMenuProps) {
	const [open, setOpen] = useState(false);
	const [copied, setCopied] = useState(false);
	const containerRef = useRef<HTMLDivElement>(null);
	const buttonRef = useRef<HTMLButtonElement>(null);

	useEffect(() => {
		if (!open) return;

		const onPointerDown = (event: PointerEvent) => {
			if (!containerRef.current?.contains(event.target as Node)) {
				setOpen(false);
			}
		};
		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				setOpen(false);
				buttonRef.current?.focus();
			}
		};

		document.addEventListener("pointerdown", onPointerDown);
		document.addEventListener("keydown", onKeyDown);
		return () => {
			document.removeEventListener("pointerdown", onPointerDown);
			document.removeEventListener("keydown", onKeyDown);
		};
	}, [open]);

	const handleCopySummary = async () => {
		try {
			await navigator.clipboard.writeText(buildSummaryText(data));
			setCopied(true);
			window.setTimeout(() => setCopied(false), 2000);
		} catch {
			setCopied(false);
		}
		setOpen(false);
	};

	const items: Array<{ label: string; onSelect: () => void }> = [
		{
			label: `저장소 CSV (${filteredGithub.length})`,
			onSelect: () => {
				downloadFile(
					"repositories.csv",
					buildReposCsv(filteredGithub),
					"text/csv",
				);
				setOpen(false);
			},
		},
		{
			label: `노트북 CSV (${filteredNotebooks.length})`,
			onSelect: () => {
				downloadFile(
					"notebooks.csv",
					buildNotebooksCsv(filteredNotebooks),
					"text/csv",
				);
				setOpen(false);
			},
		},
		{
			label: "전체 JSON",
			onSelect: () => {
				downloadFile(
					"dashboard_data.json",
					JSON.stringify(data, null, 2),
					"application/json",
				);
				setOpen(false);
			},
		},
		{ label: "요약 복사", onSelect: handleCopySummary },
	];

	return (
		<div className="relative" ref={containerRef}>
			<Button
				ref={buttonRef}
				variant="outline"
				onClick={() => setOpen((value) => !value)}
				aria-haspopup="menu"
				aria-expanded={open}
				className="bg-white/5 hover:bg-white/10 border-white/10 backdrop-blur-md"
			>
				{copied ? (
					<Check className="w-4 h-4 text-emerald-400" aria-hidden="true" />
				) : (
					<Download className="w-4 h-4" aria-hidden="true" />
				)}
				{copied ? "복사됨" : "내보내기"}
			</Button>

			{open && (
				<div
					role="menu"
					aria-label="내보내기 옵션"
					className="absolute right-0 z-20 mt-2 w-52 overflow-hidden rounded-xl border border-white/10 bg-slate-900/95 p-1 shadow-2xl backdrop-blur-md"
				>
					{items.map((item) => (
						<button
							key={item.label}
							type="button"
							role="menuitem"
							onClick={item.onSelect}
							className="block w-full rounded-lg px-3 py-2 text-left text-sm text-slate-200 transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:bg-white/10"
						>
							{item.label}
						</button>
					))}
				</div>
			)}
		</div>
	);
}
