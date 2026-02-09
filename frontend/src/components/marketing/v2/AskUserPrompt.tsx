"use client";

/**
 * AskUserPrompt Component
 *
 * Renders interactive choice cards when the agent needs user clarification.
 * - All questions are optional
 * - Single-select: radio toggle (click again to deselect)
 * - Multi-select: checkbox toggle
 * - Every question has a system-appended "Other" free-text option
 * - Submit + Skip buttons at the bottom (no instant send)
 */

import { useState, useCallback } from "react";
import { HelpCircle, Check, Send, SkipForward, PenLine } from "lucide-react";
import type { AskUserQuestionItem } from "@/lib/marketing/types";

const OTHER_KEY = "__other__";

interface AskUserPromptProps {
  questions: AskUserQuestionItem[];
  answered: boolean;
  onRespond: (response: string) => void;
}

export function AskUserPrompt({
  questions,
  answered,
  onRespond,
}: AskUserPromptProps) {
  const [selections, setSelections] = useState<Record<number, Set<string>>>(
    {}
  );
  const [otherTexts, setOtherTexts] = useState<Record<number, string>>({});

  const handleOptionClick = useCallback(
    (questionIdx: number, label: string, multiSelect: boolean) => {
      if (answered) return;

      setSelections((prev) => {
        const current = new Set(prev[questionIdx] || []);

        if (multiSelect) {
          if (current.has(label)) {
            current.delete(label);
          } else {
            current.add(label);
          }
        } else {
          // Single-select: toggle (click again to deselect)
          if (current.has(label)) {
            current.clear();
          } else {
            current.clear();
            current.add(label);
          }
        }

        return { ...prev, [questionIdx]: new Set(current) };
      });
    },
    [answered]
  );

  // Build response text from current selections
  const buildResponseText = useCallback((): string | null => {
    const parts: string[] = [];

    questions.forEach((q, idx) => {
      const sel = selections[idx];
      if (!sel || sel.size === 0) return;

      const labels = Array.from(sel)
        .map((l) =>
          l === OTHER_KEY ? (otherTexts[idx] || "").trim() : l
        )
        .filter(Boolean);

      if (labels.length === 0) return;

      const answer = labels.join(", ");
      parts.push(questions.length === 1 ? answer : `${q.header}: ${answer}`);
    });

    return parts.length > 0 ? parts.join(" / ") : null;
  }, [questions, selections, otherTexts]);

  const handleSubmit = useCallback(() => {
    if (answered) return;
    const text = buildResponseText();
    if (text) onRespond(text);
  }, [answered, buildResponseText, onRespond]);

  const handleSkip = useCallback(() => {
    if (answered) return;
    onRespond("確認をスキップします。あなたの判断で進めてください。");
  }, [answered, onRespond]);

  // Check if submit is possible
  const hasValidSelection = (() => {
    for (const [idx, sel] of Object.entries(selections)) {
      if (!sel || sel.size === 0) continue;
      for (const item of sel) {
        if (item !== OTHER_KEY) return true;
        if ((otherTexts[Number(idx)] || "").trim()) return true;
      }
    }
    return false;
  })();

  return (
    <div className="my-3 space-y-4">
      {questions.map((q, qIdx) => {
        const isMulti = q.multiSelect ?? false;
        const currentSel = selections[qIdx] || new Set<string>();
        const isOtherSelected = currentSel.has(OTHER_KEY);

        return (
          <div key={qIdx} className="space-y-2">
            {/* Header chip + question */}
            <div className="flex items-start gap-2">
              <HelpCircle className="w-4 h-4 shrink-0 mt-0.5 text-[#6366f1]" />
              <div className="space-y-1">
                <span className="inline-block text-[10px] font-semibold text-[#6366f1] bg-[#eef2ff] px-2 py-0.5 rounded-full">
                  {q.header}
                </span>
                <p className="text-[13px] sm:text-sm text-[#374151] font-medium">
                  {q.question}
                </p>
                {isMulti && (
                  <p className="text-[11px] text-[#9ca3af]">
                    複数選択可
                  </p>
                )}
              </div>
            </div>

            {/* Option cards */}
            <div className="grid gap-1.5 ml-6">
              {q.options.map((opt) => {
                const isSelected = currentSel.has(opt.label);

                return (
                  <button
                    key={opt.label}
                    type="button"
                    disabled={answered}
                    onClick={() =>
                      handleOptionClick(qIdx, opt.label, isMulti)
                    }
                    className={`
                      group/opt flex items-center gap-2.5 w-full text-left rounded-lg px-3 py-2.5
                      border transition-all duration-150
                      ${
                        answered
                          ? "opacity-60 cursor-default border-[#e5e7eb] bg-[#f8f9fb]"
                          : isSelected
                            ? "border-[#6366f1] bg-[#eef2ff] shadow-sm"
                            : "border-[#e5e7eb] bg-white hover:border-[#a5b4fc] hover:bg-[#f5f3ff] cursor-pointer"
                      }
                    `}
                  >
                    {/* Radio / Checkbox indicator */}
                    <div
                      className={`
                        w-4 h-4 shrink-0 flex items-center justify-center
                        ${isMulti ? "rounded" : "rounded-full"}
                        border transition-colors
                        ${
                          isSelected
                            ? "border-[#6366f1] bg-[#6366f1]"
                            : "border-[#d1d5db] bg-white group-hover/opt:border-[#a5b4fc]"
                        }
                      `}
                    >
                      {isSelected && (
                        <Check className="w-2.5 h-2.5 text-white" />
                      )}
                    </div>

                    {/* Label + description */}
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] sm:text-sm font-medium text-[#1a1a2e]">
                        {opt.label}
                      </div>
                      {opt.description && (
                        <div className="text-[11px] sm:text-xs text-[#6b7280] mt-0.5 leading-relaxed">
                          {opt.description}
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}

              {/* "Other" option - always appended by system */}
              <button
                type="button"
                disabled={answered}
                onClick={() =>
                  handleOptionClick(qIdx, OTHER_KEY, isMulti)
                }
                className={`
                  group/opt flex items-center gap-2.5 w-full text-left rounded-lg px-3 py-2.5
                  border transition-all duration-150
                  ${
                    answered
                      ? "opacity-60 cursor-default border-[#e5e7eb] bg-[#f8f9fb]"
                      : isOtherSelected
                        ? "border-[#6366f1] bg-[#eef2ff] shadow-sm"
                        : "border-[#e5e7eb] bg-white hover:border-[#a5b4fc] hover:bg-[#f5f3ff] cursor-pointer"
                  }
                `}
              >
                <div
                  className={`
                    w-4 h-4 shrink-0 flex items-center justify-center
                    ${isMulti ? "rounded" : "rounded-full"}
                    border transition-colors
                    ${
                      isOtherSelected
                        ? "border-[#6366f1] bg-[#6366f1]"
                        : "border-[#d1d5db] bg-white group-hover/opt:border-[#a5b4fc]"
                    }
                  `}
                >
                  {isOtherSelected && (
                    <Check className="w-2.5 h-2.5 text-white" />
                  )}
                </div>
                <div className="flex-1 min-w-0 flex items-center gap-1.5">
                  <PenLine className="w-3.5 h-3.5 text-[#9ca3af]" />
                  <span className="text-[13px] sm:text-sm font-medium text-[#6b7280]">
                    その他（自由入力）
                  </span>
                </div>
              </button>

              {/* Free text input for "Other" */}
              {isOtherSelected && !answered && (
                <input
                  type="text"
                  value={otherTexts[qIdx] || ""}
                  onChange={(e) =>
                    setOtherTexts((prev) => ({
                      ...prev,
                      [qIdx]: e.target.value,
                    }))
                  }
                  placeholder="回答を入力してください..."
                  className="w-full rounded-lg border border-[#d1d5db] px-3 py-2 text-[13px] sm:text-sm
                    text-[#1a1a2e] placeholder:text-[#9ca3af]
                    focus:outline-none focus:border-[#6366f1] focus:ring-1 focus:ring-[#6366f1]/30
                    transition-colors"
                  autoFocus
                />
              )}
            </div>
          </div>
        );
      })}

      {/* Action buttons at the bottom */}
      {!answered ? (
        <div className="ml-6 flex items-center gap-2 pt-1">
          <button
            type="button"
            disabled={!hasValidSelection}
            onClick={handleSubmit}
            className={`
              inline-flex items-center gap-1.5 rounded-lg px-5 py-2.5 sm:px-4 sm:py-2 text-[13px] font-medium
              transition-all duration-150
              ${
                hasValidSelection
                  ? "bg-[#6366f1] text-white hover:bg-[#4f46e5] shadow-sm cursor-pointer"
                  : "bg-[#e5e7eb] text-[#9ca3af] cursor-not-allowed"
              }
            `}
          >
            <Send className="w-3.5 h-3.5" />
            送信
          </button>
          <button
            type="button"
            onClick={handleSkip}
            className="inline-flex items-center gap-1.5 rounded-lg px-5 py-2.5 sm:px-4 sm:py-2 text-[13px] font-medium
              text-[#6b7280] border border-[#e5e7eb] bg-white hover:bg-[#f9fafb] hover:border-[#d1d5db]
              transition-all duration-150 cursor-pointer"
          >
            <SkipForward className="w-3.5 h-3.5" />
            スキップ
          </button>
        </div>
      ) : (
        <div className="ml-6 text-[11px] text-[#10b981] flex items-center gap-1">
          <Check className="w-3 h-3" />
          回答済み
        </div>
      )}
    </div>
  );
}
