/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,vue}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        slate: {
          950: "#080d1a",
        },
        wind: {
          50: "#ecfeff",
          100: "#cffafe",
          200: "#a5f3fc",
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
          700: "#0e7490",
          800: "#155e75",
          900: "#164e63",
        },
        amber: {
          DEFAULT: "#f59e0b",
        },
        danger: {
          DEFAULT: "#ef4444",
        },
        ok: {
          DEFAULT: "#10b981",
        },
      },
      fontFamily: {
        display: ['Oswald', 'sans-serif'],
        sans: ['"Noto Sans SC"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
};
