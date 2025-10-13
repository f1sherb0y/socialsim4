import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import i18n, { setLanguage } from '../i18n';

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

  return (
    <div ref={ref} className="lang-switch">
      <button
        type="button"
        className="lang-button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        🌐 {label}
      </button>
      {open && (
        <div className="menu" role="menu" aria-label="Language">
          <button
            type="button"
            role="menuitemradio"
            aria-checked={current === 'en'}
            className={`menu-item ${current === 'en' ? 'active' : ''}`}
            onClick={() => { setLanguage('en'); setOpen(false); }}
          >
            EN {current === 'en' ? '✓' : ''}
          </button>
          <button
            type="button"
            role="menuitemradio"
            aria-checked={current === 'zh'}
            className={`menu-item ${current === 'zh' ? 'active' : ''}`}
            onClick={() => { setLanguage('zh'); setOpen(false); }}
          >
            中文 {current === 'zh' ? '✓' : ''}
          </button>
        </div>
      )}
    </div>
  );
}

