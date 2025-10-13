import { Link, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { useThemeStore } from "../store/theme";

export function NavBar() {
  const location = useLocation();
  const { user, isAuthenticated, clearSession } = useAuthStore((s) => ({ user: s.user, isAuthenticated: s.isAuthenticated, clearSession: s.clearSession }));
  const { mode, toggle } = useThemeStore((s) => ({ mode: s.mode, toggle: s.toggle }));

  const navItems = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/simulations/new", label: "New" },
    { to: "/simulations/saved", label: "Saved" },
    { to: "/settings/providers", label: "Settings" },
  ];

  return (
    <nav className="nav">
      <div className="nav-left">
        <Link to="/dashboard" className="nav-brand">SocialSim4</Link>
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
        {isAuthenticated ? (
          <div className="nav-user">
            <span className="nav-username">{String((user as any)?.email ?? "")}</span>
            <button type="button" className="text-button" onClick={clearSession}>Sign out</button>
          </div>
        ) : (
          <div className="nav-user">
            <Link to="/login" className="nav-link">Login</Link>
            <Link to="/register" className="nav-link">Register</Link>
          </div>
        )}
      </div>
    </nav>
  );
}
