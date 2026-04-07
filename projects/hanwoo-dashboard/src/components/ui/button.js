import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "clay-pressable inline-flex items-center justify-center whitespace-nowrap rounded-[18px] border text-sm font-semibold ring-offset-background transition-[transform,box-shadow,filter,background,border-color] duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.96] active:duration-100",
  {
    variants: {
      variant: {
        default:
          "[background:var(--surface-gradient-primary)] text-primary-foreground shadow-[var(--shadow-button-primary)] hover:brightness-[1.03] hover:shadow-[var(--shadow-glow)]",
        destructive:
          "bg-destructive/15 text-destructive border-[color:color-mix(in_srgb,var(--color-danger)_28%,white_72%)] hover:bg-destructive/20 hover:shadow-[0_0_16px_color-mix(in_srgb,var(--color-danger)_16%,transparent)]",
        outline:
          "clay-inset border-[color:var(--color-surface-border)] bg-transparent text-foreground hover:text-foreground hover:border-[color:var(--color-accent-custom)]",
        secondary:
          "bg-secondary/80 text-secondary-foreground border-[color:var(--color-surface-stroke)] hover:bg-secondary hover:border-[color:var(--color-accent-custom)]",
        ghost: "border-transparent bg-transparent shadow-none hover:bg-secondary/55 hover:text-foreground",
        link: "text-primary underline-offset-4 hover:underline shadow-none",
      },
      size: {
        default: "h-10 px-5 py-2",
        sm: "h-9 rounded-[14px] px-3.5",
        lg: "h-11 rounded-[20px] px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const Button = React.forwardRef(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
