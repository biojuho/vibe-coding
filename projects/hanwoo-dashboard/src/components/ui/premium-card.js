import * as React from "react"
import { cn } from "@/lib/utils"

const PremiumCard = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "relative group bg-slate-800/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-xl hover:border-slate-600 transition-colors duration-300 overflow-hidden",
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
      {/* subtle gradient glow overlay */}
      <div className="absolute inset-0 bg-linear-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
      
      <PremiumCardContent className="p-6">
        <h4 className="text-sm font-medium text-slate-400 mb-2">{title}</h4>
        <div className="flex items-end justify-between">
          <div className="text-3xl font-bold text-slate-100 tracking-tight">
            {value}
          </div>
          <div
            className={cn(
              "flex items-center gap-1 text-sm font-semibold rounded-full px-2.5 py-0.5",
              isPositive 
                ? "text-emerald-400 bg-emerald-400/10 border border-emerald-400/20" 
                : "text-rose-400 bg-rose-400/10 border border-rose-400/20"
            )}
          >
            {isPositive ? "▲" : "▼"} {change}
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
