"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

const Dialog = DialogPrimitive.Root;

const DialogTrigger = DialogPrimitive.Trigger;

const DialogPortal = DialogPrimitive.Portal;

const DialogClose = DialogPrimitive.Close;

function normalizeDialogOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

const DialogOverlay = React.forwardRef((options, ref) => {
	const { className, ...props } = normalizeDialogOptions(options);

	return (
		<DialogPrimitive.Overlay
			ref={ref}
			className={cn(
				"fixed inset-0 z-50 bg-[color:var(--color-overlay)]/90 backdrop-blur-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
				className,
			)}
			{...props}
		/>
	);
});
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

const DialogContent = React.forwardRef((options, ref) => {
	const {
		className,
		children,
		closeLabel = "대화상자 닫기",
		...props
	} = normalizeDialogOptions(options);

	return (
		<DialogPortal>
			<DialogOverlay />
			<DialogPrimitive.Content
				ref={ref}
				className={cn(
					"clay-surface fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background/90 p-7 backdrop-blur-xl shadow-[0_24px_64px_rgba(0,0,0,0.18)] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-[28px]",
					className,
				)}
				{...props}
			>
				{children}
				<DialogPrimitive.Close
					aria-label={closeLabel}
					title={closeLabel}
					className="absolute right-4 top-4 rounded-full p-1.5 opacity-70 ring-offset-background transition-[opacity,background,transform] duration-200 hover:opacity-100 hover:bg-secondary/60 hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground"
				>
					<X className="h-4 w-4" aria-hidden="true" />
					<span className="sr-only">{closeLabel}</span>
				</DialogPrimitive.Close>
			</DialogPrimitive.Content>
		</DialogPortal>
	);
});
DialogContent.displayName = DialogPrimitive.Content.displayName;

const DialogHeader = (options = {}) => {
	const { className, ...props } = normalizeDialogOptions(options);

	return (
		<div
			className={cn(
				"flex flex-col space-y-1.5 text-center sm:text-left",
				className,
			)}
			{...props}
		/>
	);
};
DialogHeader.displayName = "DialogHeader";

const DialogFooter = (options = {}) => {
	const { className, ...props } = normalizeDialogOptions(options);

	return (
		<div
			className={cn(
				"flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
				className,
			)}
			{...props}
		/>
	);
};
DialogFooter.displayName = "DialogFooter";

const DialogTitle = React.forwardRef((options, ref) => {
	const { className, ...props } = normalizeDialogOptions(options);

	return (
		<DialogPrimitive.Title
			ref={ref}
			className={cn(
				"text-lg font-bold leading-none tracking-[-0.01em]",
				className,
			)}
			{...props}
		/>
	);
});
DialogTitle.displayName = DialogPrimitive.Title.displayName;

const DialogDescription = React.forwardRef((options, ref) => {
	const { className, ...props } = normalizeDialogOptions(options);

	return (
		<DialogPrimitive.Description
			ref={ref}
			className={cn("text-sm text-muted-foreground", className)}
			{...props}
		/>
	);
});
DialogDescription.displayName = DialogPrimitive.Description.displayName;

export {
	Dialog,
	DialogClose,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogOverlay,
	DialogPortal,
	DialogTitle,
	DialogTrigger,
};
