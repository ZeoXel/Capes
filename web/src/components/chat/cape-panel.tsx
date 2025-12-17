"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronRight,
  Wrench,
  GitBranch,
  Code,
  Brain,
  Layers,
  Search,
  X,
} from "lucide-react";
import type { Cape, ExecutionType } from "@/data/types";
import { cn } from "@/lib/utils";

const executionIcons: Record<ExecutionType, typeof Wrench> = {
  tool: Wrench,
  workflow: GitBranch,
  code: Code,
  llm: Brain,
  hybrid: Layers,
};

interface CapePanelProps {
  capes: Cape[];
  isOpen: boolean;
  onClose: () => void;
  onSelect: (cape: Cape) => void;
}

export function CapePanel({ capes, isOpen, onClose, onSelect }: CapePanelProps) {
  const [search, setSearch] = useState("");

  const filtered = capes.filter(
    (cape) =>
      cape.name.toLowerCase().includes(search.toLowerCase()) ||
      cape.id.toLowerCase().includes(search.toLowerCase()) ||
      cape.tags.some((t) => t.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/20 z-40"
          />

          {/* Panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 w-80 bg-white border-l border-gray-200 z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900">可用能力</h2>
              <button
                onClick={onClose}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Search */}
            <div className="p-3 border-b border-gray-100">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="搜索能力..."
                  className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            {/* Cape list */}
            <div className="flex-1 overflow-auto">
              {filtered.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-sm">
                  没有找到匹配的能力
                </div>
              ) : (
                <div className="p-2">
                  {filtered.map((cape) => {
                    const Icon = executionIcons[cape.execution_type];
                    return (
                      <button
                        key={cape.id}
                        onClick={() => {
                          onSelect(cape);
                          onClose();
                        }}
                        className="w-full flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors text-left group"
                      >
                        <div className="flex-shrink-0 w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center group-hover:bg-blue-50 transition-colors">
                          <Icon className="w-4 h-4 text-gray-500 group-hover:text-blue-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900 text-sm truncate">
                              {cape.name}
                            </span>
                            <span className="text-xs text-gray-400 font-mono">
                              /{cape.id}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                            {cape.description}
                          </p>
                          <div className="flex gap-1 mt-1.5">
                            {cape.tags.slice(0, 3).map((tag) => (
                              <span
                                key={tag}
                                className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px] text-gray-500"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500 flex-shrink-0 mt-1" />
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-gray-100 text-xs text-gray-400 text-center">
              共 {capes.length} 个能力可用
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
