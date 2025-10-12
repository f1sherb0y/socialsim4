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
      const meRes = await apiClient.get("/auth/me");
      setSession({
        accessToken: loginRes.data.access_token,
        refreshToken: loginRes.data.refresh_token,
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
    <div className="app-container">
      <main className="app-main" style={{ maxWidth: "420px", margin: "0 auto" }}>
        <h1 style={{ fontSize: "2rem", marginBottom: "1.5rem" }}>Welcome back</h1>
        <form onSubmit={onSubmit} className="card">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              style={{ width: "100%", marginTop: "0.5rem", padding: "0.75rem", borderRadius: "10px", border: "1px solid rgba(148,163,184,0.3)" }}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              style={{ width: "100%", marginTop: "0.5rem", padding: "0.75rem", borderRadius: "10px", border: "1px solid rgba(148,163,184,0.3)" }}
            />
          </label>
          {error && <div style={{ color: "#f87171" }}>{error}</div>}
          <button type="submit" className="button" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div style={{ marginTop: "1rem", color: "#94a3b8" }}>
          No account yet? <Link to="/register">Create one</Link>
        </div>
      </main>
    </div>
  );
}
