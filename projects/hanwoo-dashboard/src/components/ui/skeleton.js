import { cn } from "@/lib/utils";

function normalizeSkeletonOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

function Skeleton(options = {}) {
	const { className, ...props } = normalizeSkeletonOptions(options);

	return (
		<div
			className={cn(
				"animate-pulse rounded-[14px] bg-muted/70 backdrop-blur-sm",
				className,
			)}
			{...props}
		/>
	);
}

export { Skeleton };
