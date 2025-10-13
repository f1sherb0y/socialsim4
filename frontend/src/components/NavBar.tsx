import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import i18n from "../i18n";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { useAuthStore } from "../store/auth";
import { useThemeStore } from "../store/theme";

export function NavBar() {
  const location = useLocation();
  const { user, isAuthenticated, clearSession } = useAuthStore((s) => ({ user: s.user, isAuthenticated: s.isAuthenticated, clearSession: s.clearSession }));
  const { mode, toggle } = useThemeStore((s) => ({ mode: s.mode, toggle: s.toggle }));
  const { t } = useTranslation();

  const navItems = [
    { to: "/dashboard", label: t('nav.dashboard') },
    { to: "/simulations/new", label: t('nav.new') },
    { to: "/simulations/saved", label: t('nav.saved') },
    { to: "/settings/providers", label: t('nav.settings') },
  ];

  return (
    <nav className="nav">
      <div className="nav-left">
        <Link to="/" className="nav-brand">{t('brand')}</Link>
        <div className="nav-links">
          {navItems.map((item) => (
            <Link key={item.to} to={item.to} className={`nav-link ${location.pathname.startsWith(item.to) ? "active" : ""}`}>
              {item.label}
            </Link>
          ))}
        </div>
      </div>
      <div className="nav-right">
        <button type="button" className="icon-button" onClick={toggle} title="Toggle theme">
          {mode === "dark" ? "🌙" : "☀️"}
        </button>
        <LanguageSwitcher />
        {isAuthenticated ? (
          <div className="nav-user">
            <span className="nav-username">{String((user as any)?.email ?? "")}</span>
            <button type="button" className="text-button" onClick={clearSession}>{t('nav.signout')}</button>
          </div>
        ) : (
          <div className="nav-user">
            <Link to="/login" className="nav-link">{t('nav.login')}</Link>
            <Link to="/register" className="nav-link">{t('nav.register')}</Link>
          </div>
        )}
      </div>
    </nav>
  );
}
