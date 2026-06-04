import type { MetadataRoute } from "next";

// Web app manifest so the dashboard is installable and the OS UI matches the
// dark theme. Next serves this at /manifest.webmanifest.
export default function manifest(): MetadataRoute.Manifest {
	return {
		name: "나만의 지식 관리 대시보드",
		short_name: "Knowledge",
		description: "GitHub + NotebookLM 통합 지식 관리 대시보드",
		start_url: "/",
		display: "standalone",
		background_color: "#0f172a",
		theme_color: "#0f172a",
		icons: [
			{
				src: "/icon.svg",
				type: "image/svg+xml",
				sizes: "any",
				purpose: "any",
			},
		],
	};
}
