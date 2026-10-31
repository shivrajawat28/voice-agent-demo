/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: '#0B0F17',
          card: '#131B2A',
          border: '#1E293B',
          accent: '#10B981', // Emerald green representing agriculture
          accentHover: '#059669',
        },
      },
    },
  },
  plugins: [],
};

