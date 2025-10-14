import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import i18n, { setLanguage } from '../i18n';
import { Dropdown } from './Dropdown';

export function LanguageSwitcher() {
  const { i18n: i18 } = useTranslation();
  const current = i18.language.startsWith('zh') ? 'zh' : 'en';
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (ref.current && !ref.current.contains(target)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, []);

  const label = current === 'zh' ? '中文' : 'EN';

  const btnRef = useRef<HTMLButtonElement | null>(null);
  return (
    <div ref={ref} className="lang-switch">
      <button
        ref={btnRef}
        type="button"
        className="lang-button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        🌐 {label} <span style={{ marginLeft: 6, color: 'var(--muted)' }}>▾</span>
      </button>
      <Dropdown
        anchor={btnRef.current}
        open={open}
        onClose={() => setOpen(false)}
        align="right"
        matchWidth={false}
      >
        <button
          type="button"
          role="menuitemradio"
          aria-checked={current === 'en'}
          className={`menu-item ${current === 'en' ? 'active' : ''}`}
          onClick={() => { setLanguage('en'); setOpen(false); }}
        >
          EN
        </button>
        <button
          type="button"
          role="menuitemradio"
          aria-checked={current === 'zh'}
          className={`menu-item ${current === 'zh' ? 'active' : ''}`}
          onClick={() => { setLanguage('zh'); setOpen(false); }}
        >
          中文
        </button>
      </Dropdown>
    </div>
  );
}
