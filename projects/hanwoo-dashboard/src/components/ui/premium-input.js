import React, { forwardRef } from "react";
import { cn } from "@/lib/utils";

function normalizePremiumInputOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

const PremiumInput = forwardRef((options, ref) => {
	const { className, type = "text", hasError, ...props } =
		normalizePremiumInputOptions(options);

	return (
		<input
			type={type}
			className={cn(
				"w-full px-4 py-3.5 rounded-xl border bg-slate-900/40 text-slate-100 placeholder:text-slate-500",
				"focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent",
				"transition-all duration-200 shadow-inner",
				hasError
					? "border-destructive/60 focus:ring-destructive/40"
					: "border-slate-700/50 hover:bg-slate-800/60",
				type === "date" ? "font-mono" : "",
				className,
			)}
			ref={ref}
			{...props}
		/>
	);
});
PremiumInput.displayName = "PremiumInput";

const PremiumTextarea = forwardRef((options, ref) => {
	const { className, hasError, ...props } =
		normalizePremiumInputOptions(options);

	return (
		<textarea
			className={cn(
				"w-full px-4 py-3.5 rounded-xl border bg-slate-900/40 text-slate-100 placeholder:text-slate-500",
				"focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent",
				"transition-all duration-200 shadow-inner resize-none",
				hasError
					? "border-destructive/60 focus:ring-destructive/40"
					: "border-slate-700/50 hover:bg-slate-800/60",
				className,
			)}
			ref={ref}
			{...props}
		/>
	);
});
PremiumTextarea.displayName = "PremiumTextarea";

const PremiumSelect = forwardRef((options, ref) => {
	const { className, hasError, children, ...props } =
		normalizePremiumInputOptions(options);

	return (
		<select
			className={cn(
				"w-full px-4 py-3.5 rounded-xl border bg-slate-900/40 text-slate-100 placeholder:text-slate-500",
				"focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent",
				"transition-all duration-200 shadow-inner appearance-none",
				hasError
					? "border-destructive/60 focus:ring-destructive/40"
					: "border-slate-700/50 hover:bg-slate-800/60",
				className,
			)}
			ref={ref}
			{...props}
		>
			{children}
		</select>
	);
});
PremiumSelect.displayName = "PremiumSelect";

const PremiumLabel = forwardRef((options, ref) => {
	const { className, children, ...props } =
		normalizePremiumInputOptions(options);

	return (
		<label
			className={cn(
				"block text-xs font-semibold text-slate-400 mb-1.5",
				className,
			)}
			ref={ref}
			{...props}
		>
			{children}
		</label>
	);
});
PremiumLabel.displayName = "PremiumLabel";

export { PremiumInput, PremiumLabel, PremiumSelect, PremiumTextarea };
