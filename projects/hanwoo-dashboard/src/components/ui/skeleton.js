import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }) {
  return (
    <div
      className={cn("animate-pulse rounded-[14px] bg-muted/70 backdrop-blur-sm", className)}
      {...props}
    />
  )
}

export { Skeleton }
