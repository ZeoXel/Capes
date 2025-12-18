"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Briefcase,
  PenTool,
  ChevronDown,
  ChevronRight,
  Package,
  Users,
  Zap,
  Check,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Pack, Cape } from "@/data/types";

// Icon mapping for packs
const packIcons: Record<string, React.ElementType> = {
  briefcase: Briefcase,
  "pen-tool": PenTool,
  default: Package,
};

interface PackCardProps {
  pack: Pack;
  capes: Cape[];
  enabledCapes: Set<string>;
  onToggleCape: (capeId: string, enabled: boolean) => void;
  onEnableAll: () => void;
  onDisableAll: () => void;
  defaultExpanded?: boolean;
}

export function PackCard({
  pack,
  capes,
  enabledCapes,
  onToggleCape,
  onEnableAll,
  onDisableAll,
  defaultExpanded = false,
}: PackCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const Icon = packIcons[pack.icon || "default"] || Package;
  const enabledCount = capes.filter((c) => enabledCapes.has(c.id)).length;
  const allEnabled = enabledCount === capes.length;
  const someEnabled = enabledCount > 0 && enabledCount < capes.length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Pack Header */}
      <div
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: `${pack.color}15` }}
            >
              <Icon
                className="w-5 h-5"
                style={{ color: pack.color || "#3B82F6" }}
              />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-gray-900">
                  {pack.display_name}
                </h3>
                <span className="text-xs text-gray-400">v{pack.version}</span>
              </div>
              <p className="text-sm text-gray-500 mt-0.5 line-clamp-2">
                {pack.description}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0 ml-4">
            {/* Stats */}
            <div className="flex items-center gap-3 text-sm mr-2">
              <span
                className={cn(
                  "font-medium",
                  allEnabled
                    ? "text-green-600"
                    : someEnabled
                      ? "text-blue-600"
                      : "text-gray-400"
                )}
              >
                {enabledCount}/{capes.length}
              </span>
            </div>

            {/* Expand icon */}
            {isExpanded ? (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronRight className="w-5 h-5 text-gray-400" />
            )}
          </div>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {pack.target_users.slice(0, 3).map((user) => (
            <span
              key={user}
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full"
            >
              <Users className="w-3 h-3" />
              {user}
            </span>
          ))}
          {pack.scenarios.slice(0, 2).map((scenario) => (
            <span
              key={scenario}
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-600 text-xs rounded-full"
            >
              <Zap className="w-3 h-3" />
              {scenario}
            </span>
          ))}
        </div>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-gray-100 px-4 py-3 bg-gray-50/50">
              {/* Quick actions */}
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-500">
                  包含 {capes.length} 个能力
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onEnableAll();
                    }}
                    className="text-xs text-blue-600 hover:text-blue-700"
                  >
                    全部启用
                  </button>
                  <span className="text-gray-300">|</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDisableAll();
                    }}
                    className="text-xs text-gray-500 hover:text-gray-700"
                  >
                    全部禁用
                  </button>
                </div>
              </div>

              {/* Cape list */}
              <div className="space-y-2">
                {capes.map((cape) => {
                  const isEnabled = enabledCapes.has(cape.id);
                  return (
                    <div
                      key={cape.id}
                      className={cn(
                        "flex items-center justify-between p-2.5 rounded-lg transition-colors cursor-pointer",
                        isEnabled
                          ? "bg-white border border-blue-200"
                          : "bg-white/50 border border-transparent hover:border-gray-200"
                      )}
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleCape(cape.id, !isEnabled);
                      }}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              "font-medium text-sm",
                              isEnabled ? "text-gray-900" : "text-gray-600"
                            )}
                          >
                            {cape.name}
                          </span>
                          <span className="text-xs text-gray-400">
                            {cape.execution_type}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                          {cape.description}
                        </p>
                      </div>

                      {/* Toggle */}
                      <div
                        className={cn(
                          "w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ml-3 transition-colors",
                          isEnabled
                            ? "bg-blue-600 text-white"
                            : "bg-gray-200 text-gray-400"
                        )}
                      >
                        {isEnabled && <Check className="w-3 h-3" />}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface PackListProps {
  packs: Pack[];
  capesByPack: Map<string, Cape[]>;
  enabledCapes: Set<string>;
  onToggleCape: (capeId: string, enabled: boolean) => void;
  onEnablePackCapes: (packName: string) => void;
  onDisablePackCapes: (packName: string) => void;
}

export function PackList({
  packs,
  capesByPack,
  enabledCapes,
  onToggleCape,
  onEnablePackCapes,
  onDisablePackCapes,
}: PackListProps) {
  return (
    <div className="space-y-4">
      {packs.map((pack, index) => (
        <PackCard
          key={pack.name}
          pack={pack}
          capes={capesByPack.get(pack.name) || []}
          enabledCapes={enabledCapes}
          onToggleCape={onToggleCape}
          onEnableAll={() => onEnablePackCapes(pack.name)}
          onDisableAll={() => onDisablePackCapes(pack.name)}
          defaultExpanded={index === 0}
        />
      ))}
    </div>
  );
}

// Simple pack badge for compact display
interface PackBadgeProps {
  pack: Pack;
  enabledCount: number;
  totalCount: number;
  onClick?: () => void;
}

export function PackBadge({
  pack,
  enabledCount,
  totalCount,
  onClick,
}: PackBadgeProps) {
  const Icon = packIcons[pack.icon || "default"] || Package;
  const allEnabled = enabledCount === totalCount;

  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-colors",
        allEnabled
          ? "bg-blue-50 text-blue-700 border border-blue-200"
          : "bg-gray-50 text-gray-600 border border-gray-200 hover:border-gray-300"
      )}
    >
      <Icon className="w-4 h-4" />
      <span className="font-medium">{pack.display_name}</span>
      <span
        className={cn(
          "text-xs",
          allEnabled ? "text-blue-500" : "text-gray-400"
        )}
      >
        {enabledCount}/{totalCount}
      </span>
    </button>
  );
}
