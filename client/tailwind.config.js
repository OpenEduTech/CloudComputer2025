/** @type {import('tailwindcss').Config} */
const gentleSky = {
  50: '#f5fafc',
  100: '#e9f3f6',
  200: '#d5e7ec',
  300: '#c1dbe2',
  400: '#a2c7d2',
  500: '#84b3c2',
  600: '#6a9daa',
  700: '#4f7b84',
  800: '#34525a',
  900: '#1d3034',
}

const mistyLeaf = {
  50: '#f6fbf4',
  100: '#e7f4e4',
  200: '#d3e8d0',
  300: '#bcdcb9',
  400: '#a3cfa2',
  500: '#86b485',
  600: '#679468',
  700: '#4d7351',
  800: '#314b35',
  900: '#1b2b1f',
}

const fogSlate = {
  50: '#f3f9f7',
  100: '#e6f1ed',
  200: '#d1e0dc',
  300: '#b5c6c3',
  400: '#9bb0ad',
  500: '#819895',
  600: '#627673',
  700: '#475754',
  800: '#2d3836',
  900: '#171f1d',
}

const mellowSun = {
  50: '#fffef3',
  100: '#fbfccd',
  200: '#f4f6a7',
  300: '#e6e57f',
  400: '#cfc558',
  500: '#b3a43b',
  600: '#8f7e2b',
  700: '#6a5a1f',
  800: '#453613',
  900: '#231c09',
}

const healingEvergreen = {
  50: '#eff8f4',
  100: '#d5f0e2',
  200: '#a9dec4',
  300: '#7fcba7',
  400: '#64a386',
  500: '#4f856d',
  600: '#3c6955',
  700: '#2c4f3f',
  800: '#1d352a',
  900: '#112018',
}

const sanctuaryPine = {
  50: '#f0f8f3',
  100: '#d7eadf',
  200: '#b2d1c0',
  300: '#8ab398',
  400: '#6d9a7b',
  500: '#557b61',
  600: '#42604b',
  700: '#314739',
  800: '#203026',
  900: '#121c16',
}

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: gentleSky,
        accent: mistyLeaf,
        slate: fogSlate,
        muted: mellowSun,
        serene: gentleSky,
        danger: sanctuaryPine,
        success: healingEvergreen,
        warning: mellowSun,
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      animation: {
        'gradient': 'gradient 8s linear infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      },
      keyframes: {
        gradient: {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'left center'
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center'
          },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}

