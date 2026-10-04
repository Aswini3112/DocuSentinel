/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // DocuSentinel design system
        sentinel: {
          bg:        '#050c1a',   // deep navy background
          surface:   '#0a1628',   // card surface
          border:    '#1a2d4a',   // subtle borders
          'border-bright': '#1e3a5f',
          cyan:      '#00d4ff',   // primary accent
          'cyan-dim': '#0099bb',
          blue:      '#0066ff',   // secondary accent
          amber:     '#f59e0b',   // warning / conflict medium
          red:       '#ef4444',   // critical conflict
          green:     '#10b981',   // verified evidence
          purple:    '#8b5cf6',   // uncertain
          gray:      '#64748b',   // muted text
          'gray-light': '#94a3b8',
          text:      '#e2e8f0',   // primary text
          'text-dim': '#94a3b8',  // secondary text
        },
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px)',
        'glow-cyan':    'radial-gradient(ellipse at center, rgba(0,212,255,0.15) 0%, transparent 70%)',
        'glow-blue':    'radial-gradient(ellipse at center, rgba(0,102,255,0.1) 0%, transparent 70%)',
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      fontFamily: {
        sans:  ['Inter', 'system-ui', 'sans-serif'],
        mono:  ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'cyan-glow':   '0 0 20px rgba(0,212,255,0.2)',
        'cyan-glow-lg':'0 0 40px rgba(0,212,255,0.15)',
        'amber-glow':  '0 0 20px rgba(245,158,11,0.2)',
        'red-glow':    '0 0 20px rgba(239,68,68,0.2)',
        'green-glow':  '0 0 20px rgba(16,185,129,0.2)',
        'glass':       '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)',
      },
      animation: {
        'pulse-slow':   'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow-pulse':   'glowPulse 2s ease-in-out infinite',
        'scan-line':    'scanLine 3s linear infinite',
        'fade-in':      'fadeIn 0.3s ease-out',
        'slide-up':     'slideUp 0.3s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
      },
      keyframes: {
        glowPulse: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.6' },
        },
        scanLine: {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          from: { opacity: '0', transform: 'translateX(12px)' },
          to:   { opacity: '1', transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
}
