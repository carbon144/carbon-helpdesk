/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        carbon: {
          900: 'var(--carbon-900)',
          800: 'var(--carbon-800)',
          700: 'var(--carbon-700)',
          600: 'var(--carbon-600)',
          500: 'var(--carbon-500)',
          400: 'var(--carbon-400)',
          300: 'var(--carbon-300)',
          200: 'var(--carbon-200)',
          100: 'var(--carbon-100)',
          50: 'var(--carbon-50)',
        },
      },
    },
  },
  plugins: [],
}
