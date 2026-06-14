import React, { useEffect, useRef, useState } from "react";

function normalizeDropdownMenuOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export function DropdownMenu(options = {}) {
	const { children } = normalizeDropdownMenuOptions(options);
	return <div className="relative inline-block text-left">{children}</div>;
}

export function DropdownMenuTrigger(options = {}) {
	const { children, ...props } = normalizeDropdownMenuOptions(options);
	if (!React.isValidElement(children)) {
		return null;
	}

	return React.cloneElement(children, { ...props });
}

export function DropdownMenuContent(options = {}) {
	const { children, className = "" } = normalizeDropdownMenuOptions(options);
	return (
		<div
			className={`clay-surface absolute right-0 mt-2 w-56 origin-top-right divide-y rounded-[22px] focus:outline-none z-50 ${className}`}
			style={{ borderColor: "var(--color-surface-stroke)" }}
		>
			<div role="menu" className="py-1">{children}</div>
		</div>
	);
}

export function DropdownMenuItem(options = {}) {
	const { children, onClick, className = "", ...props } =
		normalizeDropdownMenuOptions(options);
	const handleClick = typeof onClick === "function" ? onClick : null;
	const Element = handleClick ? "button" : "div";

	return (
		<Element
			type={handleClick ? "button" : undefined}
			role="menuitem"
			className={`block w-full cursor-pointer rounded-[14px] px-4 py-2 text-left text-sm transition-colors hover:bg-background/70 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 ${className}`}
			style={{ color: "var(--color-text)" }}
			onClick={handleClick}
			{...props}
		>
			{children}
		</Element>
	);
}

export function DropdownMenuLabel(options = {}) {
	const { children } = normalizeDropdownMenuOptions(options);
	return (
		<div
			className="px-4 py-2 text-xs font-semibold uppercase tracking-wider"
			style={{ color: "var(--color-text-secondary)" }}
		>
			{children}
		</div>
	);
}

export function DropdownMenuSeparator() {
	return (
		<div
			className="my-1 border-t"
			style={{ borderColor: "var(--color-surface-border)" }}
		></div>
	);
}
