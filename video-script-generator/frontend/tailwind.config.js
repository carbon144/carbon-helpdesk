/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        carbon: {
          50: '#FFF9E6',
          100: '#FFF0BF',
          200: '#FFE699',
          300: '#FFDB66',
          400: '#FFD133',
          500: '#E5A800',
          600: '#CC9600',
          700: '#997000',
          800: '#664B00',
          900: '#332500',
        },
      },
    },
  },
  plugins: [],
}
