import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiClient } from "../api/client";

export function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    organization: "",
    email: "",
    username: "",
    full_name: "",
    phone_number: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await apiClient.post("/auth/register", {
        organization: form.organization,
        email: form.email,
        username: form.username,
        full_name: form.full_name,
        phone_number: form.phone_number,
        password: form.password,
      });
      setSuccess(true);
      setTimeout(() => navigate("/login"), 1500);
    } catch (err) {
      setError("Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: "100%",
    marginTop: "0.5rem",
    padding: "0.75rem",
    borderRadius: "10px",
    border: "1px solid rgba(148,163,184,0.3)",
  } as const;

  return (
    <div className="app-container">
      <main className="app-main" style={{ maxWidth: "520px", margin: "0 auto" }}>
        <h1 style={{ fontSize: "2rem", marginBottom: "1.5rem" }}>Create your workspace</h1>
        <form onSubmit={onSubmit} className="card" style={{ gap: "1rem" }}>
          <label>
            Organization
            <input
              value={form.organization}
              onChange={(event) => handleChange("organization", event.target.value)}
              style={inputStyle}
              required
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={form.email}
              onChange={(event) => handleChange("email", event.target.value)}
              style={inputStyle}
              required
            />
          </label>
          <label>
            Username
            <input
              value={form.username}
              onChange={(event) => handleChange("username", event.target.value)}
              style={inputStyle}
              required
            />
          </label>
          <label>
            Full name
            <input
              value={form.full_name}
              onChange={(event) => handleChange("full_name", event.target.value)}
              style={inputStyle}
              required
            />
          </label>
          <label>
            Phone number
            <input
              value={form.phone_number}
              onChange={(event) => handleChange("phone_number", event.target.value)}
              style={inputStyle}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={(event) => handleChange("password", event.target.value)}
              style={inputStyle}
              required
            />
          </label>
          {error && <div style={{ color: "#f87171" }}>{error}</div>}
          {success && <div style={{ color: "#34d399" }}>Registration successful. Check your email.</div>}
          <button type="submit" className="button" disabled={loading}>
            {loading ? "Submitting…" : "Create account"}
          </button>
        </form>
        <div style={{ marginTop: "1rem", color: "#94a3b8" }}>
          Already registered? <Link to="/login">Sign in</Link>
        </div>
      </main>
    </div>
  );
}
