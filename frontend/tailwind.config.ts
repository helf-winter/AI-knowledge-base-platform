import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        background: '#0b1220',
        panel: '#111a2e',
        panelSoft: '#17213a',
        primary: '#4f8cff',
        primaryHover: '#3c73e6',
        text: '#e5eefc',
        muted: '#8ea2c7',
        border: 'rgba(148, 163, 184, 0.18)',
        success: '#22c55e',
        warning: '#f59e0b',
        danger: '#ef4444',
      },
      boxShadow: {
        glow: '0 12px 40px rgba(79, 140, 255, 0.18)',
      },
      borderRadius: {
        xl2: '1.25rem',
      },
    },
  },
  plugins: [],
};

export default config;
