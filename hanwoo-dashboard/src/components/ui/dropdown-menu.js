import React, { useState, useRef, useEffect } from 'react';

export function DropdownMenu({ children }) {
  return <div className="relative inline-block text-left">{children}</div>;
}

export function DropdownMenuTrigger({ asChild, children, ...props }) {
  return React.cloneElement(children, { ...props });
}

export function DropdownMenuContent({ align = "end", children, className }) {
  return (
    <div className={`absolute right-0 mt-2 w-56 origin-top-right bg-white divide-y divide-gray-100 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50 ${className}`}>
      <div className="py-1">{children}</div>
    </div>
  );
}

export function DropdownMenuItem({ children, onClick, className }) {
  return (
    <div
      className={`block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900 cursor-pointer ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

export function DropdownMenuLabel({ children }) {
  return <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">{children}</div>;
}

export function DropdownMenuSeparator() {
  return <div className="border-t border-gray-100 my-1"></div>;
}
