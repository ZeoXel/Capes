"use client";

import { motion } from "framer-motion";
import {
  Wrench,
  GitBranch,
  Code,
  Brain,
  Layers,
  Clock,
  Zap,
  Settings2,
  Shield,
} from "lucide-react";
import type { Cape, ExecutionType, RiskLevel } from "@/data/types";
import { cn } from "@/lib/utils";

const executionIcons: Record<ExecutionType, typeof Wrench> = {
  tool: Wrench,
  workflow: GitBranch,
  code: Code,
  llm: Brain,
  hybrid: Layers,
};

const typeColors: Record<ExecutionType, string> = {
  tool: "bg-emerald-50 text-emerald-600 border-emerald-100",
  workflow: "bg-violet-50 text-violet-600 border-violet-100",
  code: "bg-slate-50 text-slate-600 border-slate-100",
  llm: "bg-amber-50 text-amber-600 border-amber-100",
  hybrid: "bg-rose-50 text-rose-600 border-rose-100",
};

const riskColors: Record<RiskLevel, string> = {
  low: "text-green-600",
  medium: "text-yellow-600",
  high: "text-orange-600",
  critical: "text-red-600",
};

interface ToggleSwitchProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
}

function ToggleSwitch({ enabled, onChange }: ToggleSwitchProps) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onChange(!enabled);
      }}
      className={cn(
        "relative w-10 h-5 rounded-full transition-colors",
        enabled ? "bg-blue-600" : "bg-gray-200"
      )}
    >
      <motion.div
        className="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm"
        animate={{ left: enabled ? 20 : 2 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
      />
    </button>
  );
}

interface CapeConfigCardProps {
  cape: Cape;
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  onConfigure?: () => void;
}

export function CapeConfigCard({ cape, enabled, onToggle, onConfigure }: CapeConfigCardProps) {
  const Icon = executionIcons[cape.execution_type];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "relative flex flex-col p-4 rounded-xl border bg-white transition-all",
        enabled ? "border-gray-200" : "border-gray-100 opacity-60"
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className={cn(
          "w-10 h-10 rounded-xl flex items-center justify-center transition-colors",
          enabled ? typeColors[cape.execution_type] : "bg-gray-100 text-gray-400"
        )}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className={cn(
            "font-semibold truncate transition-colors",
            enabled ? "text-gray-900" : "text-gray-500"
          )}>
            {cape.name}
          </h3>
          <span className="text-xs text-gray-400 font-mono">/{cape.id}</span>
        </div>
        <ToggleSwitch enabled={enabled} onChange={onToggle} />
      </div>

      {/* Description */}
      <p className={cn(
        "text-sm line-clamp-2 mb-3 leading-relaxed",
        enabled ? "text-gray-500" : "text-gray-400"
      )}>
        {cape.description}
      </p>

      {/* Intent Patterns */}
      <div className="mb-3">
        <div className="text-xs text-gray-400 mb-1.5">触发意图</div>
        <div className="flex flex-wrap gap-1">
          {cape.intent_patterns.slice(0, 3).map((pattern) => (
            <span
              key={pattern}
              className={cn(
                "px-2 py-0.5 rounded-md text-xs",
                enabled ? "bg-blue-50 text-blue-600" : "bg-gray-50 text-gray-400"
              )}
            >
              "{pattern}"
            </span>
          ))}
          {cape.intent_patterns.length > 3 && (
            <span className="text-xs text-gray-400">
              +{cape.intent_patterns.length - 3}
            </span>
          )}
        </div>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {cape.tags.slice(0, 3).map((tag) => (
          <span
            key={tag}
            className="px-2 py-0.5 bg-gray-50 rounded-md text-xs text-gray-500"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-50">
        <div className="flex items-center gap-3 text-xs text-gray-400">
          {cape.timeout_seconds && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {cape.timeout_seconds}s
            </span>
          )}
          <span className="flex items-center gap-1">
            <Zap className="w-3 h-3" />
            {cape.execution_type}
          </span>
          <span className={cn("flex items-center gap-1", riskColors[cape.risk_level])}>
            <Shield className="w-3 h-3" />
            {cape.risk_level}
          </span>
        </div>
        {onConfigure && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onConfigure();
            }}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors text-gray-400 hover:text-gray-600"
            title="配置"
          >
            <Settings2 className="w-4 h-4" />
          </button>
        )}
      </div>
    </motion.div>
  );
}

interface CapeConfigGridProps {
  capes: Cape[];
  enabledCapes: Set<string>;
  onToggle: (capeId: string, enabled: boolean) => void;
  columns?: 2 | 3;
}

export function CapeConfigGrid({ capes, enabledCapes, onToggle, columns = 2 }: CapeConfigGridProps) {
  const gridCols = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
  };

  return (
    <div className={cn("grid gap-4", gridCols[columns])}>
      {capes.map((cape, i) => (
        <motion.div
          key={cape.id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.03 }}
        >
          <CapeConfigCard
            cape={cape}
            enabled={enabledCapes.has(cape.id)}
            onToggle={(enabled) => onToggle(cape.id, enabled)}
          />
        </motion.div>
      ))}
    </div>
  );
}

// Compact version for showing which capes are available (read-only)
interface CapeCompactListProps {
  capes: Cape[];
  enabledCapes: Set<string>;
}

export function CapeCompactList({ capes, enabledCapes }: CapeCompactListProps) {
  const enabledList = capes.filter(c => enabledCapes.has(c.id));

  return (
    <div className="flex flex-wrap gap-2">
      {enabledList.map((cape) => {
        const Icon = executionIcons[cape.execution_type];
        return (
          <div
            key={cape.id}
            className={cn(
              "flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs",
              typeColors[cape.execution_type]
            )}
          >
            <Icon className="w-3 h-3" />
            <span className="font-medium">{cape.name}</span>
          </div>
        );
      })}
    </div>
  );
}
