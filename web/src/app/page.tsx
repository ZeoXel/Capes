"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Settings,
  Puzzle,
  MessageSquare,
  Search,
  RefreshCw,
  Package,
  Grid3X3,
} from "lucide-react";
import {
  MessageItem,
  TypingIndicator,
  type Message,
} from "@/components/chat/message";
import { ChatInput } from "@/components/chat/input";
import { CapeConfigGrid, CapeCompactList } from "@/components/cape-card";
import { PackList, PackBadge } from "@/components/pack-card";
import { ModelSelector } from "@/components/model-selector";
import { useChat } from "@/hooks/use-chat";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Cape, Pack } from "@/data/types";

type ViewMode = "chat" | "capabilities";

export default function HomePage() {
  // Capes state
  const [capes, setCapes] = useState<Cape[]>([]);
  const [isLoadingCapes, setIsLoadingCapes] = useState(true);
  const [enabledCapes, setEnabledCapes] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");

  // Packs state
  const [packs, setPacks] = useState<Pack[]>([]);
  const [isLoadingPacks, setIsLoadingPacks] = useState(true);

  // Model state
  const [selectedModel, setSelectedModel] = useState("gemini-2.5-flash");

  // View state
  const [viewMode, setViewMode] = useState<ViewMode>("chat");
  const [capesViewMode, setCapesViewMode] = useState<"packs" | "grid">("packs");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Chat hook
  const { messages, isStreaming, currentCape, sendMessage, clearMessages } =
    useChat({
      onError: (error) => {
        console.error("Chat error:", error);
      },
    });

  // Load capes and packs on mount
  useEffect(() => {
    async function loadCapes() {
      try {
        const data = await api.getCapes();
        setCapes(data);
        // Enable all capes by default
        setEnabledCapes(new Set(data.map((c) => c.id)));
      } catch (error) {
        console.error("Failed to load capes:", error);
      } finally {
        setIsLoadingCapes(false);
      }
    }

    async function loadPacks() {
      try {
        const data = await api.getPacks();
        setPacks(data.packs);
      } catch (error) {
        console.error("Failed to load packs:", error);
      } finally {
        setIsLoadingPacks(false);
      }
    }

    loadCapes();
    loadPacks();
  }, []);

  // Scroll to bottom on new messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming, scrollToBottom]);

  // Filter capes by search query
  const filteredCapes = capes.filter(
    (cape) =>
      cape.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cape.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cape.tags.some((t) =>
        t.toLowerCase().includes(searchQuery.toLowerCase())
      ) ||
      cape.intent_patterns.some((p) =>
        p.toLowerCase().includes(searchQuery.toLowerCase())
      )
  );

  const handleToggleCape = (capeId: string, enabled: boolean) => {
    setEnabledCapes((prev) => {
      const next = new Set(prev);
      if (enabled) {
        next.add(capeId);
      } else {
        next.delete(capeId);
      }
      return next;
    });
  };

  // Build capes by pack mapping
  const capesByPack = useMemo(() => {
    const map = new Map<string, Cape[]>();
    for (const pack of packs) {
      const packCapes = capes.filter((c) => pack.cape_ids.includes(c.id));
      map.set(pack.name, packCapes);
    }
    return map;
  }, [capes, packs]);

  // Get capes not in any pack
  const unpackedCapes = useMemo(() => {
    const packedIds = new Set(packs.flatMap((p) => p.cape_ids));
    return capes.filter((c) => !packedIds.has(c.id));
  }, [capes, packs]);

  const handleEnablePackCapes = (packName: string) => {
    const packCapes = capesByPack.get(packName) || [];
    setEnabledCapes((prev) => {
      const next = new Set(prev);
      packCapes.forEach((c) => next.add(c.id));
      return next;
    });
  };

  const handleDisablePackCapes = (packName: string) => {
    const packCapes = capesByPack.get(packName) || [];
    setEnabledCapes((prev) => {
      const next = new Set(prev);
      packCapes.forEach((c) => next.delete(c.id));
      return next;
    });
  };

  const handleSend = async (content: string) => {
    // Ensure we're in chat mode
    if (viewMode === "capabilities") setViewMode("chat");

    // Send message with selected model and enabled capes
    const enabledCapeIds = Array.from(enabledCapes);
    await sendMessage(content, selectedModel, enabledCapeIds);
  };

  const handleRefreshCapes = async () => {
    setIsLoadingCapes(true);
    try {
      const data = await api.getCapes();
      setCapes(data);
    } catch (error) {
      console.error("Failed to refresh capes:", error);
    } finally {
      setIsLoadingCapes(false);
    }
  };

  const hasMessages = messages.length > 0;
  const enabledCount = enabledCapes.size;

  // Convert useChat messages to component format
  const displayMessages: Message[] = messages.map((m) => ({
    ...m,
    execution: m.execution
      ? {
          cape_id: m.execution.cape_id,
          cape_name: m.execution.cape_name,
          status: m.execution.status,
          duration_ms: m.execution.duration_ms,
        }
      : undefined,
  }));

  return (
    <div className="h-screen flex flex-col bg-gray-50/50">
      {/* Header */}
      <header className="flex-shrink-0 bg-white border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-gray-900">CAPE Agent</span>
          </div>

          <div className="flex items-center gap-1">
            {/* Model selector */}
            <ModelSelector
              value={selectedModel}
              onChange={setSelectedModel}
              className="mr-2"
            />

            {/* View toggle */}
            <div className="flex items-center bg-gray-100 rounded-lg p-1 mr-2">
              <button
                onClick={() => setViewMode("chat")}
                className={cn(
                  "p-1.5 rounded-md transition-colors",
                  viewMode === "chat"
                    ? "bg-white shadow-sm text-blue-600"
                    : "text-gray-500 hover:text-gray-700"
                )}
                title="对话"
              >
                <MessageSquare className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode("capabilities")}
                className={cn(
                  "p-1.5 rounded-md transition-colors flex items-center gap-1",
                  viewMode === "capabilities"
                    ? "bg-white shadow-sm text-blue-600"
                    : "text-gray-500 hover:text-gray-700"
                )}
                title="能力配置"
              >
                <Puzzle className="w-4 h-4" />
                <span className="text-xs font-medium">{enabledCount}</span>
              </button>
            </div>

            <button
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="设置"
            >
              <Settings className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <AnimatePresence mode="wait">
          {viewMode === "capabilities" ? (
            <motion.div
              key="capabilities"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="max-w-5xl mx-auto px-4 py-6"
            >
              {/* Header */}
              <div className="mb-6 flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-1">
                    能力配置
                  </h2>
                  <p className="text-gray-500 text-sm">
                    开启或关闭能力，Agent 将在对话中自动调用已启用的能力
                  </p>
                </div>
                <button
                  onClick={handleRefreshCapes}
                  disabled={isLoadingCapes}
                  className={cn(
                    "p-2 rounded-lg transition-colors",
                    "text-gray-500 hover:text-gray-700 hover:bg-gray-100",
                    isLoadingCapes && "animate-spin"
                  )}
                  title="刷新能力列表"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>

              {/* Search */}
              <div className="mb-6">
                <div className="relative max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="搜索能力..."
                    className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                </div>
              </div>

              {/* Stats & View Toggle */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-gray-500">共 {capes.length} 个能力</span>
                  <span className="text-blue-600 font-medium">
                    {enabledCount} 个已启用
                  </span>
                  {enabledCount < capes.length && (
                    <button
                      onClick={() =>
                        setEnabledCapes(new Set(capes.map((c) => c.id)))
                      }
                      className="text-gray-500 hover:text-gray-700"
                    >
                      全部启用
                    </button>
                  )}
                  {enabledCount > 0 && (
                    <button
                      onClick={() => setEnabledCapes(new Set())}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      全部禁用
                    </button>
                  )}
                </div>

                {/* View mode toggle */}
                <div className="flex items-center bg-gray-100 rounded-lg p-1">
                  <button
                    onClick={() => setCapesViewMode("packs")}
                    className={cn(
                      "px-3 py-1.5 rounded-md text-sm transition-colors flex items-center gap-1.5",
                      capesViewMode === "packs"
                        ? "bg-white shadow-sm text-blue-600"
                        : "text-gray-500 hover:text-gray-700"
                    )}
                  >
                    <Package className="w-4 h-4" />
                    能力包
                  </button>
                  <button
                    onClick={() => setCapesViewMode("grid")}
                    className={cn(
                      "px-3 py-1.5 rounded-md text-sm transition-colors flex items-center gap-1.5",
                      capesViewMode === "grid"
                        ? "bg-white shadow-sm text-blue-600"
                        : "text-gray-500 hover:text-gray-700"
                    )}
                  >
                    <Grid3X3 className="w-4 h-4" />
                    全部
                  </button>
                </div>
              </div>

              {/* Content */}
              {isLoadingCapes || isLoadingPacks ? (
                <div className="space-y-4">
                  {[1, 2].map((i) => (
                    <div
                      key={i}
                      className="h-40 bg-white rounded-xl animate-pulse border border-gray-100"
                    />
                  ))}
                </div>
              ) : capesViewMode === "packs" ? (
                <div className="space-y-6">
                  {/* Pack List */}
                  {packs.length > 0 && (
                    <PackList
                      packs={packs}
                      capesByPack={capesByPack}
                      enabledCapes={enabledCapes}
                      onToggleCape={handleToggleCape}
                      onEnablePackCapes={handleEnablePackCapes}
                      onDisablePackCapes={handleDisablePackCapes}
                    />
                  )}

                  {/* Unpacked capes */}
                  {unpackedCapes.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-3">
                        其他能力 ({unpackedCapes.length})
                      </h3>
                      <CapeConfigGrid
                        capes={unpackedCapes.filter(
                          (cape) =>
                            cape.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            cape.id.toLowerCase().includes(searchQuery.toLowerCase())
                        )}
                        enabledCapes={enabledCapes}
                        onToggle={handleToggleCape}
                        columns={2}
                      />
                    </div>
                  )}
                </div>
              ) : (
                <CapeConfigGrid
                  capes={filteredCapes}
                  enabledCapes={enabledCapes}
                  onToggle={handleToggleCape}
                  columns={2}
                />
              )}
            </motion.div>
          ) : (
            <motion.div
              key="chat"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="max-w-3xl mx-auto px-4 py-6"
            >
              {!hasMessages ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center py-12"
                >
                  <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <Sparkles className="w-8 h-8 text-blue-600" />
                  </div>
                  <h1 className="text-2xl font-semibold text-gray-900 mb-2">
                    CAPE Agent
                  </h1>
                  <p className="text-gray-500 mb-6 max-w-md mx-auto">
                    你好！我是 CAPE Agent。描述你想做什么，我会自动调用合适的能力来帮你完成。
                  </p>

                  {/* Current model */}
                  <div className="text-xs text-gray-400 mb-3">
                    当前模型: {selectedModel}
                  </div>

                  {/* Enabled capabilities */}
                  <div className="mb-6">
                    <div className="text-xs text-gray-400 mb-3">
                      当前已启用 {enabledCount} 个能力
                    </div>
                    <div className="flex justify-center">
                      <CapeCompactList
                        capes={capes}
                        enabledCapes={enabledCapes}
                      />
                    </div>
                  </div>

                  <button
                    onClick={() => setViewMode("capabilities")}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    配置能力 →
                  </button>

                  {/* Example prompts */}
                  <div className="mt-8 grid grid-cols-2 gap-2 max-w-lg mx-auto">
                    {[
                      "帮我审查这段代码",
                      "分析这段 Python 代码",
                      "处理这个 JSON 数据",
                      "总结一下这篇文章",
                    ].map((prompt) => (
                      <button
                        key={prompt}
                        onClick={() => handleSend(prompt)}
                        className="px-3 py-2 text-sm text-gray-600 bg-white border border-gray-200 rounded-lg hover:border-gray-300 hover:bg-gray-50 transition-colors text-left"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </motion.div>
              ) : (
                <>
                  {displayMessages.map((message, index) => {
                    // Skip rendering empty streaming assistant messages
                    // TypingIndicator will handle this state to avoid duplicate avatars
                    const isLastMessage = index === displayMessages.length - 1;
                    const isEmptyStreamingAssistant =
                      message.role === "assistant" &&
                      message.status === "streaming" &&
                      !message.content.trim() &&
                      !message.execution;

                    if (isLastMessage && isEmptyStreamingAssistant) {
                      return null;
                    }

                    return <MessageItem key={message.id} message={message} />;
                  })}
                  {/* Show typing indicator only when streaming and last message has no content/execution yet */}
                  {isStreaming && (() => {
                    const lastMsg = displayMessages[displayMessages.length - 1];
                    // Show typing when: streaming assistant with no content and no execution started
                    const isWaitingForResponse =
                      lastMsg?.role === "assistant" &&
                      !lastMsg.content.trim() &&
                      !lastMsg.execution;

                    if (!isWaitingForResponse) {
                      return null;
                    }

                    // Show cape name if matched, otherwise show generic typing
                    if (currentCape) {
                      return <TypingIndicator capeName={currentCape.name} />;
                    }
                    return <TypingIndicator />;
                  })()}
                  <div ref={messagesEndRef} />
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input */}
      {viewMode === "chat" && (
        <ChatInput
          onSend={handleSend}
          isStreaming={isStreaming}
          placeholder="描述你想做什么..."
        />
      )}
    </div>
  );
}
