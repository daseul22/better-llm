/**
 * Circular Progress 컴포넌트
 *
 * 원형 진행률 표시 (0-100%)
 * 상태별 색상 지원
 */

import React from 'react'
import { cn } from '@/lib/utils'

interface CircularProgressProps {
  /** 진행률 (0-100) */
  progress: number
  /** 크기 (px) */
  size?: number
  /** 선 두께 (px) */
  strokeWidth?: number
  /** 상태 ('running' | 'completed' | 'error' | 'idle') */
  status?: 'running' | 'completed' | 'error' | 'idle'
  /** 추가 클래스 */
  className?: string
  /** 중앙 내용 */
  children?: React.ReactNode
}

export const CircularProgress: React.FC<CircularProgressProps> = ({
  progress,
  size = 40,
  strokeWidth = 3,
  status = 'running',
  className,
  children
}) => {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (progress / 100) * circumference

  // 상태별 색상
  const statusColors = {
    running: {
      trail: '#fef9c3', // status-running-light
      progress: '#eab308', // status-running
      glow: 'rgba(234, 179, 8, 0.4)'
    },
    completed: {
      trail: '#d1fae5', // status-completed-light
      progress: '#22c55e', // status-completed
      glow: 'rgba(34, 197, 94, 0.3)'
    },
    error: {
      trail: '#fee2e2', // status-error-light
      progress: '#ef4444', // status-error
      glow: 'rgba(239, 68, 68, 0.4)'
    },
    idle: {
      trail: '#f3f4f6', // status-idle-light
      progress: '#9ca3af', // status-idle
      glow: 'rgba(156, 163, 175, 0.3)'
    }
  }

  const colors = statusColors[status]

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* 배경 원 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors.trail}
          strokeWidth={strokeWidth}
        />
        {/* 진행률 원 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors.progress}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-300 ease-out"
          style={{
            filter: `drop-shadow(0 0 2px ${colors.glow})`
          }}
        />
      </svg>
      {/* 중앙 내용 */}
      {children && (
        <div className="absolute inset-0 flex items-center justify-center">
          {children}
        </div>
      )}
    </div>
  )
}
