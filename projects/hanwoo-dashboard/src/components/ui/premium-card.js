import * as React from "react"
import { cn } from "@/lib/utils"

const PremiumCard = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "relative group bg-slate-800/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-xl overflow-hidden transition-[border-color,box-shadow,transform] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] hover:border-slate-600 hover:shadow-[0_8px_32px_rgba(0,0,0,0.24),0_0_0_1px_rgba(255,255,255,0.06)] hover:-translate-y-0.5",
      className
    )}
    {...props}
  />
))
PremiumCard.displayName = "PremiumCard"

const PremiumCardHeader = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6 relative z-10", className)}
    {...props}
  />
))
PremiumCardHeader.displayName = "PremiumCardHeader"

const PremiumCardTitle = React.forwardRef(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-2xl font-bold leading-none tracking-tight text-slate-100",
      className
    )}
    {...props}
  />
))
PremiumCardTitle.displayName = "PremiumCardTitle"

const PremiumCardDescription = React.forwardRef(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-slate-400 mt-1", className)}
    {...props}
  />
))
PremiumCardDescription.displayName = "PremiumCardDescription"

const PremiumCardContent = React.forwardRef(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0 relative z-10", className)} {...props} />
))
PremiumCardContent.displayName = "PremiumCardContent"

const PremiumCardFooter = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0 relative z-10", className)}
    {...props}
  />
))
PremiumCardFooter.displayName = "PremiumCardFooter"

const PremiumInfoCard = ({ title, value, change, changeType = "positive" }) => {
  const isPositive = changeType === "positive"
  
  return (
    <PremiumCard>
      {/* Radial glow overlay — reacts to hover */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(99,137,255,0.06)_0%,transparent_60%)] opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

      <PremiumCardContent className="p-6">
        <h4 className="text-[13px] font-medium text-slate-400 mb-3 tracking-wide uppercase">{title}</h4>
        <div className="flex items-end justify-between gap-3">
          <div className="text-[32px] font-extrabold text-slate-100 tracking-tight leading-none">
            {value}
          </div>
          <div
            className={cn(
              "flex items-center gap-1 text-[13px] font-semibold rounded-full px-2.5 py-1 transition-transform duration-200 hover:scale-105",
              isPositive
                ? "text-emerald-400 bg-emerald-400/10 border border-emerald-400/20"
                : "text-rose-400 bg-rose-400/10 border border-rose-400/20"
            )}
          >
            <span className="text-[10px]">{isPositive ? "▲" : "▼"}</span> {change}
          </div>
        </div>
      </PremiumCardContent>
    </PremiumCard>
  )
}

export { 
  PremiumCard, 
  PremiumCardHeader, 
  PremiumCardFooter, 
  PremiumCardTitle, 
  PremiumCardDescription, 
  PremiumCardContent,
  PremiumInfoCard
}
