import React, { useState, useRef, useEffect } from 'react';

export function DropdownMenu({ children }) {
  return <div className="relative inline-block text-left">{children}</div>;
}

export function DropdownMenuTrigger({ asChild, children, ...props }) {
  return React.cloneElement(children, { ...props });
}

export function DropdownMenuContent({ align = "end", children, className }) {
  return (
    <div className={`clay-surface absolute right-0 mt-2 w-56 origin-top-right divide-y rounded-[22px] focus:outline-none z-50 ${className}`} style={{ borderColor: 'var(--color-surface-stroke)' }}>
      <div className="py-1">{children}</div>
    </div>
  );
}

export function DropdownMenuItem({ children, onClick, className }) {
  return (
    <div
      className={`block cursor-pointer rounded-[14px] px-4 py-2 text-sm transition-colors hover:bg-background/70 ${className}`}
      style={{ color: 'var(--color-text)' }}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

export function DropdownMenuLabel({ children }) {
  return <div className="px-4 py-2 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>{children}</div>;
}

export function DropdownMenuSeparator() {
  return <div className="my-1 border-t" style={{ borderColor: 'var(--color-surface-border)' }}></div>;
}
