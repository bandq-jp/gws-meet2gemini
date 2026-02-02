"use client";

import { useState, useRef, useCallback } from "react";
import { Send, Square, ChevronDown } from "lucide-react";
import type { ModelAsset } from "@/lib/marketing-types";

interface Props {
  onSend: (message: string, modelAssetId: string) => void;
  isStreaming: boolean;
  onStop: () => void;
  disabled?: boolean;
  assets?: ModelAsset[];
  selectedAssetId?: string;
  onAssetChange?: (id: string) => void;
}

export function ChatInput({
  onSend,
  isStreaming,
  onStop,
  disabled,
  assets,
  selectedAssetId = "standard",
  onAssetChange,
}: Props) {
  const [input, setInput] = useState("");
  const [showAssets, setShowAssets] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const selectedAsset = assets?.find((a) => a.id === selectedAssetId);

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || disabled) return;
    onSend(trimmed, selectedAssetId);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [input, isStreaming, disabled, onSend, selectedAssetId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 150) + "px";
  };

  return (
    <div className="shrink-0 px-3 sm:px-6 pb-2 sm:pb-4 pt-2 bg-background safe-bottom">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-0 bg-white border border-[#d1d5db] rounded-2xl shadow-sm focus-within:border-[var(--brand-300)] focus-within:shadow-md transition-all">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="マーケティングについて質問..."
            disabled={disabled}
            rows={1}
            className="flex-1 min-h-[44px] max-h-[150px] resize-none bg-transparent px-4 py-3 text-[14px] sm:text-sm leading-relaxed placeholder:text-[#9ca3af] text-foreground outline-none disabled:opacity-40 disabled:cursor-not-allowed"
          />

          {/* Asset selector */}
          {assets && assets.length > 1 && (
            <div className="relative shrink-0">
              <button
                onClick={() => setShowAssets(!showAssets)}
                className="flex items-center gap-1 px-2 py-1.5 m-1 text-[11px] text-[#6b7280] hover:text-foreground bg-[#f0f1f5] hover:bg-[#e5e7eb] rounded-lg transition-colors cursor-pointer"
              >
                <span className="max-w-[80px] truncate">
                  {selectedAsset?.name || "Standard"}
                </span>
                <ChevronDown className="w-3 h-3" />
              </button>
              {showAssets && (
                <div className="absolute bottom-full right-0 mb-1 w-48 bg-white border border-[#e5e7eb] rounded-lg shadow-lg py-1 z-50">
                  {assets.map((asset) => (
                    <button
                      key={asset.id}
                      onClick={() => {
                        onAssetChange?.(asset.id);
                        setShowAssets(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs hover:bg-[#f0f1f5] transition-colors cursor-pointer ${
                        asset.id === selectedAssetId
                          ? "text-[var(--brand-400)] font-medium"
                          : "text-[#374151]"
                      }`}
                    >
                      <div className="font-medium">{asset.name}</div>
                      {asset.description && (
                        <div className="text-[10px] text-[#9ca3af] truncate">
                          {asset.description}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {isStreaming ? (
            <button
              onClick={onStop}
              className="shrink-0 w-9 h-9 m-1.5 rounded-xl flex items-center justify-center bg-[#f0f1f5] hover:bg-[#e5e7eb] transition-colors cursor-pointer"
              aria-label="停止"
            >
              <Square className="w-4 h-4 text-red-500" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || disabled}
              className="shrink-0 w-9 h-9 m-1.5 rounded-xl flex items-center justify-center bg-[var(--brand-400)] hover:bg-[#176d80] disabled:opacity-20 disabled:cursor-not-allowed transition-colors cursor-pointer"
              aria-label="送信"
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          )}
        </div>
        <p className="hidden sm:block text-center text-[11px] text-[#9ca3af] mt-2">
          Shift+Enter で改行 / Enter で送信
        </p>
      </div>
    </div>
  );
}
