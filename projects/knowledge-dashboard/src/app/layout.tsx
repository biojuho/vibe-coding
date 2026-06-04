import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
	title: "나만의 지식 관리 대시보드",
	description: "GitHub + NotebookLM 통합 지식 관리 대시보드",
	applicationName: "Knowledge Dashboard",
	// Internal, authenticated dashboard — keep it out of search indexes.
	robots: { index: false, follow: false },
	openGraph: {
		title: "나만의 지식 관리 대시보드",
		description: "GitHub + NotebookLM 통합 지식 관리 대시보드",
		type: "website",
	},
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="ko">
			<body className="antialiased">{children}</body>
		</html>
	);
}
