"use client";

import { SessionProvider } from "next-auth/react";
import { FeedbackProvider } from "@/components/feedback/FeedbackProvider";

export default function Providers({ children }) {
	return (
		<SessionProvider>
			<FeedbackProvider>{children}</FeedbackProvider>
		</SessionProvider>
	);
}
