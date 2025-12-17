"use client";

import { cn } from "@/lib/utils";
import type { ExecutionType, RiskLevel, ExecutionStatus } from "@/data/types";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "outline" | "soft";
  color?: "teal" | "indigo" | "amber" | "rose" | "emerald" | "slate";
  size?: "sm" | "md";
  className?: string;
}

const colorStyles = {
  teal: {
    default: "bg-teal-600 text-white",
    outline: "border-teal-600 text-teal-700 bg-teal-50",
    soft: "bg-teal-100 text-teal-700",
  },
  indigo: {
    default: "bg-indigo-600 text-white",
    outline: "border-indigo-600 text-indigo-700 bg-indigo-50",
    soft: "bg-indigo-100 text-indigo-700",
  },
  amber: {
    default: "bg-amber-500 text-white",
    outline: "border-amber-500 text-amber-700 bg-amber-50",
    soft: "bg-amber-100 text-amber-700",
  },
  rose: {
    default: "bg-rose-500 text-white",
    outline: "border-rose-500 text-rose-700 bg-rose-50",
    soft: "bg-rose-100 text-rose-700",
  },
  emerald: {
    default: "bg-emerald-500 text-white",
    outline: "border-emerald-500 text-emerald-700 bg-emerald-50",
    soft: "bg-emerald-100 text-emerald-700",
  },
  slate: {
    default: "bg-slate-600 text-white",
    outline: "border-slate-400 text-slate-600 bg-slate-50",
    soft: "bg-slate-100 text-slate-600",
  },
};

export function Badge({
  children,
  variant = "soft",
  color = "slate",
  size = "sm",
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center font-medium rounded-full border border-transparent",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm",
        colorStyles[color][variant],
        className
      )}
    >
      {children}
    </span>
  );
}

// Specialized badges
export function ExecutionTypeBadge({ type }: { type: ExecutionType }) {
  const config: Record<ExecutionType, { label: string; color: BadgeProps["color"] }> = {
    tool: { label: "Tool", color: "teal" },
    workflow: { label: "Workflow", color: "indigo" },
    code: { label: "Code", color: "slate" },
    llm: { label: "LLM", color: "amber" },
    hybrid: { label: "Hybrid", color: "rose" },
  };
  const { label, color } = config[type];
  return <Badge color={color}>{label}</Badge>;
}

export function RiskLevelBadge({ level }: { level: RiskLevel }) {
  const config: Record<RiskLevel, { label: string; color: BadgeProps["color"] }> = {
    low: { label: "低风险", color: "emerald" },
    medium: { label: "中风险", color: "amber" },
    high: { label: "高风险", color: "rose" },
    critical: { label: "严重", color: "rose" },
  };
  const { label, color } = config[level];
  return <Badge color={color} variant="outline">{label}</Badge>;
}

export function StatusBadge({ status }: { status: ExecutionStatus }) {
  const config: Record<ExecutionStatus, { label: string; color: BadgeProps["color"]; pulse?: boolean }> = {
    pending: { label: "等待中", color: "slate" },
    running: { label: "运行中", color: "teal", pulse: true },
    completed: { label: "已完成", color: "emerald" },
    failed: { label: "失败", color: "rose" },
  };
  const { label, color, pulse } = config[status];
  return (
    <Badge color={color} variant="soft" className={cn(pulse && "animate-pulse-soft")}>
      {pulse && (
        <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
      )}
      {label}
    </Badge>
  );
}
