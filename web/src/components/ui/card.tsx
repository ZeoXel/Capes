"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function Card({ children, className, hover = false, onClick }: CardProps) {
  const Component = hover ? motion.div : "div";

  return (
    <Component
      className={cn(
        "bg-white rounded-xl border border-gray-100 shadow-sm",
        hover && "cursor-pointer card-hover",
        className
      )}
      onClick={onClick}
      {...(hover && {
        whileHover: { y: -2 },
        transition: { duration: 0.2 },
      })}
    >
      {children}
    </Component>
  );
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("px-5 py-4 border-b border-gray-50", className)}>
      {children}
    </div>
  );
}

export function CardContent({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("px-5 py-4", className)}>
      {children}
    </div>
  );
}

export function CardFooter({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("px-5 py-3 bg-gray-50/50 rounded-b-xl border-t border-gray-50", className)}>
      {children}
    </div>
  );
}
