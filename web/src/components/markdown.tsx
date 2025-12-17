"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Check, Copy } from "lucide-react";
import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";

interface MarkdownProps {
  content: string;
  className?: string;
}

export function Markdown({ content, className }: MarkdownProps) {
  return (
    <div className={cn("markdown-body", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // Code blocks
          pre({ children }) {
            // Extract text content from code element for copy button
            const getCodeText = (): string => {
              if (!children) return "";
              const child = children as React.ReactElement<{ children?: React.ReactNode }>;
              if (child?.props?.children) {
                const content = child.props.children;
                if (typeof content === "string") return content;
                if (Array.isArray(content)) {
                  return content
                    .map((c) => (typeof c === "string" ? c : ""))
                    .join("");
                }
              }
              return "";
            };

            return (
              <div className="relative group my-3">
                <pre className="overflow-x-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100">
                  {children}
                </pre>
                <CopyButton getText={getCodeText} />
              </div>
            );
          },
          // Inline code
          code({ className, children, ...props }) {
            const isInline = !className;
            if (isInline) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded bg-gray-200 text-gray-800 text-sm font-mono"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <code className={cn(className, "text-sm")} {...props}>
                {children}
              </code>
            );
          },
          // Paragraphs
          p({ children }) {
            return <p className="my-2 leading-relaxed">{children}</p>;
          },
          // Headings
          h1({ children }) {
            return (
              <h1 className="text-xl font-bold mt-4 mb-2 text-gray-900">
                {children}
              </h1>
            );
          },
          h2({ children }) {
            return (
              <h2 className="text-lg font-semibold mt-3 mb-2 text-gray-900">
                {children}
              </h2>
            );
          },
          h3({ children }) {
            return (
              <h3 className="text-base font-semibold mt-3 mb-1 text-gray-900">
                {children}
              </h3>
            );
          },
          // Lists
          ul({ children }) {
            return (
              <ul className="my-2 ml-4 list-disc space-y-1">{children}</ul>
            );
          },
          ol({ children }) {
            return (
              <ol className="my-2 ml-4 list-decimal space-y-1">{children}</ol>
            );
          },
          li({ children }) {
            return <li className="leading-relaxed">{children}</li>;
          },
          // Blockquotes
          blockquote({ children }) {
            return (
              <blockquote className="my-3 pl-4 border-l-4 border-blue-300 bg-blue-50 py-2 pr-4 rounded-r text-gray-700 italic">
                {children}
              </blockquote>
            );
          },
          // Links
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-700 underline underline-offset-2"
              >
                {children}
              </a>
            );
          },
          // Tables
          table({ children }) {
            return (
              <div className="my-3 overflow-x-auto">
                <table className="min-w-full border border-gray-200 rounded-lg overflow-hidden">
                  {children}
                </table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-gray-100">{children}</thead>;
          },
          th({ children }) {
            return (
              <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700 border-b border-gray-200">
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="px-4 py-2 text-sm text-gray-600 border-b border-gray-100">
                {children}
              </td>
            );
          },
          // Horizontal rule
          hr() {
            return <hr className="my-4 border-gray-200" />;
          },
          // Strong/Bold
          strong({ children }) {
            return (
              <strong className="font-semibold text-gray-900">{children}</strong>
            );
          },
          // Emphasis/Italic
          em({ children }) {
            return <em className="italic">{children}</em>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

// Copy button for code blocks
function CopyButton({ getText }: { getText: () => string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    const text = getText();
    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.error("Failed to copy");
    }
  }, [getText]);

  return (
    <button
      onClick={handleCopy}
      className={cn(
        "absolute top-2 right-2 p-1.5 rounded-md transition-all",
        "opacity-0 group-hover:opacity-100",
        "bg-gray-700 hover:bg-gray-600 text-gray-300"
      )}
      title="复制代码"
    >
      {copied ? (
        <Check className="w-4 h-4 text-green-400" />
      ) : (
        <Copy className="w-4 h-4" />
      )}
    </button>
  );
}
