"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  FileSpreadsheet,
  FileImage,
  File,
  X,
  Upload,
  Loader2,
  Download,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { FileInfo } from "@/data/types";

// ============================================================
// File Icon Component
// ============================================================

function getFileIcon(contentType: string, className?: string) {
  if (contentType.includes("spreadsheet") || contentType.includes("excel")) {
    return <FileSpreadsheet className={cn("text-green-500", className)} />;
  }
  if (contentType.includes("image")) {
    return <FileImage className={cn("text-purple-500", className)} />;
  }
  if (
    contentType.includes("pdf") ||
    contentType.includes("document") ||
    contentType.includes("word")
  ) {
    return <FileText className={cn("text-blue-500", className)} />;
  }
  return <File className={cn("text-gray-500", className)} />;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ============================================================
// File Item Component
// ============================================================

interface FileItemProps {
  file: FileInfo;
  onRemove?: () => void;
  onDownload?: () => void;
  showStatus?: boolean;
  compact?: boolean;
}

export function FileItem({
  file,
  onRemove,
  onDownload,
  showStatus = false,
  compact = false,
}: FileItemProps) {
  const statusColors: Record<string, string> = {
    uploaded: "text-blue-500",
    processing: "text-yellow-500",
    completed: "text-green-500",
    expired: "text-gray-400",
    deleted: "text-red-500",
  };

  const statusIcons: Record<string, React.ReactNode> = {
    uploaded: null,
    processing: <Loader2 className="w-3 h-3 animate-spin" />,
    completed: <CheckCircle className="w-3 h-3" />,
    expired: <AlertCircle className="w-3 h-3" />,
  };

  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-lg text-sm text-gray-600"
      >
        {getFileIcon(file.content_type, "w-3.5 h-3.5")}
        <span className="max-w-[120px] truncate">{file.original_name}</span>
        {showStatus && statusIcons[file.status] && (
          <span className={statusColors[file.status]}>
            {statusIcons[file.status]}
          </span>
        )}
        {onRemove && (
          <button
            onClick={onRemove}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200"
    >
      {getFileIcon(file.content_type, "w-8 h-8")}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {file.original_name}
        </p>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>{formatFileSize(file.size_bytes)}</span>
          {showStatus && (
            <span className={cn("flex items-center gap-1", statusColors[file.status])}>
              {statusIcons[file.status]}
              {file.status}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1">
        {onDownload && (
          <button
            onClick={onDownload}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
            title="下载"
          >
            <Download className="w-4 h-4" />
          </button>
        )}
        {onRemove && (
          <button
            onClick={onRemove}
            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            title="删除"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </motion.div>
  );
}

// ============================================================
// Pending File Item (for files being uploaded)
// ============================================================

interface PendingFile {
  id: string;
  file: File;
  progress: number;
  error?: string;
}

interface PendingFileItemProps {
  pending: PendingFile;
  onRemove: () => void;
}

export function PendingFileItem({ pending, onRemove }: PendingFileItemProps) {
  const isUploading = pending.progress < 100 && !pending.error;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className={cn(
        "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm",
        pending.error ? "bg-red-50 text-red-600" : "bg-blue-50 text-blue-600"
      )}
    >
      {isUploading ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
      ) : pending.error ? (
        <AlertCircle className="w-3.5 h-3.5" />
      ) : (
        <CheckCircle className="w-3.5 h-3.5 text-green-500" />
      )}
      <span className="max-w-[120px] truncate">{pending.file.name}</span>
      {isUploading && (
        <span className="text-xs">{Math.round(pending.progress)}%</span>
      )}
      <button onClick={onRemove} className="hover:opacity-70">
        <X className="w-3.5 h-3.5" />
      </button>
    </motion.div>
  );
}

// ============================================================
// File Drop Zone
// ============================================================

interface FileDropZoneProps {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  children?: React.ReactNode;
}

export function FileDropZone({
  onFilesSelected,
  accept = ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,.csv,.json,.png,.jpg,.jpeg",
  multiple = true,
  disabled = false,
  children,
}: FileDropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragging(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (disabled) return;

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        onFilesSelected(multiple ? files : [files[0]]);
      }
    },
    [disabled, multiple, onFilesSelected]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length > 0) {
        onFilesSelected(files);
      }
      // Reset input
      e.target.value = "";
    },
    [onFilesSelected]
  );

  const handleClick = useCallback(() => {
    if (!disabled) {
      inputRef.current?.click();
    }
  }, [disabled]);

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      className={cn(
        "relative cursor-pointer transition-all duration-200",
        isDragging && "ring-2 ring-blue-400 ring-offset-2",
        disabled && "cursor-not-allowed opacity-50"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleFileChange}
        disabled={disabled}
        className="hidden"
      />
      {children || (
        <div
          className={cn(
            "flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl",
            isDragging
              ? "border-blue-400 bg-blue-50"
              : "border-gray-300 hover:border-gray-400 bg-gray-50"
          )}
        >
          <Upload className="w-8 h-8 text-gray-400 mb-2" />
          <p className="text-sm text-gray-600 mb-1">
            拖放文件到这里，或点击选择
          </p>
          <p className="text-xs text-gray-400">
            支持 PDF, Word, Excel, PPT, 图片等格式
          </p>
        </div>
      )}
    </div>
  );
}

// ============================================================
// File List Component
// ============================================================

interface FileListProps {
  files: FileInfo[];
  onRemove?: (fileId: string) => void;
  onDownload?: (file: FileInfo) => void;
  showStatus?: boolean;
  emptyMessage?: string;
}

export function FileList({
  files,
  onRemove,
  onDownload,
  showStatus = true,
  emptyMessage = "暂无文件",
}: FileListProps) {
  if (files.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <AnimatePresence>
        {files.map((file) => (
          <FileItem
            key={file.file_id}
            file={file}
            onRemove={onRemove ? () => onRemove(file.file_id) : undefined}
            onDownload={onDownload ? () => onDownload(file) : undefined}
            showStatus={showStatus}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
