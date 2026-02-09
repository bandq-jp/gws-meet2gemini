"use client";

/**
 * SuggestionCarousel - Sliding suggestion cards with arrow navigation & dot indicators.
 *
 * Shows all suggestions in pages of 6 (2-col grid), auto-rotates every 6s,
 * pauses on hover. Left/right chevron arrows + pill-shaped page dots.
 */

import {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from "react";
import { ArrowRight, ChevronLeft, ChevronRight, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type Suggestion = {
  icon: LucideIcon;
  tag: string;
  text: string;
};

interface SuggestionCarouselProps {
  suggestions: Suggestion[];
  onSend: (text: string) => void;
  /** Cards per page (default 6) */
  perPage?: number;
  /** Auto-rotate interval in ms (default 6000) */
  interval?: number;
}

export function SuggestionCarousel({
  suggestions,
  onSend,
  perPage = 6,
  interval = 6000,
}: SuggestionCarouselProps) {
  // --- pagination --------------------------------------------------------
  const pages = useMemo(() => {
    const result: Suggestion[][] = [];
    for (let i = 0; i < suggestions.length; i += perPage) {
      result.push(suggestions.slice(i, i + perPage));
    }
    return result;
  }, [suggestions, perPage]);

  const total = pages.length;
  const [active, setActive] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  // --- navigation --------------------------------------------------------
  const goTo = useCallback(
    (idx: number) => {
      setActive(((idx % total) + total) % total);
    },
    [total]
  );

  const prev = useCallback(() => goTo(active - 1), [active, goTo]);
  const next = useCallback(() => goTo(active + 1), [active, goTo]);

  // --- auto-rotate -------------------------------------------------------
  useEffect(() => {
    if (isPaused || total <= 1) return;
    const timer = setInterval(next, interval);
    return () => clearInterval(timer);
  }, [isPaused, next, interval, total]);

  // --- swipe support (touch) ---------------------------------------------
  const touchStartX = useRef(0);
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  }, []);
  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      const diff = touchStartX.current - e.changedTouches[0].clientX;
      if (Math.abs(diff) > 50) {
        diff > 0 ? next() : prev();
      }
    },
    [next, prev]
  );

  if (total === 0) return null;

  return (
    <div
      className="w-full max-w-2xl"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Slide area with side arrows */}
      <div className="relative group/carousel">
        {/* Left arrow (hidden on mobile — swipe instead) */}
        {total > 1 && (
          <button
            onClick={prev}
            aria-label="Previous"
            className="hidden sm:flex absolute -left-12 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full bg-background border border-[#e8eaed] shadow-sm items-center justify-center text-[#9ca3af] hover:text-[#1e8aa0] hover:border-[#1e8aa0]/30 hover:shadow-md transition-all duration-200 cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}

        {/* Right arrow (hidden on mobile — swipe instead) */}
        {total > 1 && (
          <button
            onClick={next}
            aria-label="Next"
            className="hidden sm:flex absolute -right-12 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full bg-background border border-[#e8eaed] shadow-sm items-center justify-center text-[#9ca3af] hover:text-[#1e8aa0] hover:border-[#1e8aa0]/30 hover:shadow-md transition-all duration-200 cursor-pointer"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}

        {/* Slide viewport */}
        <div className="overflow-hidden rounded-lg">
          <div
            className="flex transition-transform duration-500 ease-in-out"
            style={{ transform: `translateX(-${active * 100}%)` }}
          >
            {pages.map((page, pageIdx) => (
              <div
                key={pageIdx}
                className="w-full shrink-0 grid grid-cols-1 sm:grid-cols-2 gap-2 px-0.5"
              >
                {page.map((s, i) => (
                  <SuggestionCard key={i} suggestion={s} onSend={onSend} />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Dot indicators */}
      {total > 1 && (
        <div className="flex items-center justify-center gap-1.5 mt-4">
          {pages.map((_, idx) => (
            <button
              key={idx}
              onClick={() => goTo(idx)}
              aria-label={`Page ${idx + 1}`}
              className={cn(
                "rounded-full transition-all duration-300 cursor-pointer min-h-[20px] sm:min-h-0 flex items-center justify-center",
                idx === active
                  ? "w-6 h-2 sm:w-5 sm:h-1.5 bg-[#1e8aa0]/40"
                  : "w-3 h-2 sm:w-1.5 sm:h-1.5 bg-[#d1d5db]/60 hover:bg-[#9ca3af]/50"
              )}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Individual suggestion card
// ---------------------------------------------------------------------------

function SuggestionCard({
  suggestion: s,
  onSend,
}: {
  suggestion: Suggestion;
  onSend: (text: string) => void;
}) {
  const Icon = s.icon;
  return (
    <button
      onClick={() => onSend(s.text)}
      className="group text-left pl-3.5 pr-3 py-3 bg-background border border-[#e8eaed] rounded-lg text-[13px] text-[#374151] hover:border-[#1e8aa0]/25 hover:bg-[#f8fbfc] transition-all duration-150 cursor-pointer leading-relaxed flex items-start gap-3"
    >
      <div className="shrink-0 mt-0.5">
        <Icon className="w-3.5 h-3.5 text-[#9ca3af] group-hover:text-[#1e8aa0] transition-colors" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className="text-[10px] font-medium tracking-wide text-[#1e8aa0]/60 uppercase">
            {s.tag}
          </span>
        </div>
        <span className="line-clamp-2">{s.text}</span>
      </div>
      <ArrowRight className="w-3.5 h-3.5 text-[#d1d5db] group-hover:text-[#1e8aa0]/50 transition-colors shrink-0 mt-0.5 opacity-0 group-hover:opacity-100" />
    </button>
  );
}
