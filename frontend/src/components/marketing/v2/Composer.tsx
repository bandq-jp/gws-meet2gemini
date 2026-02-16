"use client";

/**
 * Composer Component
 *
 * ChatGPT-style message input with auto-resize, send/stop, and file upload.
 * Supports multimodal input: text + images/PDF/Office files.
 */

import { useState, useRef, useCallback } from "react";
import {
  Send,
  Square,
  Paperclip,
  X,
  FileText,
  Image as ImageIcon,
  FileSpreadsheet,
} from "lucide-react";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB per file
const MAX_TOTAL_SIZE = 20 * 1024 * 1024; // 20MB total
const MAX_FILE_COUNT = 5;
const ACCEPTED_TYPES =
  "image/*,application/pdf,.csv,.txt,.md,.xlsx,.docx,.pptx";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function getFileIcon(type: string) {
  if (type.startsWith("image/")) return ImageIcon;
  if (type === "application/pdf") return FileText;
  if (
    type.includes("spreadsheet") ||
    type === "text/csv"
  )
    return FileSpreadsheet;
  return FileText;
}

export interface ComposerProps {
  onSend: (content: string, files?: File[]) => Promise<void>;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function Composer({
  onSend,
  onStop,
  isStreaming = false,
  disabled = false,
  placeholder = "マーケティングデータについて質問...",
}: ComposerProps) {
  const [input, setInput] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(async () => {
    const trimmed = input.trim();
    if ((!trimmed && files.length === 0) || isStreaming || disabled) return;

    const filesToSend = files.length > 0 ? [...files] : undefined;
    setInput("");
    setFiles([]);
    setFileError(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    await onSend(trimmed || "添付ファイルを分析してください", filesToSend);
  }, [input, files, isStreaming, disabled, onSend]);

  // Enter = 改行（デフォルト動作）、送信はボタンのみ
  const handleKeyDown = useCallback(
    (_e: React.KeyboardEvent) => {
      // no-op: Enter で改行、送信はボタンクリックのみ
    },
    []
  );

  const handleInput = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInput(e.target.value);
      const el = e.target;
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 150) + "px";
    },
    []
  );

  const handleStopClick = useCallback(() => {
    onStop?.();
  }, [onStop]);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFiles = Array.from(e.target.files || []);
      if (!selectedFiles.length) return;

      // Reset input so same file can be selected again
      e.target.value = "";

      setFileError(null);

      // Validate count
      const newTotal = files.length + selectedFiles.length;
      if (newTotal > MAX_FILE_COUNT) {
        setFileError(`ファイルは最大${MAX_FILE_COUNT}個まで`);
        return;
      }

      // Validate sizes
      let totalSize = files.reduce((sum, f) => sum + f.size, 0);
      for (const file of selectedFiles) {
        if (file.size > MAX_FILE_SIZE) {
          setFileError(`${file.name} が10MBを超えています`);
          return;
        }
        totalSize += file.size;
      }
      if (totalSize > MAX_TOTAL_SIZE) {
        setFileError("合計サイズが20MBを超えています");
        return;
      }

      setFiles((prev) => [...prev, ...selectedFiles]);
    },
    [files]
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setFileError(null);
  }, []);

  const hasContent = input.trim() || files.length > 0;

  return (
    <div className="shrink-0 px-3 sm:px-6 pb-2 sm:pb-4 pt-2 bg-background safe-bottom">
      <div className="max-w-3xl mx-auto">
        {/* File preview chips */}
        {files.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2 px-1">
            {files.map((file, idx) => {
              const FileIcon = getFileIcon(file.type);
              const isImage = file.type.startsWith("image/");
              return (
                <div
                  key={`${file.name}-${idx}`}
                  className="group flex items-center gap-1.5 bg-[#f8f9fb] border border-[#e5e7eb] rounded-lg px-2 py-1 text-[11px] text-[#374151] max-w-[200px]"
                >
                  {isImage ? (
                    <img
                      src={URL.createObjectURL(file)}
                      alt={file.name}
                      className="w-5 h-5 rounded object-cover shrink-0"
                    />
                  ) : (
                    <FileIcon className="w-3.5 h-3.5 text-[#9ca3af] shrink-0" />
                  )}
                  <span className="truncate">{file.name}</span>
                  <span className="text-[9px] text-[#9ca3af] shrink-0">
                    {formatFileSize(file.size)}
                  </span>
                  <button
                    onClick={() => removeFile(idx)}
                    className="shrink-0 p-0.5 rounded hover:bg-[#e5e7eb] transition-colors opacity-60 group-hover:opacity-100"
                    aria-label={`${file.name}を削除`}
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* File error */}
        {fileError && (
          <div className="text-[11px] text-red-500 mb-1.5 px-1">
            {fileError}
          </div>
        )}

        {/* Input area */}
        <div className="flex items-end gap-0 bg-white border border-[#d1d5db] rounded-2xl shadow-sm focus-within:border-[#9ca3af] focus-within:shadow-md transition-all">
          {/* File upload button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isStreaming || disabled || files.length >= MAX_FILE_COUNT}
            className="shrink-0 w-10 h-10 sm:w-9 sm:h-9 m-1 sm:m-1.5 rounded-xl flex items-center justify-center hover:bg-[#f0f1f5] disabled:opacity-20 disabled:cursor-not-allowed transition-colors cursor-pointer"
            aria-label="ファイルを添付"
          >
            <Paperclip className="w-4 h-4 text-[#9ca3af]" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ACCEPTED_TYPES}
            onChange={handleFileSelect}
            className="hidden"
          />

          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="flex-1 min-h-[44px] max-h-[150px] resize-none bg-transparent px-2 py-3 text-[14px] sm:text-sm leading-relaxed placeholder:text-[#9ca3af] text-[#1a1a2e] outline-none disabled:opacity-40 disabled:cursor-not-allowed"
          />
          {isStreaming ? (
            <button
              onClick={handleStopClick}
              className="shrink-0 w-10 h-10 sm:w-9 sm:h-9 m-1 sm:m-1.5 rounded-xl flex items-center justify-center bg-[#f0f1f5] hover:bg-[#e5e7eb] transition-colors cursor-pointer"
              aria-label="停止"
            >
              <Square className="w-4 h-4 text-[#e94560]" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!hasContent || disabled}
              className="shrink-0 w-10 h-10 sm:w-9 sm:h-9 m-1 sm:m-1.5 rounded-xl flex items-center justify-center bg-[#1a1a2e] hover:bg-[#2a2a4e] disabled:opacity-20 disabled:cursor-not-allowed transition-colors cursor-pointer"
              aria-label="送信"
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          )}
        </div>
        <p className="text-center text-[10px] sm:text-[11px] text-rose-500/80 font-medium mt-2">
          Enter で改行 / 送信はボタンのみ / ファイル添付可
        </p>
      </div>
    </div>
  );
}
