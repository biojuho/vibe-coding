import "./globals.css";
import {
	Cormorant_Garamond,
	Noto_Sans_KR,
	Noto_Serif_KR,
} from "next/font/google";
import { Suspense } from "react";
import { FeedbackProvider } from "@/components/feedback/FeedbackProvider";

const notoSansKr = Noto_Sans_KR({
	weight: ["400", "500", "700"],
	variable: "--font-noto-sans-kr",
	display: "swap",
	preload: false,
});

const notoSerifKr = Noto_Serif_KR({
	weight: ["600", "700"],
	variable: "--font-noto-serif-kr",
	display: "swap",
	preload: false,
});

const cormorantGaramond = Cormorant_Garamond({
	subsets: ["latin"],
	weight: ["600", "700"],
	variable: "--font-cormorant-garamond",
	display: "swap",
});

export const metadata = {
	title: "Joolife 한우 농장 관리",
	description:
		"한우 농장의 개체, 번식, 출하, 재고, 일정을 한곳에서 관리하는 운영 대시보드",
	manifest: "/manifest.json",
	appleWebApp: {
		capable: true,
		statusBarStyle: "black-translucent",
		title: "Joolife 한우",
	},
};

export default function RootLayout({ children }) {
	return (
		<html lang="ko" suppressHydrationWarning>
			<body
				className={`${notoSansKr.variable} ${notoSerifKr.variable} ${cormorantGaramond.variable}`}
			>
				<FeedbackProvider>
					<Suspense>{children}</Suspense>
				</FeedbackProvider>
			</body>
		</html>
	);
}
