"use client";

import * as AvatarPrimitive from "@radix-ui/react-avatar";
import * as React from "react";

import { cn } from "@/lib/utils";

function normalizeAvatarOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

const Avatar = React.forwardRef((options, ref) => {
	const { className, ...props } = normalizeAvatarOptions(options);

	return (
		<AvatarPrimitive.Root
			ref={ref}
			className={cn(
				"relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full",
				className,
			)}
			{...props}
		/>
	);
});
Avatar.displayName = AvatarPrimitive.Root.displayName;

const AvatarImage = React.forwardRef((options, ref) => {
	const { className, ...props } = normalizeAvatarOptions(options);

	return (
		<AvatarPrimitive.Image
			ref={ref}
			className={cn("aspect-square h-full w-full", className)}
			{...props}
		/>
	);
});
AvatarImage.displayName = AvatarPrimitive.Image.displayName;

const AvatarFallback = React.forwardRef((options, ref) => {
	const { className, ...props } = normalizeAvatarOptions(options);

	return (
		<AvatarPrimitive.Fallback
			ref={ref}
			className={cn(
				"flex h-full w-full items-center justify-center rounded-full bg-muted",
				className,
			)}
			{...props}
		/>
	);
});
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName;

export { Avatar, AvatarFallback, AvatarImage };
