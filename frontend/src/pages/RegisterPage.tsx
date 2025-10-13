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

  return (
    <section className="panel" style={{ maxWidth: 520, margin: "0 auto", gap: "0.75rem" }}>
      <div className="panel-title">Create your workspace</div>
      <form onSubmit={onSubmit} className="card" style={{ gap: "0.5rem" }}>
        <label>
          Organization
          <input className="input" value={form.organization} onChange={(e) => handleChange("organization", e.target.value)} required />
        </label>
        <label>
          Email
          <input className="input" type="email" value={form.email} onChange={(e) => handleChange("email", e.target.value)} required />
        </label>
        <label>
          Username
          <input className="input" value={form.username} onChange={(e) => handleChange("username", e.target.value)} required />
        </label>
        <label>
          Full name
          <input className="input" value={form.full_name} onChange={(e) => handleChange("full_name", e.target.value)} required />
        </label>
        <label>
          Phone number
          <input className="input" value={form.phone_number} onChange={(e) => handleChange("phone_number", e.target.value)} required />
        </label>
        <label>
          Password
          <input className="input" type="password" value={form.password} onChange={(e) => handleChange("password", e.target.value)} required />
        </label>
        {error && <div style={{ color: "#f87171" }}>{error}</div>}
        {success && <div style={{ color: "#34d399" }}>Registration successful. Check your email.</div>}
        <button type="submit" className="button" disabled={loading}>
          {loading ? "Submitting…" : "Create account"}
        </button>
      </form>
      <div style={{ color: "var(--muted)" }}>
        Already registered? <Link to="/login">Sign in</Link>
      </div>
    </section>
  );
}
