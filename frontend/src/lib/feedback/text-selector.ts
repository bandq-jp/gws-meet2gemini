/**
 * Text Selection → Annotation Selector Utility
 *
 * Captures user text selection from rendered markdown content
 * and converts it to a W3C-inspired TextSpanSelector for persistence.
 */

import type { TextSpanSelector } from "./types";

const QUOTE_CONTEXT_LENGTH = 30;

/**
 * Get the plain text content of a container element.
 */
function getPlainText(container: HTMLElement): string {
  return container.textContent || "";
}

/**
 * Calculate the character offset of a node/offset within a container.
 */
function getTextOffset(container: HTMLElement, node: Node, offset: number): number {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let pos = 0;
  let current = walker.nextNode();
  while (current) {
    if (current === node) {
      return pos + offset;
    }
    pos += (current.textContent || "").length;
    current = walker.nextNode();
  }
  return pos;
}

/**
 * Capture the current text selection within a container element
 * and convert it to a TextSpanSelector.
 *
 * Returns null if no valid selection is within the container.
 */
export function captureTextSelection(
  container: HTMLElement
): TextSpanSelector | null {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
    return null;
  }

  const range = selection.getRangeAt(0);

  // Verify the selection is within the container
  if (!container.contains(range.startContainer) || !container.contains(range.endContainer)) {
    return null;
  }

  const selectedText = selection.toString().trim();
  if (!selectedText) {
    return null;
  }

  const fullText = getPlainText(container);
  const start = getTextOffset(container, range.startContainer, range.startOffset);
  const end = getTextOffset(container, range.endContainer, range.endOffset);

  const prefix = fullText.slice(Math.max(0, start - QUOTE_CONTEXT_LENGTH), start);
  const exact = fullText.slice(start, end);
  const suffix = fullText.slice(end, end + QUOTE_CONTEXT_LENGTH);

  return {
    type: "text_span",
    position: { start, end },
    quote: { prefix, exact, suffix },
  };
}

/**
 * Find the character offset range for a TextSpanSelector in plain text.
 * First tries position-based, falls back to quote-based fuzzy match.
 */
export function resolveSelector(
  plainText: string,
  selector: TextSpanSelector
): { start: number; end: number } | null {
  // Try exact position match first
  const { start, end } = selector.position;
  const slice = plainText.slice(start, end);
  if (slice === selector.quote.exact) {
    return { start, end };
  }

  // Fallback: search for exact quote text
  const idx = plainText.indexOf(selector.quote.exact);
  if (idx !== -1) {
    return { start: idx, end: idx + selector.quote.exact.length };
  }

  return null;
}

/**
 * Generate a simple SHA-like hash for content change detection.
 */
export function simpleHash(text: string): string {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    const char = text.charCodeAt(i);
    hash = ((hash << 5) - hash + char) | 0;
  }
  return Math.abs(hash).toString(16).padStart(8, "0");
}
