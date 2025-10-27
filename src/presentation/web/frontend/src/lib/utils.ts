import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * shadcn/ui 유틸리티: 클래스명 병합
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
