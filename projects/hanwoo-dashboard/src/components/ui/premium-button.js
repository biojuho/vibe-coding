import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

const premiumButtonVariants = cva(
  "relative inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition-all duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.97]",
  {
    variants: {
      variant: {
        default:
          "bg-blue-600 text-white border border-blue-500/30 shadow-[0_0_15px_rgba(37,99,235,0.25)] hover:bg-blue-500 hover:shadow-[0_0_25px_rgba(37,99,235,0.45)] hover:-translate-y-0.5",
        secondary:
          "bg-slate-800 text-slate-100 border border-slate-600 shadow-sm hover:shadow-md hover:bg-slate-700 hover:-translate-y-0.5",
        destructive:
          "bg-rose-500 text-white border border-rose-500/30 shadow-[0_0_15px_rgba(244,63,94,0.25)] hover:bg-rose-400 hover:-translate-y-0.5",
        outline:
          "border border-slate-600 bg-transparent text-slate-200 hover:bg-slate-800 hover:border-slate-500",
        ghost: "hover:bg-slate-800/50 text-slate-200",
        link: "text-blue-400 underline-offset-4 hover:underline",
      },
      size: {
        default: "h-11 px-5 py-2",
        sm: "h-9 rounded-lg px-4",
        lg: "h-12 rounded-xl px-8 text-base",
        icon: "h-11 w-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const PremiumButton = React.forwardRef(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(premiumButtonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
PremiumButton.displayName = "PremiumButton"

export { PremiumButton, premiumButtonVariants }
