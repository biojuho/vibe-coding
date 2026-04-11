import * as React from "react"
import { cn } from "@/lib/utils"

const PremiumCard = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "premium-card-clay group",
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
      "text-2xl font-bold leading-none tracking-tight",
      className
    )}
    style={{ color: 'var(--premium-card-title)' }}
    {...props}
  />
))
PremiumCardTitle.displayName = "PremiumCardTitle"

const PremiumCardDescription = React.forwardRef(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm mt-1", className)}
    style={{ color: 'var(--premium-card-subtitle)' }}
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
      {/* Ambient radial glow — matches clay theme */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at top left, color-mix(in srgb, var(--color-primary-light) 8%, transparent) 0%, transparent 60%)',
        }}
      />

      <PremiumCardContent className="p-6">
        <h4
          className="text-[13px] font-medium mb-3 tracking-wide uppercase"
          style={{ color: 'var(--premium-card-subtitle)' }}
        >
          {title}
        </h4>
        <div className="flex items-end justify-between gap-3">
          <div
            className="text-[32px] font-extrabold tracking-tight leading-none"
            style={{ color: 'var(--premium-card-value)', fontFamily: 'var(--font-display)' }}
          >
            {value}
          </div>
          {change && (
            <div
              className="flex items-center gap-1 text-[13px] font-semibold rounded-full px-2.5 py-1 transition-transform duration-200 hover:scale-105"
              style={{
                color: isPositive ? 'var(--premium-card-badge-positive-text)' : 'var(--premium-card-badge-negative-text)',
                background: isPositive ? 'var(--premium-card-badge-positive-bg)' : 'var(--premium-card-badge-negative-bg)',
                border: `1px solid ${isPositive ? 'var(--premium-card-badge-positive-border)' : 'var(--premium-card-badge-negative-border)'}`,
              }}
            >
              <span className="text-[10px]">{isPositive ? "▲" : "▼"}</span> {change}
            </div>
          )}
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

