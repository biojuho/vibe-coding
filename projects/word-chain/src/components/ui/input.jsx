import React from "react";
import { cn } from "@/lib/utils";

const Input = React.forwardRef(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex w-full bg-black/50 border-2 border-cyber-blue/50 rounded-full py-3 px-6 text-cyber-yellow font-mono focus:outline-none focus:border-cyber-pink focus:shadow-[0_0_20px_rgba(255,42,109,0.5)] transition-all disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-cyber-blue/40",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
