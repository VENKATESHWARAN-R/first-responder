import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning"
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div className={cn(
        "inline-flex items-center border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        // Theme aware radius
        "rounded-[var(--radius)]",
        // Theme aware border width
        "border-[length:var(--border-neo)]",
        {
            "border-transparent bg-primary text-primary-foreground hover:bg-primary/80": variant === "default",
            "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80": variant === "secondary",
            "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80": variant === "destructive",
            "text-foreground border-[length:var(--border-neo)]": variant === "outline",
            "border-transparent bg-green-600 text-white hover:bg-green-700 shadow-sm": variant === "success",
            "border-transparent bg-yellow-500 text-black hover:bg-yellow-600 shadow-sm": variant === "warning",
        },
        className
    )} {...props} />
  )
}

export { Badge }
