import type { Config } from "tailwindcss"

// V4 Color palette - warmer and softer
const colors = {
  "surface-primary": "#1C1C1E",
  "surface-secondary": "#2C2C2E", 
  "surface-tertiary": "#3A3A3C",
  "workspace-bg": "#FAFAFA",
  "border-soft": "#48484A",
  "text-primary": "#F2F2F7",
  "text-secondary": "#8E8E93",
  "text-dark": "#1D1D1F",
  "accent-blue": "#007AFF",
  "accent-hover": "#0051D5",
}

export default {
  darkMode: "class",
  content: [
    "./src/**/*.{ts,tsx}",
    "./src/app/**/*.tsx",
    "./src/components/**/*.tsx",
  ],
  theme: {
    extend: {
      colors: {
        ...colors,
      },
      gridTemplateColumns: {
        // sidebar | workspace | chat panel (default desktop)
        layout: "264px 1fr 320px",
      },
    },
  },
  plugins: [
    require('tailwind-scrollbar')({ nocompatible: true }),
  ],
} satisfies Config; 