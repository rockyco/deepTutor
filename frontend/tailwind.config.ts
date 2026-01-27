import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
        heading: ['"Outfit"', 'sans-serif'],
        serif: ['"Merriweather"', 'serif'],
      },
      colors: {
        primary: {
            50: '#f5f3ff',
            100: '#ede9fe',
            200: '#ddd6fe',
            300: '#c4b5fd',
            400: '#a78bfa',
            500: '#8b5cf6',
            600: '#7c3aed',
            700: '#6d28d9',
            800: '#5b21b6',
            900: '#4c1d95',
        },
        surface: '#f8fafc',
        // Preserve original subject colors for compatibility
        english: { 50: "#f0f9ff", 100: "#e0f2fe", 500: "#0ea5e9", 600: "#0284c7" },
        maths: { 50: "#f0fdf4", 100: "#dcfce7", 500: "#22c55e", 600: "#16a34a" },
        verbal: { 50: "#faf5ff", 100: "#f3e8ff", 500: "#a855f7", 600: "#9333ea" },
        nonverbal: { 50: "#fff7ed", 100: "#ffedd5", 500: "#f97316", 600: "#ea580c" },
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'fade-in-up': 'fadeInUp 0.5s ease-out forwards',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        float: {
            '0%, 100%': { transform: 'translateY(0)' },
            '50%': { transform: 'translateY(-10px)' },
        },
        fadeInUp: {
            '0%': { opacity: '0', transform: 'translateY(20px)' },
            '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
};
export default config;
