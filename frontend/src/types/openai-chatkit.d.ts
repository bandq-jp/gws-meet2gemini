import type { DetailedHTMLProps, HTMLAttributes } from "react";

declare global {
  namespace React.JSX {
    interface IntrinsicElements {
      "openai-chatkit": DetailedHTMLProps<HTMLAttributes<HTMLElement>, HTMLElement>;
    }
  }
  namespace JSX {
    interface IntrinsicElements {
      "openai-chatkit": DetailedHTMLProps<HTMLAttributes<HTMLElement>, HTMLElement>;
    }
  }
}

export {};
