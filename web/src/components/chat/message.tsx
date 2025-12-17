"use client";

import { motion } from "framer-motion";
import { User, Bot, CheckCircle, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Markdown } from "@/components/markdown";

export type MessageRole = "user" | "assistant";
export type MessageStatus = "pending" | "streaming" | "complete" | "error";

export interface CapeExecution {
  cape_id: string;
  cape_name: string;
  status: "running" | "completed" | "failed";
  duration_ms?: number;
  error?: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  status?: MessageStatus;
  execution?: CapeExecution;
}

interface MessageItemProps {
  message: Message;
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === "user";
  const hasContent = message.content.trim().length > 0;
  const isStreaming = message.status === "streaming";
  const isRunningCape = message.execution?.status === "running";

  // For assistant messages: show indicator when running cape with no content yet
  const showCapeIndicatorOnly = !isUser && isRunningCape && !hasContent;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("flex gap-3 py-3", isUser ? "flex-row-reverse" : "")}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
          isUser ? "bg-gray-900" : "bg-blue-600"
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Content */}
      <div className={cn("flex-1 max-w-[85%]", isUser ? "text-right" : "")}>
        {/* Cape Running Indicator - shown when cape is running but no content yet */}
        {showCapeIndicatorOnly && (
          <CapeRunningIndicator capeName={message.execution!.cape_name} />
        )}

        {/* Message Bubble - only show when we have content or it's a user message */}
        {(hasContent || isUser) && (
          <div
            className={cn(
              "inline-block rounded-2xl text-[15px] leading-relaxed",
              isUser
                ? "bg-gray-900 text-white rounded-br-md px-4 py-2.5"
                : "bg-gray-100 text-gray-900 rounded-bl-md px-4 py-3"
            )}
          >
            {/* Message content - Markdown for assistant, plain text for user */}
            {isUser ? (
              <div className="whitespace-pre-wrap">{message.content}</div>
            ) : (
              <Markdown
                content={message.content}
                className="text-gray-900 [&>*:first-child]:mt-0 [&>*:last-child]:mb-0"
              />
            )}

            {/* Streaming indicator - show when streaming with content */}
            {isStreaming && hasContent && (
              <span className="inline-flex ml-1">
                <span className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" />
              </span>
            )}
          </div>
        )}

        {/* Execution Summary - shown below message when completed */}
        {message.execution?.status === "completed" && hasContent && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-1.5 flex items-center gap-2 text-xs text-gray-400"
          >
            <CheckCircle className="w-3 h-3 text-green-500" />
            <span>通过 {message.execution.cape_name}</span>
            {typeof message.execution.duration_ms === "number" && message.execution.duration_ms > 0 && (
              <>
                <span>·</span>
                <span>{message.execution.duration_ms}ms</span>
              </>
            )}
          </motion.div>
        )}

        {/* Error indicator */}
        {message.execution?.status === "failed" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-1.5 flex items-center gap-2 text-xs text-red-500"
          >
            <AlertCircle className="w-3 h-3" />
            <span>{message.execution.error || "执行失败"}</span>
          </motion.div>
        )}

        {/* Error message status */}
        {message.status === "error" && !message.execution && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-1.5 flex items-center gap-2 text-xs text-red-500"
          >
            <AlertCircle className="w-3 h-3" />
            <span>发送失败</span>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

// Simple inline indicator showing which cape is being used
function CapeRunningIndicator({ capeName }: { capeName: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="inline-flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-100 rounded-xl text-sm text-blue-600"
    >
      <Loader2 className="w-4 h-4 animate-spin" />
      <span>正在调用</span>
      <span className="font-medium">{capeName}</span>
    </motion.div>
  );
}

interface TypingIndicatorProps {
  capeName?: string;
}

export function TypingIndicator({ capeName }: TypingIndicatorProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex gap-3 py-3"
    >
      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="flex flex-col items-start gap-2">
        {capeName && (
          <div className="inline-flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-100 rounded-xl text-sm text-blue-600">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>正在调用</span>
            <span className="font-medium">{capeName}</span>
          </div>
        )}
        {!capeName && (
          <div className="flex items-center gap-1 px-4 py-3 bg-gray-100 rounded-2xl rounded-bl-md">
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                className="w-2 h-2 bg-gray-400 rounded-full"
                animate={{ y: [0, -4, 0] }}
                transition={{
                  duration: 0.6,
                  repeat: Infinity,
                  delay: i * 0.15,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
