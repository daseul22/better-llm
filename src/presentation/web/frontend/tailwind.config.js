/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{ts,tsx,js,jsx}',
  ],
  theme: {
  	container: {
  		center: true,
  		padding: '2rem',
  		screens: {
  			'2xl': '1400px'
  		}
  	},
  	extend: {
  		colors: {
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			// 노드 타입별 브랜드 컬러
  			node: {
  				input: {
  					light: '#d1fae5',
  					DEFAULT: '#10b981',
  					dark: '#059669'
  				},
  				worker: {
  					light: '#e0e7ff',
  					DEFAULT: '#6366f1',
  					dark: '#4f46e5'
  				},
  				condition: {
  					light: '#fef3c7',
  					DEFAULT: '#f59e0b',
  					dark: '#d97706'
  				},
  				merge: {
  					light: '#e9d5ff',
  					DEFAULT: '#a855f7',
  					dark: '#9333ea'
  				}
  			},
  			// 상태별 시맨틱 컬러
  			status: {
  				running: {
  					light: '#fef9c3',
  					DEFAULT: '#eab308',
  					dark: '#ca8a04',
  					glow: 'rgba(234, 179, 8, 0.4)'
  				},
  				completed: {
  					light: '#d1fae5',
  					DEFAULT: '#22c55e',
  					dark: '#16a34a',
  					glow: 'rgba(34, 197, 94, 0.3)'
  				},
  				error: {
  					light: '#fee2e2',
  					DEFAULT: '#ef4444',
  					dark: '#dc2626',
  					glow: 'rgba(239, 68, 68, 0.4)'
  				},
  				idle: {
  					light: '#f3f4f6',
  					DEFAULT: '#9ca3af',
  					dark: '#6b7280'
  				}
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		// 노드 전용 간격 시스템 (8px 그리드)
  		spacing: {
  			'node': '12px',
  			'node-sm': '8px',
  			'node-xs': '6px',
  			'node-lg': '16px',
  			'node-xl': '20px'
  		},
  		// 노드 전용 타이포그래피
  		fontSize: {
  			'node-xs': ['10px', { lineHeight: '14px', fontWeight: '400' }],
  			'node-sm': ['11px', { lineHeight: '16px', fontWeight: '400' }],
  			'node-base': ['12px', { lineHeight: '18px', fontWeight: '400' }],
  			'node-lg': ['14px', { lineHeight: '20px', fontWeight: '500' }]
  		},
  		// Elevation 시스템 (그림자)
  		boxShadow: {
  			'node': '0 2px 4px rgba(0, 0, 0, 0.08)',
  			'node-hover': '0 4px 12px rgba(0, 0, 0, 0.15)',
  			'node-selected': '0 0 0 3px rgba(59, 130, 246, 0.3)',
  			'node-executing': '0 0 20px rgba(234, 179, 8, 0.4)',
  			'node-error': '0 0 20px rgba(239, 68, 68, 0.3)'
  		},
  		// 트랜지션
  		transitionDuration: {
  			'node': '200ms',
  			'node-fast': '100ms',
  			'node-slow': '300ms'
  		},
  		transitionTimingFunction: {
  			'node': 'cubic-bezier(0.4, 0, 0.2, 1)'
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			},
  			// 노드 애니메이션
  			'pulse-border': {
  				'0%, 100%': {
  					borderColor: 'rgb(234 179 8)',
  					boxShadow: '0 0 0 0 rgba(234, 179, 8, 0.7)'
  				},
  				'50%': {
  					borderColor: 'rgb(250 204 21)',
  					boxShadow: '0 0 0 4px rgba(234, 179, 8, 0)'
  				}
  			},
  			'node-appear': {
  				'0%': {
  					opacity: '0',
  					transform: 'scale(0.95)'
  				},
  				'100%': {
  					opacity: '1',
  					transform: 'scale(1)'
  				}
  			},
  			'shake': {
  				'0%, 100%': { transform: 'translateX(0)' },
  				'10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-2px)' },
  				'20%, 40%, 60%, 80%': { transform: 'translateX(2px)' }
  			},
  			'glow': {
  				'0%, 100%': {
  					boxShadow: '0 0 8px rgba(234, 179, 8, 0.3)'
  				},
  				'50%': {
  					boxShadow: '0 0 16px rgba(234, 179, 8, 0.6)'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out',
  			'pulse-border': 'pulse-border 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
  			'node-appear': 'node-appear 0.3s ease-out',
  			'shake': 'shake 0.5s ease-in-out',
  			'glow': 'glow 2s ease-in-out infinite'
  		}
  	}
  },
  plugins: [require('tailwindcss-animate')],
}
