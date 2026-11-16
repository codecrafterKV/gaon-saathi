/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#ecfdf3',
          100: '#d1fae0',
          200: '#a6f2c4',
          300: '#6be3a0',
          400: '#34cb7b',
          500: '#14ae5c',
          600: '#0b8f4a',
          700: '#0b713d',
          800: '#0e5a34',
          900: '#0d4a2c',
        },
        navy: {
          50: '#f2f6fb',
          100: '#e1e9f4',
          200: '#c4d3e8',
          300: '#97b2d4',
          400: '#5f86b8',
          500: '#3d6699',
          600: '#2b4f7d',
          700: '#1f3d64',
          800: '#152d4c',
          900: '#0b1f3a',
          950: '#06142a',
        },
      },
      fontFamily: {
        sans: ['"Inter Variable"', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        display: ['"Plus Jakarta Sans Variable"', '"Inter Variable"', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(11,31,58,0.04), 0 4px 16px -4px rgba(11,31,58,0.08)',
        lift: '0 2px 4px rgba(11,31,58,0.06), 0 16px 40px -12px rgba(11,31,58,0.22)',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.9)', opacity: '0.6' },
          '100%': { transform: 'scale(1.6)', opacity: '0' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.6s ease-out both',
        'pulse-ring': 'pulse-ring 2.4s ease-out infinite',
      },
    },
  },
  plugins: [],
}
