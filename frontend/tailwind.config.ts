import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  // Disable dark mode completely - force light mode only
  darkMode: false,
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;