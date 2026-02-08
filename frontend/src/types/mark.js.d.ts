declare module "mark.js" {
  interface MarkOptions {
    element?: string;
    className?: string;
    exclude?: string[];
    separateWordSearch?: boolean;
    acrossElements?: boolean;
    each?: (element: HTMLElement, range: MarkRange) => void;
    done?: (count: number) => void;
    filter?: (
      textNode: Text,
      term: string,
      marksSoFar: number,
      marksTotal: number
    ) => boolean;
  }

  interface MarkRange {
    start: number;
    length: number;
    [key: string]: unknown;
  }

  interface UnmarkOptions {
    element?: string;
    className?: string;
    done?: () => void;
  }

  class Mark {
    constructor(context: HTMLElement | HTMLElement[] | string);
    mark(keyword: string | string[], options?: MarkOptions): void;
    markRanges(
      ranges: MarkRange[],
      options?: MarkOptions
    ): void;
    unmark(options?: UnmarkOptions): void;
  }

  export default Mark;
}
