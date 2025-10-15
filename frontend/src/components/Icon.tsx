import type { JSX } from 'react';

type IconName =
  | 'test'
  | 'delete'
  | 'save'
  | 'star'
  | 'star-solid'
  | 'eye'
  | 'eye-off';

export function Icon({ name }: { name: IconName }): JSX.Element {
  switch (name) {
    case 'test':
      // Link icon (represents connectivity test)
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M10 13a5 5 0 0 0 7.07 0l1.41-1.41a5 5 0 1 0-7.07-7.07L10 5"/>
          <path d="M14 11a5 5 0 0 0-7.07 0L5.5 12.43a5 5 0 1 0 7.07 7.07L14 19"/>
        </svg>
      );
    case 'delete':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M3 6h18"/>
          <path d="M8 6V4h8v2"/>
          <path d="M6 6l1 14h10l1-14"/>
          <path d="M10 11v6M14 11v6"/>
        </svg>
      );
    case 'save':
      // ArrowDownTray-like save indicator
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M12 3v12"/>
          <path d="M8 11l4 4 4-4"/>
          <path d="M5 21h14"/>
        </svg>
      );
    case 'star':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.9 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/>
        </svg>
      );
    case 'star-solid':
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="0" aria-hidden>
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.9 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/>
        </svg>
      );
    case 'eye':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
      );
    case 'eye-off':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M17.94 17.94L6.06 6.06"/>
          <path d="M10.58 10.58a3 3 0 004.24 4.24"/>
          <path d="M9.88 4.12A9.91 9.91 0 0121 12c-1.64 2.9-4.88 5-9 5a9.91 9.91 0 01-4.12-.88"/>
          <path d="M3 3l18 18"/>
        </svg>
      );
  }
}

