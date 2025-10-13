import { FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { apiClient } from "../api/client";
import { useAuthStore } from "../store/auth";

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
};

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: { pathname?: string } } };
  const setSession = useAuthStore((state) => state.setSession);
  const updateTokens = useAuthStore((state) => state.updateTokens);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const loginRes = await apiClient.post<LoginResponse>("/auth/login", {
        email,
        password,
      });
      const { access_token, refresh_token } = loginRes.data;
      updateTokens(access_token, refresh_token);

      const meRes = await apiClient.get("/auth/me");
      setSession({
        accessToken: access_token,
        refreshToken: refresh_token,
        user: meRes.data,
      });
      const redirectTo = location.state?.from?.pathname ?? "/dashboard";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError("Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel" style={{ maxWidth: 420, margin: "0 auto", gap: "0.75rem" }}>
      <div className="panel-title">Welcome back</div>
      <form onSubmit={onSubmit} className="card" style={{ gap: "0.5rem" }}>
        <label>
          Email
          <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <div style={{ color: "#f87171" }}>{error}</div>}
        <button type="submit" className="button" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <div style={{ color: "var(--muted)" }}>
        No account yet? <Link to="/register">Create one</Link>
      </div>
    </section>
  );
}
