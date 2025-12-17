"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Paperclip, X, Sparkles, StopCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  onStop,
  disabled,
  isStreaming,
  placeholder,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [attachments, setAttachments] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const newHeight = Math.min(textareaRef.current.scrollHeight, 180);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [value]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = () => {
    if (!value.trim() || disabled || isStreaming) return;
    onSend(value.trim());
    setValue("");
    setAttachments([]);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleAttach = () => {
    // Placeholder for file attachment
    console.log("Attach file");
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  const hasContent = value.trim().length > 0;
  const showStopButton = isStreaming && onStop;

  return (
    <div className="sticky bottom-0 pt-4 pb-4 px-4">
      <motion.div
        initial={false}
        animate={{
          boxShadow: isFocused
            ? "0 0 0 2px rgba(59, 130, 246, 0.2), 0 4px 20px rgba(0, 0, 0, 0.08)"
            : "0 2px 12px rgba(0, 0, 0, 0.06)",
        }}
        className="max-w-3xl mx-auto rounded-2xl"
      >
        <div
          className={cn(
            "relative bg-white rounded-2xl border transition-colors duration-200",
            isFocused ? "border-blue-400" : "border-gray-200"
          )}
        >
          {/* Attachments preview */}
          <AnimatePresence>
            {attachments.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="px-3 pt-3 pb-1 border-b border-gray-100"
              >
                <div className="flex flex-wrap gap-2">
                  {attachments.map((name, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-lg text-sm text-gray-600"
                    >
                      <Paperclip className="w-3.5 h-3.5" />
                      <span className="max-w-[120px] truncate">{name}</span>
                      <button
                        onClick={() => removeAttachment(i)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Input area */}
          <div className="flex items-end gap-1 p-2">
            {/* Attach button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleAttach}
              disabled={disabled || isStreaming}
              className={cn(
                "flex-shrink-0 p-2.5 rounded-xl transition-colors",
                "text-gray-400 hover:text-gray-600 hover:bg-gray-100",
                "disabled:opacity-40 disabled:cursor-not-allowed",
                "focus:outline-none focus:ring-0"
              )}
              title="附加文件"
            >
              <Paperclip className="w-5 h-5" />
            </motion.button>

            {/* Textarea */}
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                placeholder={placeholder || "描述你想做什么，我来帮你完成..."}
                disabled={disabled || isStreaming}
                rows={1}
                className={cn(
                  "w-full resize-none bg-transparent text-[15px] leading-relaxed",
                  "placeholder:text-gray-400 focus:outline-none",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  "py-2.5 px-1"
                )}
              />
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-1">
              {/* Stop button - shown when streaming */}
              <AnimatePresence mode="wait">
                {showStopButton ? (
                  <motion.button
                    key="stop"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={onStop}
                    className="flex-shrink-0 p-2.5 rounded-xl bg-red-50 text-red-500 hover:bg-red-100 transition-colors focus:outline-none focus:ring-0"
                    title="停止生成"
                  >
                    <StopCircle className="w-5 h-5" />
                  </motion.button>
                ) : (
                  <motion.button
                    key="send"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    whileHover={{ scale: hasContent && !disabled ? 1.05 : 1 }}
                    whileTap={{ scale: hasContent && !disabled ? 0.95 : 1 }}
                    onClick={handleSubmit}
                    disabled={!hasContent || disabled}
                    className={cn(
                      "flex-shrink-0 p-2.5 rounded-xl transition-all duration-200 focus:outline-none focus:ring-0",
                      hasContent && !disabled
                        ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm shadow-blue-200"
                        : "bg-gray-100 text-gray-400 cursor-not-allowed"
                    )}
                    title="发送消息"
                  >
                    <Send className="w-5 h-5" />
                  </motion.button>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Bottom hint bar */}
          <div className="px-4 pb-2.5 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Agent 将自动调用合适的能力</span>
            </div>
            <div className="text-xs text-gray-400">
              <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px] font-medium">
                Enter
              </kbd>
              <span className="mx-1">发送</span>
              <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-[10px] font-medium">
                Shift+Enter
              </kbd>
              <span className="ml-1">换行</span>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
