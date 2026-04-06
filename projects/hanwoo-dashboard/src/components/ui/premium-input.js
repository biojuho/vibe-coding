import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';

const PremiumInput = forwardRef(({ className, type = 'text', hasError, ...props }, ref) => {
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
        type === 'date' ? "font-mono" : "",
        className
      )}
      ref={ref}
      {...props}
    />
  );
});
PremiumInput.displayName = "PremiumInput";

const PremiumTextarea = forwardRef(({ className, hasError, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        "w-full px-4 py-3.5 rounded-xl border bg-slate-900/40 text-slate-100 placeholder:text-slate-500",
        "focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent",
        "transition-all duration-200 shadow-inner resize-none",
        hasError 
          ? "border-destructive/60 focus:ring-destructive/40" 
          : "border-slate-700/50 hover:bg-slate-800/60",
        className
      )}
      ref={ref}
      {...props}
    />
  );
});
PremiumTextarea.displayName = "PremiumTextarea";

const PremiumSelect = forwardRef(({ className, hasError, children, ...props }, ref) => {
  return (
    <select
      className={cn(
        "w-full px-4 py-3.5 rounded-xl border bg-slate-900/40 text-slate-100 placeholder:text-slate-500",
        "focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent",
        "transition-all duration-200 shadow-inner appearance-none",
        hasError 
          ? "border-destructive/60 focus:ring-destructive/40" 
          : "border-slate-700/50 hover:bg-slate-800/60",
        className
      )}
      ref={ref}
      {...props}
    >
      {children}
    </select>
  );
});
PremiumSelect.displayName = "PremiumSelect";

const PremiumLabel = forwardRef(({ className, children, ...props }, ref) => {
  return (
    <label
      className={cn(
        "block text-xs font-semibold text-slate-400 mb-1.5",
        className
      )}
      ref={ref}
      {...props}
    >
      {children}
    </label>
  );
});
PremiumLabel.displayName = "PremiumLabel";

export { PremiumInput, PremiumTextarea, PremiumSelect, PremiumLabel };
