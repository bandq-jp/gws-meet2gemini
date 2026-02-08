/**
 * Highlight Renderer
 *
 * Applies colored <mark> highlights to rendered markdown content
 * by walking DOM text nodes and wrapping matching character ranges.
 *
 * Returns a cleanup function that removes all marks and normalizes text nodes.
 */

import type { AnnotationSeverity } from "./types";

export interface HighlightRange {
  annotationId: string;
  start: number;
  end: number;
  severity: AnnotationSeverity;
}

const SEVERITY_CLASSES: Record<AnnotationSeverity, string> = {
  critical: "annotation-hl annotation-hl-critical",
  major: "annotation-hl annotation-hl-major",
  minor: "annotation-hl annotation-hl-minor",
  info: "annotation-hl annotation-hl-info",
  positive: "annotation-hl annotation-hl-positive",
};

/**
 * Collect all text nodes in document order with their cumulative offsets.
 */
function collectTextNodes(container: HTMLElement): { node: Text; start: number; end: number }[] {
  const result: { node: Text; start: number; end: number }[] = [];
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let offset = 0;
  let current = walker.nextNode() as Text | null;
  while (current) {
    const len = (current.textContent || "").length;
    result.push({ node: current, start: offset, end: offset + len });
    offset += len;
    current = walker.nextNode() as Text | null;
  }
  return result;
}

/**
 * Apply highlight marks to a container's text nodes.
 *
 * For each range, finds the overlapping text nodes and wraps the matching
 * portions in <mark> elements with severity-based CSS classes.
 *
 * Returns a cleanup function that removes all marks.
 */
export function applyHighlights(
  container: HTMLElement,
  ranges: HighlightRange[],
  onClick: (annotationId: string, event: MouseEvent) => void,
): () => void {
  if (ranges.length === 0) return () => {};

  // Sort by start ascending, then by end descending (larger spans first)
  const sorted = [...ranges].sort((a, b) => a.start - b.start || b.end - a.end);
  const marks: HTMLElement[] = [];

  // Process each range independently (re-collect text nodes each time
  // since previous wrapping may have split nodes)
  for (const range of sorted) {
    const textNodes = collectTextNodes(container);
    const toWrap: { node: Text; wrapStart: number; wrapEnd: number }[] = [];

    for (const tn of textNodes) {
      // Skip nodes outside the range
      if (tn.end <= range.start || tn.start >= range.end) continue;

      // Compute the overlap within this text node
      const wrapStart = Math.max(0, range.start - tn.start);
      const wrapEnd = Math.min(tn.node.textContent!.length, range.end - tn.start);
      toWrap.push({ node: tn.node, wrapStart, wrapEnd });
    }

    for (const { node, wrapStart, wrapEnd } of toWrap) {
      try {
        // Split the text node to isolate the portion to wrap
        let targetNode = node;

        // Split off the part before the highlight
        if (wrapStart > 0) {
          targetNode = node.splitText(wrapStart);
        }

        // Split off the part after the highlight
        if (wrapEnd - wrapStart < targetNode.textContent!.length) {
          targetNode.splitText(wrapEnd - wrapStart);
        }

        // Wrap the target node in <mark>
        const mark = document.createElement("mark");
        mark.className = SEVERITY_CLASSES[range.severity];
        mark.dataset.annotationId = range.annotationId;
        targetNode.parentNode!.insertBefore(mark, targetNode);
        mark.appendChild(targetNode);

        mark.addEventListener("click", (e) => {
          e.stopPropagation();
          onClick(range.annotationId, e);
        });

        marks.push(mark);
      } catch {
        // If DOM manipulation fails (e.g., node was already moved), skip
      }
    }
  }

  // Return cleanup function
  return () => {
    for (const mark of marks) {
      const parent = mark.parentNode;
      if (!parent) continue;
      while (mark.firstChild) {
        parent.insertBefore(mark.firstChild, mark);
      }
      parent.removeChild(mark);
    }
    // Normalize adjacent text nodes
    container.normalize();
  };
}
