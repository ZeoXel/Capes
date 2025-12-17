"use client";

import { useState, useEffect } from "react";
import { ChevronDown, Zap, Clock, DollarSign } from "lucide-react";
import { api, type Model } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ModelSelectorProps {
  value: string;
  onChange: (modelId: string) => void;
  className?: string;
}

const PROVIDER_COLORS = {
  google: "bg-blue-500",
  openai: "bg-emerald-500",
  anthropic: "bg-orange-500",
};

const PROVIDER_LABELS = {
  google: "Gemini",
  openai: "OpenAI",
  anthropic: "Claude",
};

const SPEED_ICONS = {
  fast: <Zap className="w-3 h-3 text-yellow-500" />,
  medium: <Clock className="w-3 h-3 text-blue-500" />,
  slow: <Clock className="w-3 h-3 text-gray-400" />,
};

const COST_LABELS = {
  low: "$",
  medium: "$$",
  high: "$$$",
};

export function ModelSelector({
  value,
  onChange,
  className,
}: ModelSelectorProps) {
  const [models, setModels] = useState<Model[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadModels() {
      try {
        const data = await api.getModels();
        setModels(data.models);

        // Set default if not set
        if (!value && data.default_model) {
          onChange(data.default_model);
        }
      } catch (error) {
        console.error("Failed to load models:", error);
      } finally {
        setIsLoading(false);
      }
    }

    loadModels();
  }, [value, onChange]);

  const selectedModel = models.find((m) => m.id === value);

  if (isLoading) {
    return (
      <div
        className={cn(
          "h-8 w-36 bg-gray-100 rounded-lg animate-pulse",
          className
        )}
      />
    );
  }

  return (
    <div className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-lg",
          "bg-gray-100 hover:bg-gray-200 border border-gray-200",
          "text-sm text-gray-700 transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-blue-500"
        )}
      >
        {selectedModel && (
          <>
            <span
              className={cn(
                "w-2 h-2 rounded-full",
                PROVIDER_COLORS[selectedModel.provider]
              )}
            />
            <span className="font-medium text-gray-900">{selectedModel.name}</span>
            <span className="text-xs text-gray-400">
              {COST_LABELS[selectedModel.cost_tier]}
            </span>
          </>
        )}
        {!selectedModel && <span className="text-gray-500">选择模型</span>}
        <ChevronDown
          className={cn("w-4 h-4 text-gray-400 transition-transform", {
            "rotate-180": isOpen,
          })}
        />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div
            className={cn(
              "absolute top-full left-0 mt-1 z-20",
              "w-64 max-h-80 overflow-auto",
              "bg-white border border-gray-200 rounded-xl shadow-lg"
            )}
          >
            {/* Group by provider */}
            {(["google", "openai", "anthropic"] as const).map((provider) => {
              const providerModels = models.filter(
                (m) => m.provider === provider
              );
              if (providerModels.length === 0) return null;

              return (
                <div key={provider}>
                  <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider bg-gray-50">
                    {PROVIDER_LABELS[provider]}
                  </div>
                  {providerModels.map((model) => (
                    <button
                      key={model.id}
                      type="button"
                      onClick={() => {
                        onChange(model.id);
                        setIsOpen(false);
                      }}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2",
                        "hover:bg-gray-50 transition-colors text-left",
                        value === model.id && "bg-blue-50"
                      )}
                    >
                      <span
                        className={cn(
                          "w-2 h-2 rounded-full flex-shrink-0",
                          PROVIDER_COLORS[model.provider]
                        )}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-900 truncate">
                            {model.name}
                          </span>
                          {model.default && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded">
                              默认
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-400">
                          <span className="flex items-center gap-1">
                            {SPEED_ICONS[model.speed]}
                            {model.speed}
                          </span>
                          <span className="flex items-center gap-1">
                            <DollarSign className="w-3 h-3" />
                            {model.cost_tier}
                          </span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
