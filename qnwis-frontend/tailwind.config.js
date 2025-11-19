/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        qatar: {
          maroon: '#8B1538',
          white: '#FFFFFF',
        }
      }
    },
  },
  plugins: [],
}
