"use client";

import * as ProgressPrimitive from "@radix-ui/react-progress";
import * as React from "react";

import { cn } from "@/lib/utils";

function normalizeProgressOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function normalizeProgressValue(value) {
	const numericValue = Number(value);
	if (!Number.isFinite(numericValue)) {
		return 0;
	}
	return Math.min(100, Math.max(0, numericValue));
}

const Progress = React.forwardRef((options, ref) => {
	const { className, value, ...props } = normalizeProgressOptions(options);
	const safeValue = normalizeProgressValue(value);

	return (
		<ProgressPrimitive.Root
			ref={ref}
			className={cn(
				"relative h-3 w-full overflow-hidden rounded-full bg-secondary/60 shadow-[var(--shadow-inset-soft)]",
				className,
			)}
			{...props}
		>
			<ProgressPrimitive.Indicator
				className="h-full w-full flex-1 bg-primary rounded-full transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]"
				style={{ transform: `translateX(-${100 - safeValue}%)` }}
			/>
		</ProgressPrimitive.Root>
	);
});
Progress.displayName = ProgressPrimitive.Root.displayName;

export { Progress };
