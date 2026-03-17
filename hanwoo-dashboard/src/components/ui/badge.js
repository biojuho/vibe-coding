import * as React from "react"
import { cva } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold tracking-[0.02em] shadow-[var(--shadow-sm)] transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "[background:var(--surface-gradient-primary)] border-[color:var(--color-surface-stroke)] text-primary-foreground",
        secondary:
          "[background:var(--surface-gradient)] border-[color:var(--color-surface-stroke)] text-secondary-foreground",
        destructive:
          "bg-destructive/15 border-[color:color-mix(in_srgb,var(--color-danger)_28%,white_72%)] text-destructive",
        outline: "[background:var(--surface-gradient)] text-foreground",
        success:
          "[background:linear-gradient(145deg,color-mix(in_srgb,var(--color-success-light)_82%,white_18%),var(--color-success-light))] border-[color:var(--color-surface-stroke)] text-[color:var(--color-success)]",
        warning:
          "[background:linear-gradient(145deg,color-mix(in_srgb,var(--color-warning-light)_82%,white_18%),var(--color-warning-light))] border-[color:var(--color-surface-stroke)] text-[color:var(--color-warning)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({ className, variant, ...props }) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
