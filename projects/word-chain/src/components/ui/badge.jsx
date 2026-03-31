import React from "react";
import { cn } from "@/lib/utils";

const Badge = React.forwardRef(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-md border border-cyber-blue/30 px-2.5 py-0.5 text-xs font-mono font-semibold text-cyber-blue transition-colors",
        className
      )}
      {...props}
    />
  )
);
Badge.displayName = "Badge";

export { Badge };
