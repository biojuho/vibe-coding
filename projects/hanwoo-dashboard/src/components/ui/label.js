"use client";

import * as LabelPrimitive from "@radix-ui/react-label";
import { cva } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const labelVariants = cva(
	"text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
);

function normalizeLabelOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

const Label = React.forwardRef((options, ref) => {
	const { className, ...props } = normalizeLabelOptions(options);

	return (
		<LabelPrimitive.Root
			ref={ref}
			className={cn(labelVariants(), className)}
			{...props}
		/>
	);
});
Label.displayName = LabelPrimitive.Root.displayName;

export { Label };
